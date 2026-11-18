"""Validasi kualitas dataset korpus (passage kosong, duplikat, metadata hilang)."""

from typing import Any

from src.contracts import PassageRecord


def validate_corpus(passages: list[PassageRecord]) -> dict[str, Any]:
    """Memeriksa kualitas daftar passage dan mengembalikan laporan ringkas."""
    raise NotImplementedError("Anggota 2: implementasikan validasi korpus di sini.")
