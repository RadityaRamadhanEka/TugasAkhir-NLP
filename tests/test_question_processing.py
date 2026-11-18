"""Pengujian modul Question Processing (Anggota 3)."""

from src.question_processing import (
    answer_type_detector,
    entity_extractor,
    question_classifier,
    question_processor,
)


def test_question_processing_module_imports() -> None:
    assert hasattr(question_processor, "process_question")
    assert hasattr(question_classifier, "classify_question")
    assert hasattr(entity_extractor, "extract_entities")
    assert hasattr(answer_type_detector, "detect_answer_type")
