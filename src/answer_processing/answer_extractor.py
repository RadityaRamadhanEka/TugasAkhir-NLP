"""Ekstraksi kandidat jawaban berbasis aturan/pola sesuai answer_type."""

from typing import Any

from src.contracts import QuestionAnalysis, RetrievalResult


def extract_answer_candidates(
    question_analysis: QuestionAnalysis,
    retrieval_result: RetrievalResult,
) -> list[dict[str, Any]]:
    """Mengekstrak kandidat jawaban beserta metadata sumber dari passage terpilih."""
    raise NotImplementedError("Anggota 5: implementasikan ekstraksi kandidat jawaban di sini.")
