"""Pengujian modul Preprocessing, Passage Builder, & Knowledge Triples (Anggota 2)."""

from config.settings import EXTRACTED_DATA_DIR
from src.preprocessing import corpus_validator, passage_builder, preprocessing


def test_preprocessing_module_imports() -> None:
    assert hasattr(preprocessing, "clean_text")
    assert hasattr(preprocessing, "normalize_text")
    assert hasattr(preprocessing, "tokenize_text")
    assert hasattr(preprocessing, "remove_stopwords")
    assert hasattr(preprocessing, "stem_text")
    assert hasattr(passage_builder, "build_passages")
    assert hasattr(passage_builder, "build_knowledge_triples")
    assert hasattr(corpus_validator, "validate_corpus")


def test_clean_and_normalize_preserve_domain_codes() -> None:
    raw = (
        "CPMK-5: Memahami machine learning (CPL: ) \n"
        "CPMK-1 (%): CPMK-2 (%) (CPL: CPMK-5 (%))\n"
        "Syarat ≥ 60 SKS, kode MK CIF63110, MPK60001-5, CPL-3IF_CPL_KK2, Praktikum: ✓"
    )
    cleaned = preprocessing.clean_text(raw)
    assert "CPMK-1 (%)" not in cleaned
    assert "(CPL: )" not in cleaned
    assert "IF_CPL_KK2" in cleaned
    assert "CIF63110" in cleaned
    assert "MPK60001-5" in cleaned

    normalized = preprocessing.normalize_text(cleaned)
    assert ">= 60 SKS" in normalized
    assert "CIF63110" in normalized
    assert "MPK60001-5" in normalized
    assert "IF_CPL_KK2" in normalized
    assert "ya" in normalized


def test_tokenize_selective_stopwords_and_stemming() -> None:
    sample = "Mahasiswa wajib tidak mengambil mata kuliah CIF63110 dan IF_CPL_S1 minimal 3 SKS untuk pembelajaran."
    tokens = preprocessing.tokenize_text(sample)
    assert "cif63110" in tokens
    assert "mpk60001-5" not in tokens
    assert "if_cpl_s1" in tokens

    filtered = preprocessing.remove_stopwords(tokens)
    # Negasi, syarat, angka, dan kode domain tetap dipertahankan
    for must_keep in ("wajib", "tidak", "minimal", "3", "sks", "cif63110", "if_cpl_s1"):
        assert must_keep in filtered
    # Stopword umum dihapus
    assert "dan" not in filtered
    assert "untuk" not in filtered

    stemmed = preprocessing.stem_text(filtered)
    stemmed_tokens = stemmed.split()
    assert "cif63110" in stemmed_tokens
    assert "if_cpl_s1" in stemmed_tokens
    assert "sks" in stemmed_tokens
    assert "ajar" in stemmed_tokens  # "pembelajaran" ter-stem tanpa merusak kode MK


def test_build_passages_merges_continuations_and_preserves_text() -> None:
    items = passage_builder.load_extracted_items(EXTRACTED_DATA_DIR)
    passages = passage_builder.build_passages(items)
    triples = passage_builder.build_knowledge_triples(items)

    report = corpus_validator.validate_corpus(passages, triples)
    assert report["is_valid"] is True
    assert set(report["content_type_distribution"].keys()) == {"table", "text", "visual"}

    # Pastikan penggabungan silabus lintas halaman COM60014 (hal. 50 -> 51) menyatukan Deskripsi & Bahan Kajian
    com14 = [
        p
        for p in passages
        if p["content_type"] == "table"
        and p["metadata"].get("table_type") == "syllabus_card"
        and p["metadata"].get("course_code") == "COM60014"
    ]
    assert len(com14) == 1
    assert "Deskripsi Mata Kuliah:" in com14[0]["text"]
    assert "Bahan Kajian:" in com14[0]["text"]
    assert "CPMK-1 (%)" not in com14[0]["text"]

    # Pastikan dua MK berbeda dengan kode CIF61235 (Administrasi Sistem Server & Forensik Digital) tidak tertimpa
    cif61235 = [
        p
        for p in passages
        if p["content_type"] == "table"
        and p["metadata"].get("table_type") == "syllabus_card"
        and p["metadata"].get("course_code") == "CIF61235"
    ]
    assert len(cif61235) == 2

    # Cek duplikasi doc_page="6" pada pdf_page 13 dan 14 tetap dibedakan
    p13 = [p for p in passages if p["pdf_page"] == 13]
    p14 = [p for p in passages if p["pdf_page"] == 14]
    assert p13 and all(p["doc_page"] == "6" for p in p13)
    assert p14 and all(p["doc_page"] == "6" for p in p14)

    # Cek knowledge triples kunci sesuai vocabulary GATE-A
    assert any(
        t["predicate"] == "prerequisite_of"
        and "Kecerdasan Artifisial Lanjut" in t["subject"]
        and "CIF63110" in str(t["object"])
        for t in triples
    )
    assert any(
        t["predicate"] == "min_grade"
        and t["subject"] == "Kecerdasan Artifisial Lanjut"
        and t["object"] == "C"
        for t in triples
    )
    assert any(
        t["predicate"] == "learning_path_member"
        and t["subject"] == "Pemrosesan Bahasa Alami"
        and t["object"] == "NLP Engineer"
        for t in triples
    )
    assert any(
        t["predicate"] == "total_sks"
        and t["subject"] == "muatan program studi"
        and t["object"] == 75
        for t in triples
    )
