"""Pemeringkatan kandidat jawaban (8 Fitur PBA14 Slide 62), Confidence Merging, & Fallback."""

import re

from config.settings import DEFAULT_ANSWER_TOP_M, MIN_CONFIDENCE_THRESHOLD
from src.contracts import AnswerCandidate, AnswerOutput, QuestionAnalysis

# 8 Fitur Pemeringkatan Kandidat Jawaban (PBA14 Slide 62):
# 1. answer_type_match    : Kandidat cocok dengan expected answer_type
# 2. pattern_match        : Kandidat cocok dengan pola regex answer-type
# 3. question_keywords    : Jumlah keyword pertanyaan di sekitar kandidat
# 4. keyword_distance     : Jarak kata antara kandidat dan query keywords
# 5. novelty_factor       : Kata pada kandidat BUKAN pengulangan kata dalam query
# 6. apposition_feature   : Kandidat adalah apositif terhadap term pertanyaan (mis. "CIF63110 (KA)")
# 7. punctuation_location : Kandidat diikuti koma, titik, kutip, atau titik koma
# 8. question_term_seq    : Panjang urutan term pertanyaan terpanjang di sekitar kandidat
#
# Bobot terbesar diberikan ke fitur yang paling membedakan kandidat benar dan salah
# (fitur 1 & 2). Fitur yang nilainya hampir selalu sama untuk semua kandidat
# (tanda baca, aposisi) hanya jadi bonus kecil. retrieval_score adalah tambahan
# di luar 8 fitur: skor passage dari Modul 4 (fakta tabel diberi 1.0).
FEATURE_WEIGHTS = {
    "answer_type_match": 0.30,
    "pattern_match": 0.20,
    "question_keywords": 0.10,
    "keyword_distance": 0.10,
    "retrieval_score": 0.10,
    "novelty_factor": 0.05,
    "question_term_seq": 0.05,
    "punctuation_location": 0.05,
    "apposition_feature": 0.05,
}

# Confidence merging: tiap sumber lain yang memberi jawaban sama menambah sedikit skor,
# dibatasi supaya jawaban yang sering muncul tidak otomatis menang
MERGE_BONUS_PER_SOURCE = 0.03
MAX_MERGE_BONUS = 0.10

NOT_FOUND_MESSAGE = "Maaf, jawaban tidak ditemukan atau bukti di dokumen tidak cukup."


def _answer_key(answer: str) -> str:
    """Bentuk sederhana jawaban untuk mengenali kandidat yang isinya sama."""
    text = re.sub(r"[^a-z0-9\s]", " ", str(answer).lower())
    return re.sub(r"\s+", " ", text).strip()


def _source_key(candidate: AnswerCandidate) -> str:
    source = candidate.get("source") or {}
    return str(source.get("triple_id") or source.get("passage_id") or source.get("pdf_page"))


def score_candidate(candidate: AnswerCandidate) -> float:
    """Skor dasar = jumlah (bobot x nilai fitur). Hasilnya 0 sampai 1."""
    features = candidate.get("features", {})
    return sum(weight * float(features.get(name, 0.0)) for name, weight in FEATURE_WEIGHTS.items())


def rank_answer_candidates(
    question_analysis: QuestionAnalysis,
    candidates: list[AnswerCandidate],
) -> list[AnswerCandidate]:
    """Menggabungkan kandidat ekuivalen & memeringkat kandidat memakai fitur Slide 62 (+ KB confidence)."""
    groups: dict[str, list[AnswerCandidate]] = {}
    for candidate in candidates:
        key = _answer_key(candidate.get("answer", ""))
        if key:
            groups.setdefault(key, []).append(candidate)

    merged: list[AnswerCandidate] = []
    for group in groups.values():
        scored = sorted(group, key=score_candidate, reverse=True)
        best = dict(scored[0])  # kandidat terbaik jadi wakil, sumbernya dipakai sebagai bukti
        n_sources = len({_source_key(c) for c in group})
        bonus = min(MERGE_BONUS_PER_SOURCE * (n_sources - 1), MAX_MERGE_BONUS)

        best["features"] = {**best.get("features", {}), "supporting_sources": float(n_sources)}
        best["score"] = round(min(score_candidate(scored[0]) + bonus, 1.0), 4)
        merged.append(best)

    merged.sort(key=lambda c: c["score"], reverse=True)
    return merged


def select_best_answer(
    question_analysis: QuestionAnalysis,
    ranked_candidates: list[AnswerCandidate],
    min_confidence: float = MIN_CONFIDENCE_THRESHOLD,
    top_m: int = DEFAULT_ANSWER_TOP_M,
) -> AnswerOutput:
    """Memilih jawaban terbaik, menyertakan `top_candidates` (top-M untuk MRR), & fallback jika bukti kurang."""
    question = question_analysis.get("original_question", "")
    top_candidates = ranked_candidates[:top_m]

    if not top_candidates or top_candidates[0].get("score", 0.0) < min_confidence:
        return {
            "question": question,
            "answer": NOT_FOUND_MESSAGE,
            "answer_granularity": "long",
            "source": None,
            "confidence": round(top_candidates[0]["score"], 4) if top_candidates else 0.0,
            "status": "not_found",
            "top_candidates": top_candidates,
        }

    best = top_candidates[0]
    return {
        "question": question,
        "answer": best["answer"],
        "answer_granularity": best.get("answer_granularity", "short"),
        "source": best.get("source"),
        "confidence": best["score"],
        "status": "answered",
        "top_candidates": top_candidates,
    }
