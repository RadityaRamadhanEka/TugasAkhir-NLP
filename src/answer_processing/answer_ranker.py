"""Pemilihan jawaban terbaik, pelacakan sumber, dan mekanisme fallback."""

from typing import Any

from config.settings import MIN_CONFIDENCE_THRESHOLD
from src.contracts import AnswerOutput, QuestionAnalysis


def select_best_answer(
    question_analysis: QuestionAnalysis,
    candidates: list[dict[str, Any]],
    min_confidence: float = MIN_CONFIDENCE_THRESHOLD,
) -> AnswerOutput:
    """Memilih kandidat jawaban terbaik atau mengembalikan status not_found bila bukti kurang."""
    raise NotImplementedError("Anggota 5: implementasikan pemilihan jawaban & fallback di sini.")
