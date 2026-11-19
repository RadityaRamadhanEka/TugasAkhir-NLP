"""Kontrak interface data antar-modul (sesuai Brief & Audit Materi PBA14 QAS).

Gunakan tipe data ini sebagai single source of truth agar 5 anggota dapat
mengembangkan modul secara paralel tanpa konflik format saat integrasi.
"""

from typing import Any, Literal, TypedDict

AnswerTypeCoarse = Literal[
    "ABBREVIATION",
    "ENTITY",
    "DESCRIPTION",
    "HUMAN",
    "LOCATION",
    "NUMERIC",
]

SpeechActType = Literal["wh", "yes_no", "command", "indirect_request"]
QuestionCategory = Literal["factoid", "definition", "list", "narrative", "yes_no"]
AnswerGranularity = Literal["exact", "short", "long"]


class PassageRecord(TypedDict, total=False):
    """Format standar satu unit passage korpus (Output Anggota 2, Input Anggota 4 & 5)."""

    passage_id: str
    text: str
    stemmed_text: str
    tokens: list[str]
    pdf_page: int
    doc_page: str
    source_page: int  # alias backward-compatible untuk pdf_page
    section: str
    content_type: Literal["text", "table", "visual"]
    table_title: str | None
    metadata: dict[str, Any]


class KnowledgeTriple(TypedDict, total=False):
    """Representasi fakta terstruktur (subject, predicate, object) untuk Hybrid KB-QA.

    Dibangun Anggota 2 dari tabel kurikulum & transkripsi visual (Gambar 7.1-7.11),
    diambil oleh Anggota 4 (relation retrieval), dan digabungkan Anggota 5.
    """

    triple_id: str
    subject: str
    predicate: str
    object: Any
    pdf_page: int
    doc_page: str
    section: str
    table_title: str | None
    content_type: Literal["table", "visual"]
    metadata: dict[str, Any]


class ExtractedEntity(TypedDict, total=False):
    """Satu entitas yang diekstrak dari pertanyaan pengguna."""

    type: str
    value: str
    normalized_value: str


class ExtractedRelation(TypedDict):
    """Relasi antar entitas yang diekstrak dari pertanyaan (PBA14 Slide 35, 37, 69)."""

    predicate: str
    subject: str | None
    object: str | None


class QuestionAnalysis(TypedDict, total=False):
    """Output dari modul Question Processing (Output Anggota 3, Input Anggota 4 & 5).

    Mencakup 5 komponen PBA14 Slide 35: Answer Type Detection (taksonomi Li & Roth),
    Query Formulation & Expansion, Question Type & Speech Act Classification,
    Focus Detection (headword), dan Relation Extraction, plus POS tags.
    """

    original_question: str
    normalized_question: str
    tokens: list[str]
    pos_tags: list[tuple[str, str]]
    speech_act: SpeechActType
    question_category: QuestionCategory
    intent: str
    answer_type_coarse: AnswerTypeCoarse
    answer_type: str
    focus: str | None
    query_keywords: list[str]
    expanded_queries: list[str]
    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]


class RetrievedPassage(TypedDict, total=False):
    """Satu kandidat passage hasil retrieval & reranking."""

    passage_id: str
    score: float
    doc_rank: int
    rerank_score: float
    rerank_features: dict[str, float]
    text: str
    pdf_page: int
    doc_page: str
    source_page: int
    section: str
    content_type: str
    table_title: str | None
    metadata: dict[str, Any]


class RetrievalResult(TypedDict, total=False):
    """Output dari modul Passage & Relation Retrieval (Output Anggota 4, Input Anggota 5)."""

    query: str
    results: list[RetrievedPassage]
    structured_results: list[KnowledgeTriple]


class AnswerSource(TypedDict, total=False):
    """Metadata sumber jawaban untuk verifikasi (menyimpan pdf_page dan doc_page)."""

    passage_id: str | None
    triple_id: str | None
    pdf_page: int
    doc_page: str
    page: int  # alias backward-compatible untuk pdf_page
    section: str
    table_title: str | None
    source_type: Literal["text", "table", "visual", "knowledge_base"]


class AnswerCandidate(TypedDict, total=False):
    """Satu kandidat jawaban terstruktur beserta skor & fitur ranking (PBA14 Slide 62)."""

    answer: str
    answer_granularity: AnswerGranularity
    score: float
    extraction_method: Literal[
        "ner_tagger",
        "pattern_regex",
        "knowledge_base",
        "passage_fallback",
    ]
    features: dict[str, float]
    source: AnswerSource


class AnswerOutput(TypedDict, total=False):
    """Output akhir sistem QA (Output Anggota 5), termasuk top_candidates untuk MRR."""

    question: str
    answer: str
    answer_granularity: AnswerGranularity
    source: AnswerSource | None
    confidence: float
    status: Literal["answered", "not_found"]
    top_candidates: list[AnswerCandidate]
