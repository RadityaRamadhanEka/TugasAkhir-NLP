"""Pengujian modul Question Processing & NLP Analysis (Anggota 3)."""

import json
from pathlib import Path

from src.question_processing import (
    answer_type_detector,
    entity_extractor,
    query_formulator,
    question_classifier,
    question_processor,
)

BASE_DIR = Path(__file__).resolve().parent.parent
FIXTURE_PATH = BASE_DIR / "tests" / "fixtures" / "question_analysis_samples.json"
EVAL_DRAFT_PATH = BASE_DIR / "data" / "question_processing" / "eval_q09_q12.json"

VALID_SPEECH_ACTS = {"wh", "yes_no", "command", "indirect_request"}
VALID_QUESTION_CATEGORIES = {"factoid", "definition", "list", "narrative", "yes_no"}
VALID_COARSE_TYPES = {
    "ABBREVIATION",
    "ENTITY",
    "DESCRIPTION",
    "HUMAN",
    "LOCATION",
    "NUMERIC",
}
REQUIRED_QA_KEYS = {
    "original_question",
    "normalized_question",
    "tokens",
    "pos_tags",
    "speech_act",
    "question_category",
    "intent",
    "answer_type_coarse",
    "answer_type",
    "focus",
    "query_keywords",
    "expanded_queries",
    "entities",
    "relations",
}


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


def test_fixture_samples_conform_to_contract() -> None:
    samples = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(samples) >= 10
    for item in samples:
        assert REQUIRED_QA_KEYS.issubset(item.keys())
        assert item["speech_act"] in VALID_SPEECH_ACTS
        assert item["question_category"] in VALID_QUESTION_CATEGORIES
        assert item["answer_type_coarse"] in VALID_COARSE_TYPES
        assert item["answer_type"].startswith(f"{item['answer_type_coarse']}:")
        assert len(item["pos_tags"]) == len(item["tokens"])
        assert len(item["expanded_queries"]) <= 5
        for rel in item["relations"]:
            assert {"predicate", "subject", "object"} == set(rel.keys())


def test_eval_q09_q12_draft_schema() -> None:
    items = json.loads(EVAL_DRAFT_PATH.read_text(encoding="utf-8"))
    assert [it["id"] for it in items] == ["Q09", "Q10", "Q11", "Q12"]
    for it in items:
        assert it["speech_act"] in VALID_SPEECH_ACTS
        assert it["question_category"] in VALID_QUESTION_CATEGORIES
        assert it["expected_answer_type_coarse"] in VALID_COARSE_TYPES
        assert it["expected_answer_type"].startswith(f"{it['expected_answer_type_coarse']}:")
        assert isinstance(it["source_pdf_page"], int)
        assert it["ground_truth"]

