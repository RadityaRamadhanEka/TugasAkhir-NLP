"""Ekstraksi entitas, relasi, dan Focus Detection / Question Headword (PBA14 Slide 35-37, 44)."""

from src.contracts import ExtractedEntity, ExtractedRelation


def extract_entities(question: str) -> list[ExtractedEntity]:
    """Mengekstrak entitas domain kurikulum (kode MK, nama MK, semester, SKS, learning path, CPL)."""
    raise NotImplementedError("Anggota 3: implementasikan ekstraksi entitas di sini.")


def detect_focus(
    tokens: list[str],
    pos_tags: list[tuple[str, str]] | None = None,
) -> str | None:
    """Mendeteksi question focus / headword (frasa NP setelah wh-word yang digantikan jawaban)."""
    raise NotImplementedError("Anggota 3: implementasikan focus/headword detection (Slide 36, 44) di sini.")


def extract_relations(
    question: str,
    entities: list[ExtractedEntity],
    pos_tags: list[tuple[str, str]] | None = None,
) -> list[ExtractedRelation]:
    """Mengekstrak relasi semantik dari pertanyaan (mis. `prasyarat(MK, ?x)`, `sks(MK, ?x)`)."""
    raise NotImplementedError("Anggota 3: implementasikan relation extraction pertanyaan (Slide 35, 69) di sini.")
