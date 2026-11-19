"""Inventarisasi gambar/diagram/grafik dan ekstraksi OCR/transkripsi terstruktur."""

from pathlib import Path
from typing import Any


def extract_visuals(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Menginventarisasi konten visual dan melakukan OCR/transkripsi (prioritas Gambar 7.1-7.11).

    Returns:
        List dict berisi `pdf_page`, `doc_page`, `section`, `caption`,
        `relevant_for_qa`, `text`, `structured_records` (opsional), dan `content_type="visual"`.
    """
    raise NotImplementedError("Anggota 1: implementasikan inventarisasi dan OCR/transkripsi visual di sini.")
