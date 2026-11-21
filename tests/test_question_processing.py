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


def test_course_lexicon_coverage_and_inconsistencies() -> None:
    from src.question_processing.resources import load_course_lexicon

    lex = load_course_lexicon()
    courses_2024 = lex["courses_2024"]
    courses_2020 = lex["courses_2020"]
    code_aliases = lex["code_aliases"]

    total_unique_codes = len(courses_2024) + len(courses_2020) + len(code_aliases)
    assert total_unique_codes >= 120
    assert courses_2024["CIF64311"]["name"] == "Kecerdasan Artifisial Lanjut"
    assert courses_2024["CIF63110"]["name"] == "Kecerdasan Artifisial"
    assert code_aliases["CIF63107"] == "CIF63106"
    assert courses_2024["CIF63106"]["name"] == "Analisis dan Perancangan Sistem"
    assert code_aliases["CIF60050"] == "CIF60048"
    assert courses_2024["CIF60048"]["name"] == "Machine Learning Operations (MLOps)"
    assert courses_2024["CIF61235"]["name"] == "Forensik Digital"
    assert courses_2020["CIF61011"]["equivalent_2024_code"] == "CIF63110"


def test_domain_lexicon_structure() -> None:
    from src.question_processing.resources import load_domain_lexicon

    dom = load_domain_lexicon()
    assert len(dom["learning_paths"]) == 11
    assert len(dom["cpl_codes"]) == 11
    assert len(dom["elective_groups"]) == 3
    for key in ("abbreviations", "synonyms", "wh_words", "command_words", "question_stopwords"):
        assert key in dom and len(dom[key]) > 0


def test_normalize_and_tokenize_question() -> None:
    import pytest
    from src.question_processing.text_utils import normalize_question, tokenize_question

    assert normalize_question("  Apa prasyarat KA Lanjut??  ") == "apa prasyarat ka lanjut"
    assert normalize_question("Apa isi IF_CPL_KK1?") == "apa isi if_cpl_kk1"
    assert tokenize_question("apa isi if_cpl_kk1") == ["apa", "isi", "if_cpl_kk1"]
    assert tokenize_question("kode mpk60001-5 dan cif63110") == [
        "kode",
        "mpk60001-5",
        "dan",
        "cif63110",
    ]
    assert tokenize_question("learning path ai/ml engineer") == [
        "learning",
        "path",
        "ai/ml",
        "engineer",
    ]
    assert tokenize_question("apa mk-nya di semester 3") == ["apa", "mk", "di", "semester", "3"]
    with pytest.raises(ValueError):
        normalize_question("   ")


def test_detect_speech_act_rules_and_traps() -> None:
    from src.question_processing.question_classifier import detect_speech_act

    assert detect_speech_act("Tolong jelaskan aturan peralihan semester 5!") == "indirect_request"
    assert detect_speech_act("Bisakah Anda sebutkan MK semester 3?") == "indirect_request"
    assert detect_speech_act("Bolehkah saya tahu prasyarat AI Lanjut?") == "indirect_request"
    assert detect_speech_act("Sebutkan mata kuliah pada semester 3!") == "command"
    assert detect_speech_act("Jelaskan isi IF_CPL_KK1") == "command"
    assert detect_speech_act("Apakah Sistem Operasi memiliki praktikum?") == "yes_no"
    assert detect_speech_act("Adakah praktikum pada Basis Data?") == "yes_no"
    assert detect_speech_act("Apa prasyarat Kecerdasan Artifisial Lanjut?") == "wh"
    assert detect_speech_act("brp sks apb?") == "wh"


def test_idn_corpus_multiword_splitter() -> None:
    from src.question_processing.train_pos_tagger import parse_idn_tsv

    sample_tsv = "<kalimat id=1>\npesta olahraga\tNN\n.\tZ\n</kalimat>\n"
    sentences = parse_idn_tsv(sample_tsv)
    assert sentences == [[("pesta", "NN"), ("olahraga", "NN"), (".", "Z")]]


def test_pos_tag_question_domain_overrides() -> None:
    from src.question_processing.query_formulator import pos_tag_question

    tagged = pos_tag_question(["apa", "prasyarat", "kecerdasan", "artifisial", "lanjut"])
    assert tagged == [
        ("apa", "WH"),
        ("prasyarat", "NN"),
        ("kecerdasan", "NNP"),
        ("artifisial", "NNP"),
        ("lanjut", "NNP"),
    ]
    tagged_code = pos_tag_question(["sebutkan", "sks", "cif63110", "semester", "3", "if_cpl_kk1"])
    tag_map = dict(tagged_code)
    assert tag_map["sebutkan"] == "VB"
    assert tag_map["cif63110"] == "NNP"
    assert tag_map["3"] == "CD"
    assert tag_map["if_cpl_kk1"] == "NNP"


def test_pos_tag_question_fallback_without_model(monkeypatch, tmp_path) -> None:
    import pytest
    from src.question_processing import query_formulator

    query_formulator._load_crf_tagger.cache_clear()
    monkeypatch.setattr(query_formulator, "_POS_MODEL_PATH", tmp_path / "missing.crfsuite")
    try:
        with pytest.warns(UserWarning):
            tagged = query_formulator.pos_tag_question(["apa", "sks", "basis", "data"])
        assert len(tagged) == 4
        assert tagged[0] == ("apa", "WH")
        assert tagged[2] == ("basis", "NNP")
        assert tagged[3] == ("data", "NNP")
    finally:
        query_formulator._load_crf_tagger.cache_clear()




