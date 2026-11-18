"""Pembuatan indeks retrieval (TF-IDF / BM25) dari dataset passage."""

from typing import Any

from src.contracts import PassageRecord


def build_index(passages: list[PassageRecord]) -> Any:
    """Membangun struktur indeks dari daftar passage korpus."""
    raise NotImplementedError("Anggota 4: implementasikan pembuatan indeks TF-IDF/BM25 di sini.")
