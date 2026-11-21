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


def test_extract_entities_all_types_and_longest_match() -> None:
    from src.question_processing.entity_extractor import extract_entities

    # Longest match: Kecerdasan Artifisial Lanjut must NOT also emit Kecerdasan Artifisial
    ents_kal = extract_entities("Apa prasyarat Kecerdasan Artifisial Lanjut?")
    assert [(e["type"], e["normalized_value"]) for e in ents_kal] == [
        ("course_name", "Kecerdasan Artifisial Lanjut")
    ]

    # Alias + code normalization
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("prasyarat ka lanjut")] == [
        ("course_name", "Kecerdasan Artifisial Lanjut")
    ]
    assert extract_entities("kode cif63110 dan mpk60001-5") == [
        {"type": "course_code", "value": "cif63110", "normalized_value": "CIF63110"},
        {"type": "course_code", "value": "mpk60001-5", "normalized_value": "MPK60001-5"},
    ]

    # Semester variants (digit, Indonesian word, Roman numeral, antara)
    assert extract_entities("semester tiga")[0]["normalized_value"] == "3"
    assert extract_entities("semester iv")[0]["normalized_value"] == "4"
    assert extract_entities("semester antara")[0]["normalized_value"] == "antara"

    # SKS, CPL, learning path, elective group, grade, curriculum_year, abbreviation
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("minimal 3 sks")] == [
        ("sks_value", "3")
    ]
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("isi cpl kk1")] == [
        ("cpl_code", "IF_CPL_KK1")
    ]
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("learning path data science")] == [
        ("learning_path", "Data Scientist")
    ]
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("front end developer")] == [
        ("learning_path", "Frontend Developer")
    ]
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("kelompok perekayasa komputasi cerdas")] == [
        ("elective_group", "Perekayasa Komputasi Cerdas")
    ]
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("nilai minimal c kurikulum 2020 dan 2024")] == [
        ("grade", "C"),
        ("curriculum_year", "2020"),
        ("curriculum_year", "2024"),
    ]
    assert [(e["type"], e["normalized_value"]) for e in extract_entities("kepanjangan mbkm")] == [
        ("abbreviation", "MBKM")
    ]


def test_detect_focus_four_patterns_and_fallback() -> None:
    from src.question_processing.entity_extractor import detect_focus
    from src.question_processing.query_formulator import pos_tag_question
    from src.question_processing.text_utils import normalize_question, tokenize_question

    def focus_of(q: str) -> str | None:
        toks = tokenize_question(normalize_question(q))
        tags = pos_tag_question(toks)
        return detect_focus(toks, tags)

    assert focus_of("Apa prasyarat Kecerdasan Artifisial Lanjut?") == "prasyarat"
    assert focus_of("Berapa SKS mata kuliah Basis Data?") == "sks"
    assert focus_of("Berapa nilai minimum prasyarat Jaringan Saraf Tiruan?") == "nilai minimum prasyarat"
    assert focus_of("Apa kode MK untuk Kecerdasan Artifisial?") == "kode mk"
    assert focus_of("Apa isi capaian pembelajaran IF_CPL_KK1?") == "isi capaian pembelajaran"
    assert focus_of("Mata kuliah apa saja pada learning path NLP Engineer?") == "mata kuliah"
    assert focus_of("Sebutkan mata kuliah pada semester 3!") == "mata kuliah"
    assert focus_of("Tolong jelaskan aturan peralihan untuk mahasiswa semester 3!") == "aturan peralihan"
    assert focus_of("Apakah Sistem Operasi memiliki praktikum?") == "praktikum"
    assert focus_of("Learning path apa saja yang tersedia?") == "learning path"
    assert focus_of("Apa visi program studi Teknik Informatika?") == "visi program studi"
    assert focus_of("Bagaimana kalau tidak lulus?") is None


def test_extract_relations_cases() -> None:
    from src.question_processing.entity_extractor import extract_entities, extract_relations

    def rels_of(q: str):
        ents = extract_entities(q)
        return extract_relations(q, ents)

    assert rels_of("Apa prasyarat Kecerdasan Artifisial Lanjut?") == [
        {"predicate": "prerequisite_of", "subject": "Kecerdasan Artifisial Lanjut", "object": None}
    ]
    assert rels_of("Berapa SKS Basis Data?") == [
        {"predicate": "sks", "subject": "Basis Data", "object": None}
    ]
    assert rels_of("Mata kuliah Sistem Operasi diambil pada semester berapa?") == [
        {"predicate": "semester", "subject": "Sistem Operasi", "object": None}
    ]
    assert rels_of("Sebutkan mata kuliah pada semester 3!") == [
        {"predicate": "semester", "subject": None, "object": "3"}
    ]
    assert rels_of("Apakah Sistem Operasi memiliki praktikum?") == [
        {"predicate": "has_practicum", "subject": "Sistem Operasi", "object": None}
    ]
    assert rels_of("Mata kuliah apa saja pada learning path NLP Engineer?") == [
        {"predicate": "learning_path_member", "subject": None, "object": "NLP Engineer"}
    ]
    assert rels_of("MK pilihan kelompok Perekayasa Komputasi Cerdas") == [
        {"predicate": "elective_group_member", "subject": None, "object": "Perekayasa Komputasi Cerdas"}
    ]
    assert rels_of("MK 2024 apa yang setara dengan CIF61011?") == [
        {"predicate": "equivalent_to", "subject": "CIF61011", "object": None}
    ]
    assert rels_of("Apa kode MK untuk Kecerdasan Artifisial?") == [
        {"predicate": "course_code", "subject": "Kecerdasan Artifisial", "object": None}
    ]


