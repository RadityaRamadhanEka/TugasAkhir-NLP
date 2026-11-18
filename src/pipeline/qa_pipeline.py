"""Orkestrasi alur QA end-to-end: Question Processing -> Retrieval -> Answer Extraction."""

from typing import Any

from config.settings import DEFAULT_TOP_K
from src.answer_processing.answer_extractor import extract_answer_candidates
from src.answer_processing.answer_ranker import select_best_answer
from src.contracts import AnswerOutput
from src.question_processing.question_processor import process_question
from src.retrieval.retriever import retrieve_passages


def answer_question(
    question: str,
    index: Any,
    top_k: int = DEFAULT_TOP_K,
) -> AnswerOutput:
    """Menjalankan pipeline QA penuh untuk satu pertanyaan pengguna."""
    q_analysis = process_question(question)
    retrieval_result = retrieve_passages(q_analysis, index=index, top_k=top_k)
    candidates = extract_answer_candidates(q_analysis, retrieval_result)
    return select_best_answer(q_analysis, candidates)
