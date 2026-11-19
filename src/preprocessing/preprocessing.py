"""Pembersihan artefak PDF, tokenisasi, normalisasi, stopword selektif, dan stemming."""


def clean_text(raw_text: str) -> str:
    """Membersihkan artefak PDF (nomor halaman sisipan, spasi berlebih, artefak CPMK-1, pemenggalan baris)."""
    raise NotImplementedError("Anggota 2: implementasikan pembersihan artefak PDF di sini.")


def normalize_text(text: str) -> str:
    """Menormalisasi teks (case folding selektif, simbol centang, tanpa merusak kode MK/SKS/semester)."""
    raise NotImplementedError("Anggota 2: implementasikan normalisasi teks di sini.")


def tokenize_text(text: str) -> list[str]:
    """Memecah teks menjadi token dengan tetap menjaga kode MK (mis. CIF63110) & kode CPL."""
    raise NotImplementedError("Anggota 2: implementasikan tokenisasi regex/NLTK domain kurikulum di sini.")


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Menghapus stopword Bahasa Indonesia secara selektif (pertahankan negasi/angka/kode penting)."""
    raise NotImplementedError("Anggota 2: implementasikan penghapusan stopword selektif di sini.")


def stem_text(tokens: list[str]) -> str:
    """Melakukan stemming Bahasa Indonesia (Sastrawi) untuk keperluan indexing/retrieval.

    Catatan: Simpan hasil stemming di field `stemmed_text` dan tetap pertahankan `text` asli
    agar Answer Extraction tidak menghasilkan potongan kata yang rusak.
    """
    raise NotImplementedError("Anggota 2: implementasikan stemming Bahasa Indonesia (Sastrawi) di sini.")
