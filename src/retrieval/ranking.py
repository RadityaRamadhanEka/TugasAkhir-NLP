"""Re-ranking kandidat passage menggunakan entitas, kode MK, atau sinyal tambahan."""

from src.contracts import QuestionAnalysis, RetrievedPassage


def rank_passages(
    candidates: list[RetrievedPassage],
    question_analysis: QuestionAnalysis,
) -> list[RetrievedPassage]:
    """Mengurutkan ulang kandidat passage berdasarkan kecocokan entitas dan skor relevansi."""
    raise NotImplementedError("Anggota 4: implementasikan ranking kandidat passage di sini.")
