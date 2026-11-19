"""Pencarian top-k passage (IR-based) & relation retrieval dari Knowledge Base (Hybrid QA)."""

from typing import Any

from src.contracts import KnowledgeTriple, QuestionAnalysis, RetrievalResult


def retrieve_passages(
    question_analysis: QuestionAnalysis,
    index: Any,
    top_k: int = 5,
) -> RetrievalResult:
    """Mengambil top-k passage relevan (TF-IDF/BM25) + kandidat triple terstruktur bila tersedia.

    Menggunakan `query_keywords` dan `expanded_queries` dari QuestionAnalysis.
    """
    raise NotImplementedError("Anggota 4: implementasikan pencarian top-k passage di sini.")


def retrieve_triples(
    question_analysis: QuestionAnalysis,
    index: Any,
) -> list[KnowledgeTriple]:
    """Mencari fakta terstruktur `(subject, predicate, object)` sesuai entitas & relasi pertanyaan."""
    raise NotImplementedError("Anggota 4: implementasikan relation retrieval dari knowledge triples di sini.")
