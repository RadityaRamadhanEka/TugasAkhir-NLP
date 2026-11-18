"""Pembentukan unit passage terstruktur lengkap dengan metadata sumber."""

from typing import Any

from src.contracts import PassageRecord


def build_passages(extracted_items: list[dict[str, Any]]) -> list[PassageRecord]:
    """Mengubah hasil ekstraksi (teks, tabel, visual) menjadi list PassageRecord."""
    raise NotImplementedError("Anggota 2: implementasikan pembentukan passage di sini.")
