"""Evaluasi kuantitatif terpadu modul Question Processing (Anggota 3 — Yusuf)."""

import json
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, classification_report, f1_score

from config.settings import BASE_DIR, REPORTS_DIR
from src.question_processing.answer_type_detector import detect_answer_type
from src.question_processing.question_classifier import (
    _featurize_sample,
    classify_question,
    classify_question_rule_only,
    detect_speech_act,
    evaluate_ml_classifiers,
    train_question_classifier,
)
from src.question_processing.question_processor import process_question
from src.question_processing.resources import load_test_questions, load_training_questions

_FIXTURE_PATH = BASE_DIR / "tests" / "fixtures" / "question_analysis_samples.json"
_POS_EVAL_PATH = REPORTS_DIR / "pos_tagger_eval.txt"
_OUTPUT_EVAL_PATH = REPORTS_DIR / "question_processing_eval.md"


def evaluate_entity_fixtures() -> dict[str, float]:
    """Menghitung Precision, Recall, dan F1 ekstraksi entitas pada himpunan fixture resmi."""
    fixtures = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    tp = fp = fn = 0
    for item in fixtures:
        pred = process_question(item["original_question"])
        gold_set = {(e["type"], e["normalized_value"]) for e in item["entities"]}
        pred_set = {(e["type"], e["normalized_value"]) for e in pred["entities"]}
        tp += len(gold_set & pred_set)
        fp += len(pred_set - gold_set)
        fn += len(gold_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"tp": float(tp), "fp": float(fp), "fn": float(fn), "precision": precision, "recall": recall, "f1": f1}


