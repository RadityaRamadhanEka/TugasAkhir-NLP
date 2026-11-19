"""Pemeringkatan kandidat jawaban (8 Fitur PBA14 Slide 62), Confidence Merging, & Fallback."""

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


def rank_answer_candidates(
    question_analysis: QuestionAnalysis,
    candidates: list[AnswerCandidate],
) -> list[AnswerCandidate]:
    """Menggabungkan kandidat ekuivalen & memeringkat kandidat memakai fitur Slide 62 (+ KB confidence)."""
    raise NotImplementedError("Anggota 5: implementasikan ranking & confidence merging kandidat jawaban di sini.")


def select_best_answer(
    question_analysis: QuestionAnalysis,
    ranked_candidates: list[AnswerCandidate],
    min_confidence: float = MIN_CONFIDENCE_THRESHOLD,
    top_m: int = DEFAULT_ANSWER_TOP_M,
) -> AnswerOutput:
    """Memilih jawaban terbaik, menyertakan `top_candidates` (top-M untuk MRR), & fallback jika bukti kurang."""
    raise NotImplementedError("Anggota 5: implementasikan pemilihan jawaban terbaik & fallback di sini.")
