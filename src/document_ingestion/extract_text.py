"""Ekstraksi teks per halaman beserta metadata sumber (`pdf_page`, `doc_page`, & bagian)."""

from pathlib import Path
from typing import Any


def extract_text_pages(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Mengekstrak teks per halaman dari PDF.

    Returns:
        List dict berisi minimal `pdf_page`, `doc_page`, `section`,
        `content_type="text"`, dan `text`.
    """
    raise NotImplementedError("Anggota 1: implementasikan ekstraksi teks per halaman di sini.")
