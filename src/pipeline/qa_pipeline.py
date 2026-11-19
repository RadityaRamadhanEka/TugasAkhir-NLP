"""Orkestrasi alur Hybrid QA end-to-end (PBA14 Slide 33 & 75).

Alur:
Question Processing -> Passage & Relation Retrieval -> Passage Reranking
-> Answer Extraction -> Candidate Answer Ranking & Confidence Merging -> AnswerOutput
"""

from typing import Any

from config.settings import DEFAULT_ANSWER_TOP_M, DEFAULT_TOP_K, MIN_CONFIDENCE_THRESHOLD
from src.answer_processing.answer_extractor import extract_answer_candidates
from src.answer_processing.answer_ranker import rank_answer_candidates, select_best_answer
from src.contracts import AnswerOutput
from src.question_processing.question_processor import process_question
from src.retrieval.ranking import rank_passages
from src.retrieval.retriever import retrieve_passages


def answer_question(
    question: str,
    index: Any,
    top_k: int = DEFAULT_TOP_K,
    top_m: int = DEFAULT_ANSWER_TOP_M,
    min_confidence: float = MIN_CONFIDENCE_THRESHOLD,
) -> AnswerOutput:
    """Menjalankan pipeline Hybrid QA penuh untuk satu pertanyaan pengguna."""
    q_analysis = process_question(question)
    retrieval_result = retrieve_passages(q_analysis, index=index, top_k=top_k)

    # Tahap Passage Reranking (PBA14 Slide 51-52)
    reranked_passages = rank_passages(retrieval_result.get("results", []), q_analysis)
    retrieval_result["results"] = reranked_passages

    # Tahap Answer Extraction, Candidate Ranking (Slide 62), & Selection (Top-M untuk MRR)
    candidates = extract_answer_candidates(q_analysis, retrieval_result)
    ranked_candidates = rank_answer_candidates(q_analysis, candidates)
    return select_best_answer(
        q_analysis,
        ranked_candidates,
        min_confidence=min_confidence,
        top_m=top_m,
    )
