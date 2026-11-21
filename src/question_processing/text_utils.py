"""Utilitas normalisasi dan tokenisasi pertanyaan Bahasa Indonesia domain Kurikulum 2024."""

import re

TOKEN_RE = re.compile(
    r"[a-z]{3}\d{5}(?:-\d)?|if_cpl_[a-z0-9_]+|[a-z0-9]+/[a-z0-9]+|\d+(?:\.\d+)?|[a-z0-9]+"
)


def normalize_question(question: str) -> str:
    """Menormalisasi pertanyaan pengguna tanpa merusak kode MK, kode CPL, atau angka.

    Menghapus spasi berlebih dan tanda baca tepi, melakukan lowercase, serta membuang
    partikel enklitik berhubung tanda hubung seperti `-nya`.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Pertanyaan tidak boleh kosong.")

    text = question.strip().lower()
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"(?<=[a-z])-(?:nya|lah)\b", "", text)
    text = re.sub(r"\bif[\s_-]+cpl[\s_-]+([a-z]{1,2}\d)\b", r"if_cpl_\1", text)
    text = re.sub(r"[^\w\s/-]", " ", text)
    text = re.sub(r"(?<!\w)[/-]+|[/-]+(?!\w)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize_question(normalized_question: str) -> list[str]:
    """Memecah teks pertanyaan ter-normalisasi menjadi daftar token.

    Menjaga keutuhan kode MK (mis. `mpk60001-5`, `cif63110`), kode CPL (`if_cpl_kk1`),
    dan istilah bergaris miring (`ai/ml`).
    """
    cleaned = re.sub(r"(?<=[a-z])-(?:nya|lah)\b", "", normalized_question.lower())
    return TOKEN_RE.findall(cleaned)
