"""Inventarisasi gambar/diagram/grafik dan ekstraksi OCR/transkripsi terstruktur."""

from pathlib import Path
from typing import Any


def extract_visuals(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Menginventarisasi konten visual dan melakukan OCR/transkripsi bila diperlukan.

    Returns:
        List dict berisi `source_page`, `caption`, `relevant_for_qa`, `text`, dan `content_type="visual"`.
    """
    raise NotImplementedError("Anggota 1: implementasikan inventarisasi dan OCR visual di sini.")
