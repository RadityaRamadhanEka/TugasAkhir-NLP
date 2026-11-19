"""Pengujian modul Answer Processing, Pipeline Integrasi, & Metrik Evaluasi (Anggota 5)."""

import pytest

from src.answer_processing import answer_extractor, answer_ranker
from src.pipeline import evaluation, qa_pipeline


def test_answer_processing_module_imports() -> None:
    assert hasattr(answer_extractor, "extract_answer_candidates")
    assert hasattr(answer_ranker, "rank_answer_candidates")
    assert hasattr(answer_ranker, "select_best_answer")
    assert hasattr(qa_pipeline, "answer_question")
    assert hasattr(evaluation, "compute_accuracy")
    assert hasattr(evaluation, "compute_mrr")
    assert hasattr(evaluation, "run_evaluation")


def test_compute_accuracy() -> None:
    assert evaluation.compute_accuracy([]) == 0.0
    assert evaluation.compute_accuracy([True, False, True, True]) == pytest.approx(0.75)


def test_compute_mrr() -> None:
    assert evaluation.compute_mrr([]) == 0.0
    # Contoh PBA14 Slide 64: rank 1 -> 1.0, rank 2 -> 0.5, rank 3 -> 1/3, tidak ketemu -> 0.0
    expected = (1.0 + 0.5 + (1.0 / 3.0) + 0.0) / 4.0
    assert evaluation.compute_mrr([1, 2, 3, None]) == pytest.approx(expected)
    assert evaluation.compute_mrr([1, 0]) == pytest.approx(0.5)
