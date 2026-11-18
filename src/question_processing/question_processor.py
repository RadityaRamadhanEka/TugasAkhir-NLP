"""Orkestrator modul Question Processing (tokenisasi, normalisasi, intent, entitas, answer type)."""

from src.contracts import QuestionAnalysis


def process_question(question: str) -> QuestionAnalysis:
    """Memproses pertanyaan pengguna menjadi representasi terstruktur QuestionAnalysis."""
    raise NotImplementedError("Anggota 3: hubungkan normalisasi, classifier, entity, dan answer type.")
