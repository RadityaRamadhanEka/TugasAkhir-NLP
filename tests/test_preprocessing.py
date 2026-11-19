"""Pengujian modul Preprocessing, Passage Builder, & Knowledge Triples (Anggota 2)."""

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
