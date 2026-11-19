"""Pengujian modul Passage Retrieval, Relation Retrieval, & Reranking (Anggota 4)."""

from src.retrieval import index_builder, ranking, retriever


def test_retrieval_module_imports() -> None:
    assert hasattr(index_builder, "build_index")
    assert hasattr(retriever, "retrieve_passages")
    assert hasattr(retriever, "retrieve_triples")
    assert hasattr(ranking, "extract_passage_ranking_features")
    assert hasattr(ranking, "rank_passages")
