"""Pengujian modul Question Processing & NLP Analysis (Anggota 3)."""

from src.question_processing import (
    answer_type_detector,
    entity_extractor,
    query_formulator,
    question_classifier,
    question_processor,
)


def test_question_processing_module_imports() -> None:
    assert hasattr(question_processor, "process_question")
    assert hasattr(question_classifier, "detect_speech_act")
    assert hasattr(question_classifier, "classify_question")
    assert hasattr(question_classifier, "train_question_classifier")
    assert hasattr(entity_extractor, "extract_entities")
    assert hasattr(entity_extractor, "detect_focus")
    assert hasattr(entity_extractor, "extract_relations")
    assert hasattr(answer_type_detector, "detect_answer_type")
    assert hasattr(query_formulator, "pos_tag_question")
    assert hasattr(query_formulator, "formulate_query")