def test_no_train_test_data_leakage() -> None:
    from src.question_processing.resources import load_test_questions, load_training_questions
    from src.question_processing.text_utils import normalize_question

    train = load_training_questions()
    test = load_test_questions()
    assert 200 <= len(train) <= 320
    assert 50 <= len(test) <= 80

    train_norm = {normalize_question(item["question"]) for item in train}
    test_norm = {normalize_question(item["question"]) for item in test}
    assert train_norm.isdisjoint(test_norm)

    # Pastikan tiap intent memiliki >= 10 sampel latih dan >= 2 sampel uji
    from collections import Counter

    train_counts = Counter(item["intent"] for item in train)
    test_counts = Counter(item["intent"] for item in test)
    assert len(train_counts) >= 20
    assert min(train_counts.values()) >= 10
    assert min(test_counts.values()) >= 2


def test_hybrid_classifier_and_answer_type() -> None:
    from src.question_processing.answer_type_detector import detect_answer_type
    from src.question_processing.question_classifier import (
        classify_question,
        detect_speech_act,
        train_question_classifier,
    )
    from src.question_processing.resources import load_training_questions

    samples = load_training_questions()
    model = train_question_classifier(samples)
    assert model is not None

    cases = [
        ("Apa prasyarat Kecerdasan Artifisial Lanjut?", "course_prerequisite", "factoid", "ENTITY", "ENTITY:prerequisite"),
        ("brp sks papb?", "course_sks", "factoid", "NUMERIC", "NUMERIC:count"),
        ("Basis Data diambil semester berapa?", "course_semester", "factoid", "NUMERIC", "NUMERIC:order"),
        ("Berapa nilai minimum prasyarat Jaringan Saraf Tiruan?", "course_min_grade", "factoid", "NUMERIC", "NUMERIC:grade"),
        ("Apa kode MK Basis Data?", "course_code", "factoid", "NUMERIC", "NUMERIC:code"),
        ("Mata kuliah apa yang berkode CIF63110?", "course_name", "factoid", "ENTITY", "ENTITY:course_name"),
        ("Apakah Sistem Operasi memiliki praktikum?", "course_practicum", "yes_no", "DESCRIPTION", "DESCRIPTION:yes_no"),
        ("Sebutkan mata kuliah pada semester 3!", "course_list_semester", "list", "ENTITY", "ENTITY:course_list"),
        ("MK pilihan kelompok Perekayasa Komputasi Cerdas apa saja?", "elective_group", "list", "ENTITY", "ENTITY:course_list"),
        ("MK apa saja di learning path NLP Engineer?", "learning_path", "list", "ENTITY", "ENTITY:course_list"),
        ("Learning path apa saja yang tersedia?", "learning_path_list", "list", "ENTITY", "ENTITY:learning_path"),
        ("Berapa total SKS mata kuliah muatan program studi?", "total_sks", "factoid", "NUMERIC", "NUMERIC:count"),
        ("Bagaimana aturan peralihan untuk mahasiswa semester 5?", "curriculum_transition", "narrative", "DESCRIPTION", "DESCRIPTION:manner"),
        ("MK 2024 apa yang setara dengan CIF61011?", "course_equivalence", "factoid", "ENTITY", "ENTITY:course_name"),
        ("Apa isi IF_CPL_KK1?", "cpl", "definition", "DESCRIPTION", "DESCRIPTION:definition"),
        ("Apa saja profil lulusan Teknik Informatika?", "graduate_profile", "list", "HUMAN", "HUMAN:title"),
        ("Apa visi program studi Teknik Informatika?", "vision_mission", "definition", "DESCRIPTION", "DESCRIPTION:definition"),
        ("Apa yang dipelajari pada mata kuliah Komputer Grafis?", "course_description", "definition", "DESCRIPTION", "DESCRIPTION:definition"),
        ("Apa saja bentuk kegiatan Merdeka Belajar?", "mbkm", "list", "ENTITY", "ENTITY:other"),
        ("Apa kepanjangan MBKM?", "abbreviation", "definition", "ABBREVIATION", "ABBREVIATION:expansion"),
        ("Siapa rektor Universitas Brawijaya saat ini?", "other", "factoid", "HUMAN", "HUMAN:individual"),
    ]

    for q, exp_intent, exp_cat, exp_coarse, exp_fine in cases:
        sa = detect_speech_act(q)
        intent, cat = classify_question(q, speech_act=sa, classifier_model=model)
        assert intent == exp_intent, f"Intent salah untuk {q}: dapat {intent}"
        assert cat == exp_cat, f"Kategori salah untuk {q}: dapat {cat}"
        coarse, fine = detect_answer_type(q, intent)
        assert coarse == exp_coarse, f"Coarse salah untuk {q}: dapat {coarse}"
        assert fine == exp_fine, f"Fine salah untuk {q}: dapat {fine}"
        assert fine.startswith(f"{coarse}:")






