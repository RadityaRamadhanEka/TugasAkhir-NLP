"""POS Tagging pertanyaan, Query Formulation, Query Expansion, & Reformulation (PBA14 Slide 46-47)."""

import re
import warnings
from functools import lru_cache
from pathlib import Path

import pycrfsuite

from config.settings import DATA_DIR
from src.contracts import ExtractedEntity
from src.question_processing.resources import load_course_lexicon, load_domain_lexicon
from src.question_processing.train_pos_tagger import sentence_to_features

_POS_MODEL_PATH = DATA_DIR / "question_processing" / "models" / "pos_crf.crfsuite"
_COURSE_CODE_RE = re.compile(r"^[a-z]{3}\d{5}(?:-\d)?$", re.IGNORECASE)
_CPL_CODE_RE = re.compile(r"^if_cpl_[a-z]{1,2}\d$", re.IGNORECASE)


@lru_cache(maxsize=1)
def _load_crf_tagger(model_path: str) -> pycrfsuite.Tagger | None:
    path = Path(model_path)
    if not path.exists():
        warnings.warn(
            f"Model POS CRF tidak ditemukan di {path}; memakai fallback lexicon tagger.",
            UserWarning,
            stacklevel=2,
        )
        return None
    tagger = pycrfsuite.Tagger()
    tagger.open(str(path))
    return tagger


@lru_cache(maxsize=1)
def _domain_proper_noun_phrases() -> tuple[tuple[str, ...], ...]:
    phrases: set[tuple[str, ...]] = set()
    course_lex = load_course_lexicon()
    for entry in course_lex["courses_2024"].values():
        toks = tuple(entry["name"].lower().split())
        if toks:
            phrases.add(toks)
        for alias in entry.get("aliases", []):
            a_toks = tuple(alias.lower().split())
            if len(a_toks) >= 2:
                phrases.add(a_toks)
    for entry in course_lex["courses_2020"].values():
        toks = tuple(entry["name"].lower().split())
        if toks:
            phrases.add(toks)
    domain_lex = load_domain_lexicon()
    for canon, aliases in domain_lex["learning_paths"].items():
        phrases.add(tuple(canon.lower().split()))
        for alias in aliases:
            a_toks = tuple(alias.lower().split())
            if len(a_toks) >= 2:
                phrases.add(a_toks)
    for canon, aliases in domain_lex["elective_groups"].items():
        phrases.add(tuple(canon.lower().split()))
        for alias in aliases:
            a_toks = tuple(alias.lower().split())
            if len(a_toks) >= 2:
                phrases.add(a_toks)
    return tuple(sorted(phrases, key=len, reverse=True))


def apply_domain_pos_overrides(tagged: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Menerapkan override leksikon domain kurikulum di atas hasil POS tagger umum."""
    domain_lex = load_domain_lexicon()
    wh_words = set(domain_lex["wh_words"])
    command_words = set(domain_lex["command_words"])
    abbrevs = {k.lower() for k in domain_lex["abbreviations"]}
    tokens_lower = [tok.lower() for tok, _ in tagged]
    result = list(tagged)

    # Tandai span frasa nama MK / learning path / kelompok pilihan sebagai NNP
    idx = 0
    phrases = _domain_proper_noun_phrases()
    while idx < len(tokens_lower):
        matched_len = 0
        for phrase in phrases:
            plen = len(phrase)
            if idx + plen <= len(tokens_lower) and tuple(tokens_lower[idx : idx + plen]) == phrase:
                matched_len = plen
                break
        if matched_len > 0:
            for offset in range(matched_len):
                result[idx + offset] = (result[idx + offset][0], "NNP")
            idx += matched_len
        else:
            idx += 1

    for i, (tok, tag) in enumerate(result):
        low = tok.lower()
        if low in wh_words:
            result[i] = (tok, "WH")
        elif _COURSE_CODE_RE.match(tok) or _CPL_CODE_RE.match(tok):
            result[i] = (tok, "NNP")
        elif tok.isdigit() or re.fullmatch(r"\d+(?:\.\d+)?", tok):
            result[i] = (tok, "CD")
        elif i == 0 and low in command_words:
            result[i] = (tok, "VB")
        elif low in {"sks", "mk"}:
            result[i] = (tok, "NN")
        elif low in abbrevs and tag not in {"NN", "NNP"}:
            result[i] = (tok, "NNP")

    return result


def _fallback_pos_tag(tokens: list[str]) -> list[tuple[str, str]]:
    domain_lex = load_domain_lexicon()
    wh_words = set(domain_lex["wh_words"])
    command_words = set(domain_lex["command_words"])
    preps = {"di", "ke", "dari", "pada", "dalam", "untuk", "bagi", "dengan", "tentang"}
    conjs = {"dan", "atau", "yang", "serta", "jika", "bila"}
    tagged: list[tuple[str, str]] = []
    for i, tok in enumerate(tokens):
        low = tok.lower()
        if low in wh_words:
            tagged.append((tok, "WH"))
        elif i == 0 and low in command_words:
            tagged.append((tok, "VB"))
        elif tok.isdigit():
            tagged.append((tok, "CD"))
        elif low in preps:
            tagged.append((tok, "IN"))
        elif low in conjs:
            tagged.append((tok, "SC"))
        else:
            tagged.append((tok, "NN"))
    return tagged


def pos_tag_question(tokens: list[str]) -> list[tuple[str, str]]:
    """Memberi label Part-of-Speech (POS tag) pada token pertanyaan (CRF + override domain)."""
    if not tokens:
        return []
    tagger = _load_crf_tagger(str(_POS_MODEL_PATH))
    if tagger is None:
        raw_tagged = _fallback_pos_tag(tokens)
    else:
        preds = tagger.tag(sentence_to_features(tokens))
        raw_tagged = list(zip(tokens, preds))
    return apply_domain_pos_overrides(raw_tagged)


def formulate_query(
    normalized_question: str,
    tokens: list[str],
    entities: list[ExtractedEntity],
    pos_tags: list[tuple[str, str]] | None = None,
) -> tuple[list[str], list[str]]:
    """Menghasilkan `(query_keywords, expanded_queries)` untuk modul Passage Retrieval.

    Mencakup:
    - Seleksi query keywords (buang kata tanya & stopword yang tidak informatif)
    - Query expansion dengan sinonim/singkatan domain (mis. MK <-> mata kuliah, AI <-> kecerdasan artifisial)
    - Query reformulation ke pola deklaratif (ala Lin 2007, Slide 47)
    """
    raise NotImplementedError("Anggota 3: implementasikan query formulation & expansion di sini.")
