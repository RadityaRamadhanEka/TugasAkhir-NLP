"""Kontrak interface data antar-modul (sesuai Bagian 7 dokumen brief).

Gunakan tipe data ini sebagai acuan input-output agar setiap anggota dapat
mengembangkan modul secara paralel tanpa konflik format saat integrasi.
"""

from typing import Any, Literal, TypedDict


class PassageRecord(TypedDict, total=False):
    """Format standar satu unit passage korpus (Output Anggota 2, Input Anggota 4 & 5)."""

    passage_id: str
    text: str
    source_page: int
    section: str
    content_type: Literal["text", "table", "visual"]
    table_title: str | None
    metadata: dict[str, Any]


class ExtractedEntity(TypedDict):
    """Satu entitas yang diekstrak dari pertanyaan pengguna."""

    type: str
    value: str


class QuestionAnalysis(TypedDict):
    """Output dari modul Question Processing (Output Anggota 3, Input Anggota 4 & 5)."""

    original_question: str
    normalized_question: str
    intent: str
    entities: list[ExtractedEntity]
    answer_type: str


class RetrievedPassage(TypedDict, total=False):
    """Satu kandidat passage hasil retrieval."""

    passage_id: str
    score: float
    text: str
    source_page: int
    section: str
    content_type: str
    table_title: str | None
    metadata: dict[str, Any]


class RetrievalResult(TypedDict):
    """Output dari modul Passage Retrieval (Output Anggota 4, Input Anggota 5)."""

    query: str
    results: list[RetrievedPassage]


class AnswerSource(TypedDict, total=False):
    """Metadata sumber jawaban untuk verifikasi."""

    passage_id: str
    page: int
    section: str
    table_title: str | None


class AnswerOutput(TypedDict):
    """Output akhir sistem QA (Output Anggota 5)."""

    question: str
    answer: str
    source: AnswerSource | None
    confidence: float
    status: Literal["answered", "not_found"]
