"""Memuat file PDF pedoman kurikulum dan memeriksa struktur dasar dokumen."""

from pathlib import Path
from typing import Any


def load_pdf_metadata(pdf_path: str | Path) -> dict[str, Any]:
    """Memuat dokumen PDF dan mengembalikan informasi struktur dasar (jumlah halaman, dll.)."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File PDF tidak ditemukan: {path}")
    raise NotImplementedError("Anggota 1: implementasikan pembacaan metadata PDF di sini.")
