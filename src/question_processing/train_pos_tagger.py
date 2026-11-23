"""Pelatihan dan evaluasi POS Tagger CRF Bahasa Indonesia (IDN Tagged Corpus + Domain Gold)."""

import random
import re
from pathlib import Path
from typing import Any

import pycrfsuite
from sklearn.metrics import classification_report

from config.settings import DATA_DIR, REPORTS_DIR

_IDN_CORPUS_PATH = DATA_DIR / "question_processing" / "external" / "idn_tagged_corpus.tsv"
_DOMAIN_GOLD_PATH = DATA_DIR / "question_processing" / "training" / "pos_domain_gold.tsv"
_POS_MODEL_PATH = DATA_DIR / "question_processing" / "models" / "pos_crf.crfsuite"
_EVAL_REPORT_PATH = REPORTS_DIR / "pos_tagger_eval.txt"


def parse_idn_tsv(raw_text: str) -> list[list[tuple[str, str]]]:
    """Mem-parse format TSV IDN Tagged Corpus dan memecah token multi-kata per spasi."""
    sentences: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<kalimat"):
            current = []
            continue
        if stripped == "</kalimat>":
            if current:
                sentences.append(current)
                current = []
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue
        token_text, tag = parts[0].strip(), parts[1].strip().upper()
        if not token_text or not tag:
            continue
        for sub_tok in token_text.split():
            current.append((sub_tok, tag))

    if current:
        sentences.append(current)
    return sentences


def extract_token_features(tokens: list[str], index: int) -> dict[str, Any]:
    """Mengekstrak fitur morfologi dan konteks untuk satu token pada model CRF."""
    word = tokens[index]
    lower = word.lower()
    feats: dict[str, Any] = {
        "bias": 1.0,
        "word.lower": lower,
        "prefix1": lower[:1],
        "prefix2": lower[:2],
        "prefix3": lower[:3],
        "suffix1": lower[-1:],
        "suffix2": lower[-2:],
        "suffix3": lower[-3:],
        "is_digit": word.isdigit(),
        "has_digit": any(ch.isdigit() for ch in word),
        "is_title": word.istitle(),
        "is_upper": word.isupper(),
        "has_hyphen": "-" in word,
        "has_underscore": "_" in word,
    }
    if index > 0:
        prev_w = tokens[index - 1].lower()
        feats["-1:word.lower"] = prev_w
        feats["-1:suffix2"] = prev_w[-2:]
        feats["-1:is_digit"] = tokens[index - 1].isdigit()
    else:
        feats["BOS"] = True

    if index < len(tokens) - 1:
        next_w = tokens[index + 1].lower()
        feats["+1:word.lower"] = next_w
        feats["+1:suffix2"] = next_w[-2:]
        feats["+1:is_digit"] = tokens[index + 1].isdigit()
    else:
        feats["EOS"] = True

    return feats


def sentence_to_features(tokens: list[str]) -> list[dict[str, Any]]:
    """Mengonversi urutan token kalimat menjadi daftar dict fitur untuk CRFsuite."""
    return [extract_token_features(tokens, i) for i in range(len(tokens))]


def _compute_token_accuracy(y_true: list[list[str]], y_pred: list[list[str]]) -> float:
    total = sum(len(seq) for seq in y_true)
    if total == 0:
        return 0.0
    correct = sum(
        1
        for true_seq, pred_seq in zip(y_true, y_pred)
        for t, p in zip(true_seq, pred_seq)
        if t == p
    )
    return correct / total


def train_and_evaluate(
    corpus_path: Path = _IDN_CORPUS_PATH,
    domain_gold_path: Path = _DOMAIN_GOLD_PATH,
    model_path: Path = _POS_MODEL_PATH,
    eval_report_path: Path = _EVAL_REPORT_PATH,
    seed: int = 42,
) -> dict[str, float]:
    """Melatih model CRF pada 90% korpus IDN, mengevaluasi pada 10% held-out dan gold domain."""
    from src.question_processing.query_formulator import apply_domain_pos_overrides

    sentences = parse_idn_tsv(corpus_path.read_text(encoding="utf-8"))
    shuffled = list(sentences)
    random.Random(seed).shuffle(shuffled)

    split_idx = int(0.9 * len(shuffled))
    train_sents = shuffled[:split_idx]
    test_sents = shuffled[split_idx:]

    trainer = pycrfsuite.Trainer(verbose=False)
    for sent in train_sents:
        tokens = [w for w, _ in sent]
        labels = [t for _, t in sent]
        trainer.append(sentence_to_features(tokens), labels)

    trainer.set_params(
        {
            "c1": 0.1,
            "c2": 0.1,
            "max_iterations": 100,
            "feature.possible_transitions": True,
        }
    )
    model_path.parent.mkdir(parents=True, exist_ok=True)
    trainer.train(str(model_path))

    tagger = pycrfsuite.Tagger()
    tagger.open(str(model_path))

    y_true = [[t for _, t in sent] for sent in test_sents]
    y_pred = [tagger.tag(sentence_to_features([w for w, _ in sent])) for sent in test_sents]
    idn_acc = _compute_token_accuracy(y_true, y_pred)

    flat_true = [t for seq in y_true for t in seq]
    flat_pred = [p for seq in y_pred for p in seq]
    cls_rep = classification_report(flat_true, flat_pred, zero_division=0, digits=4)

    # Evaluasi pada 20 pertanyaan domain sebelum vs sesudah override leksikon
    domain_sents = parse_idn_tsv(domain_gold_path.read_text(encoding="utf-8"))
    dom_true = [[t for _, t in sent] for sent in domain_sents]
    dom_pred_raw = [tagger.tag(sentence_to_features([w for w, _ in sent])) for sent in domain_sents]
    dom_pred_ovr = [
        [
            t
            for _, t in apply_domain_pos_overrides(
                list(zip([w for w, _ in sent], raw_tags))
            )
        ]
        for sent, raw_tags in zip(domain_sents, dom_pred_raw)
    ]
    dom_acc_raw = _compute_token_accuracy(dom_true, dom_pred_raw)
    dom_acc_ovr = _compute_token_accuracy(dom_true, dom_pred_ovr)

    eval_report_path.parent.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "# Evaluasi POS Tagger CRF (IDN Tagged Corpus + Domain Gold)",
        f"Train sentences: {len(train_sents)} | Held-out test sentences: {len(test_sents)}",
        f"IDN Held-out Token Accuracy: {idn_acc:.4f}",
        f"Domain Gold Sentences: {len(domain_sents)}",
        f"Domain Gold Accuracy (CRF Raw): {dom_acc_raw:.4f}",
        f"Domain Gold Accuracy (CRF + Domain Override): {dom_acc_ovr:.4f}",
        "",
        "## Classification Report (IDN 10% Held-out)",
        cls_rep,
    ]
    eval_report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return {
        "idn_accuracy": idn_acc,
        "domain_accuracy_raw": dom_acc_raw,
        "domain_accuracy_override": dom_acc_ovr,
    }


def main() -> None:
    """Entry point CLI untuk pelatihan dan evaluasi POS Tagger CRF."""
    metrics = train_and_evaluate()
    print(
        f"IDN acc={metrics['idn_accuracy']:.4f}, "
        f"Domain raw={metrics['domain_accuracy_raw']:.4f}, "
        f"Domain override={metrics['domain_accuracy_override']:.4f}"
    )


if __name__ == "__main__":
    main()
