"""Pengujian modul Answer Processing & Pipeline Integrasi (Anggota 5)."""

from src.answer_processing import answer_extractor, answer_ranker
from src.pipeline import evaluation, qa_pipeline


def test_answer_processing_module_imports() -> None:
    assert hasattr(answer_extractor, "extract_answer_candidates")
    assert hasattr(answer_ranker, "select_best_answer")
    assert hasattr(qa_pipeline, "answer_question")
    assert hasattr(evaluation, "run_evaluation")
