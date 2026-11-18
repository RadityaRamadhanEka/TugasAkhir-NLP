"""Pembersihan artefak PDF dan normalisasi teks tanpa merusak kode MK/SKS/semester."""


def clean_text(raw_text: str) -> str:
    """Membersihkan artefak PDF (nomor halaman sisipan, spasi berlebih, pemenggalan baris)."""
    raise NotImplementedError("Anggota 2: implementasikan pembersihan artefak PDF di sini.")


def normalize_text(text: str) -> str:
    """Menormalisasi teks untuk kebutuhan korpus dan retrieval."""
    raise NotImplementedError("Anggota 2: implementasikan normalisasi teks di sini.")