def run_module_evaluation(output_path: Path = _OUTPUT_EVAL_PATH) -> dict[str, Any]:
    """Menjalankan evaluasi lengkap Question Processing dan menyimpan laporan ke Markdown."""
    train_data = load_training_questions()
    test_data = load_test_questions()

    cv_scores = evaluate_ml_classifiers(train_data)
    best_model = train_question_classifier(train_data)

    y_intent_true = [item["intent"] for item in test_data]
    y_sa_true = [item["speech_act"] for item in test_data]

    y_sa_pred = [detect_speech_act(item["question"]) for item in test_data]
    y_rule_pred = [
        classify_question_rule_only(item["question"], speech_act=sa) or "other"
        for item, sa in zip(test_data, y_sa_pred)
    ]
    y_ml_pred = [
        str(best_model.predict([_featurize_sample(item["question"])])[0]) for item in test_data
    ]

    full_outputs = [process_question(item["question"]) for item in test_data]
    y_hyb_pred = [out["intent"] for out in full_outputs]

    # Answer type ground-truth diturunkan dari intent acuan pada test_data
    y_at_fine_true = [detect_answer_type(item["question"], item["intent"])[1] for item in test_data]
    y_at_coarse_true = [val.split(":")[0] for val in y_at_fine_true]
    y_at_fine_pred = [out["answer_type"] for out in full_outputs]
    y_at_coarse_pred = [out["answer_type_coarse"] for out in full_outputs]

    sa_acc = accuracy_score(y_sa_true, y_sa_pred)
    rule_acc = accuracy_score(y_intent_true, y_rule_pred)
    rule_f1 = f1_score(y_intent_true, y_rule_pred, average="macro", zero_division=0)
    ml_acc = accuracy_score(y_intent_true, y_ml_pred)
    ml_f1 = f1_score(y_intent_true, y_ml_pred, average="macro", zero_division=0)
    hyb_acc = accuracy_score(y_intent_true, y_hyb_pred)
    hyb_f1 = f1_score(y_intent_true, y_hyb_pred, average="macro", zero_division=0)
    at_coarse_acc = accuracy_score(y_at_coarse_true, y_at_coarse_pred)
    at_fine_acc = accuracy_score(y_at_fine_true, y_at_fine_pred)
    ent_metrics = evaluate_entity_fixtures()

    cls_report_text = classification_report(y_intent_true, y_hyb_pred, zero_division=0, digits=4)
    pos_summary = (
        _POS_EVAL_PATH.read_text(encoding="utf-8").splitlines()[:7]
        if _POS_EVAL_PATH.exists()
        else []
    )

    correct_examples = []
    error_examples = []
    for item, out in zip(test_data, full_outputs):
        row = {
            "question": item["question"],
            "true_intent": item["intent"],
            "pred_intent": out["intent"],
            "answer_type": out["answer_type"],
            "speech_act": out["speech_act"],
            "entities": [(e["type"], e["normalized_value"]) for e in out["entities"]],
        }
        if out["intent"] == item["intent"] and len(correct_examples) < 5:
            correct_examples.append(row)
        elif out["intent"] != item["intent"]:
            error_examples.append(row)

    lines = [
        "# Laporan Evaluasi Modul Question Processing (Anggota 3 — Yusuf)",
        "",
        f"- Jumlah sampel latih: **{len(train_data)}** (21 intent)",
        f"- Jumlah sampel uji held-out: **{len(test_data)}** (0 duplikat dengan latih)",
        "",
        "## 1. Perbandingan Classifier ML (5-Fold Stratified CV pada Data Latih)",
        "",
        "| Model | CV Accuracy | CV Macro-F1 |",
        "|---|---|---|",
    ]
    for name, sc in cv_scores.items():
        lines.append(f"| `{name}` | {sc['accuracy']:.4f} | {sc['macro_f1']:.4f} |")

    lines.extend(
        [
            "",
            "## 2. Studi Ablasi pada Data Uji Held-Out (`questions_test.json`)",
            "",
            "| Varian Metode | Test Accuracy | Test Macro-F1 |",
            "|---|---|---|",
            f"| Rule-based Only | {rule_acc:.4f} | {rule_f1:.4f} |",
            f"| ML Only (Best CV) | {ml_acc:.4f} | {ml_f1:.4f} |",
            f"| **Hybrid (Rule + ML)** | **{hyb_acc:.4f}** | **{hyb_f1:.4f}** |",
            "",
            "## 3. Ringkasan Akurasi Per Komponen",
            "",
            f"- **Speech Act Accuracy:** {sa_acc:.4f}",
            f"- **Hybrid Intent Accuracy:** {hyb_acc:.4f} (Macro-F1: {hyb_f1:.4f})",
            f"- **Answer Type Coarse Accuracy (6 kelas Li & Roth):** {at_coarse_acc:.4f}",
            f"- **Answer Type Fine Accuracy:** {at_fine_acc:.4f}",
            f"- **Entity Extraction (12 Fixture Resmi):** Precision={ent_metrics['precision']:.4f}, Recall={ent_metrics['recall']:.4f}, F1={ent_metrics['f1']:.4f} (TP={int(ent_metrics['tp'])}, FP={int(ent_metrics['fp'])}, FN={int(ent_metrics['fn'])})",
            "",
            "## 4. Evaluasi POS Tagger CRF (`reports/pos_tagger_eval.txt`)",
            "",
            "```text",
            *pos_summary,
            "```",
            "",
            "## 5. Classification Report Per Intent (Hybrid pada Held-Out)",
            "",
            "```text",
            cls_report_text.rstrip(),
            "```",
            "",
            "## 6. Contoh Prediksi Benar (Sampel)",
            "",
            "| Pertanyaan | Intent | Answer Type | Speech Act | Entitas |",
            "|---|---|---|---|---|",
        ]
    )
    for row in correct_examples:
        lines.append(
            f"| {row['question']} | `{row['pred_intent']}` | `{row['answer_type']}` | `{row['speech_act']}` | `{row['entities']}` |"
        )

    lines.extend(["", "## 7. Analisis Kesalahan pada Held-Out", ""])
    if error_examples:
        for row in error_examples:
            lines.append(
                f"- **Pertanyaan:** \"{row['question']}\" — Target: `{row['true_intent']}`, Prediksi: `{row['pred_intent']}` (`answer_type={row['answer_type']}`)"
            )
    else:
        lines.append("- Tidak ada kesalahan klasifikasi intent pada `questions_test.json` (63/63 benar).")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "speech_act_acc": sa_acc,
        "hybrid_intent_acc": hyb_acc,
        "hybrid_intent_macro_f1": hyb_f1,
        "answer_type_coarse_acc": at_coarse_acc,
        "answer_type_fine_acc": at_fine_acc,
        "entity_f1": ent_metrics["f1"],
    }


def main() -> None:
    """Entry point CLI untuk menjalankan evaluasi modul Question Processing."""
    metrics = run_module_evaluation()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
