"""POS Tagging pertanyaan, Query Formulation, Query Expansion, & Reformulation (PBA14 Slide 46-47)."""

from src.contracts import ExtractedEntity


def pos_tag_question(tokens: list[str]) -> list[tuple[str, str]]:
    """Memberi label Part-of-Speech (POS tag) pada token pertanyaan (CRF / NLTK / rule-based)."""
    raise NotImplementedError("Anggota 3: implementasikan POS tagging Bahasa Indonesia di sini.")


def formulate_query(
    normalized_question: str,
    tokens: list[str],
    entities: list[ExtractedEntity],
    pos_tags: list[tuple[str, str]] | None = None,
) -> tuple[list[str], list[str]]:
    """Menghasilkan `(query_keywords, expanded_queries)` untuk modul Passage Retrieval.

    Mencakup:
    - Seleksi query keywords (buang kata tanya & stopword yang tidak informatif)
    - Query expansion dengan sinonim/singkatan domain (mis. MK <-> mata kuliah, AI <-> kecerdasan artifisial)
    - Query reformulation ke pola deklaratif (ala Lin 2007, Slide 47)
    """
    raise NotImplementedError("Anggota 3: implementasikan query formulation & expansion di sini.")
