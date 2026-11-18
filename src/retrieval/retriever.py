"""Pencarian top-k passage relevan menggunakan skor retrieval klasik."""

from typing import Any

from src.contracts import QuestionAnalysis, RetrievalResult


def retrieve_passages(
    question_analysis: QuestionAnalysis,
    index: Any,
    top_k: int = 5,
) -> RetrievalResult:
    """Mengambil top-k passage paling relevan berdasarkan hasil analisis pertanyaan."""
    raise NotImplementedError("Anggota 4: implementasikan pencarian top-k passage di sini.")
