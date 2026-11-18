"""Ekstraksi entitas pertanyaan (kode MK, nama MK, semester, SKS, learning path, CPL)."""

from src.contracts import ExtractedEntity


def extract_entities(question: str) -> list[ExtractedEntity]:
    """Mengekstrak entitas relevan dari teks pertanyaan."""
    raise NotImplementedError("Anggota 3: implementasikan ekstraksi entitas di sini.")
