"""Ekstraksi tabel kurikulum (mata kuliah, SKS, semester, prasyarat, CPL, peralihan)."""

from pathlib import Path
from typing import Any


def extract_tables(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Mengekstrak tabel dari PDF beserta judul tabel, `pdf_page`, dan `doc_page`.

    Returns:
        List dict berisi `pdf_page`, `doc_page`, `section`, `table_title`,
        `headers`, `rows`, dan `content_type="table"`.
    """
    raise NotImplementedError("Anggota 1: implementasikan ekstraksi tabel di sini.")
