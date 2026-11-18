"""Pengujian modul Preprocessing & Passage Builder (Anggota 2)."""

from src.preprocessing import corpus_validator, passage_builder, preprocessing


def test_preprocessing_module_imports() -> None:
    assert hasattr(preprocessing, "clean_text")
    assert hasattr(preprocessing, "normalize_text")
    assert hasattr(passage_builder, "build_passages")
    assert hasattr(corpus_validator, "validate_corpus")
