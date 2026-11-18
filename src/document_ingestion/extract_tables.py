"""Ekstraksi tabel kurikulum (mata kuliah, SKS, semester, prasyarat, dll.)."""

from pathlib import Path
from typing import Any


def extract_tables(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Mengekstrak tabel dari PDF beserta judul tabel dan nomor halaman.

    Returns:
        List dict berisi `source_page`, `table_title`, `headers`, `rows`, dan `content_type="table"`.
    """
    raise NotImplementedError("Anggota 1: implementasikan ekstraksi tabel di sini.")
