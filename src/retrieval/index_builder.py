"""Pembuatan indeks retrieval klasik (TF-IDF / BM25) & indeks Knowledge Triples."""

from typing import Any, Literal

from src.contracts import KnowledgeTriple, PassageRecord


def build_index(
    passages: list[PassageRecord],
    method: Literal["bm25", "tfidf"] = "bm25",
    triples: list[KnowledgeTriple] | None = None,
) -> Any:
    """Membangun struktur indeks dari daftar passage korpus (+ opsional indeks knowledge triples).

    Mendukung perbandingan metode retrieval klasik `bm25` dan `tfidf` (cosine similarity)
    serta menyimpan lookup terstruktur untuk cabang Hybrid Knowledge-Based QA (Slide 75).
    """
    raise NotImplementedError("Anggota 4: implementasikan pembuatan indeks TF-IDF/BM25 & KB triples di sini.")
