"""Pembentukan unit passage terstruktur dan Knowledge Triples (Hybrid KB-QA)."""

from typing import Any

from src.contracts import KnowledgeTriple, PassageRecord


def build_passages(extracted_items: list[dict[str, Any]]) -> list[PassageRecord]:
    """Mengubah hasil ekstraksi (teks, tabel, visual) menjadi list PassageRecord.

    Menangani penggabungan tabel/silabus lintas halaman, konversi tanda centang,
    serta penyimpanan `pdf_page`, `doc_page`, `tokens`, dan `stemmed_text`.
    """
    raise NotImplementedError("Anggota 2: implementasikan pembentukan passage di sini.")


def build_knowledge_triples(extracted_items: list[dict[str, Any]]) -> list[KnowledgeTriple]:
    """Membangun RDF-like triples `(subject, predicate, object)` dari tabel & transkripsi visual.

    Contoh triple:
    - subject: "CIF63110", predicate: "nama_mk", object: "Kecerdasan Artifisial"
    - subject: "CIF63110", predicate: "sks", object: 3
    - subject: "CIF63110", predicate: "prasyarat", object: "..."
    - subject: "NLP", predicate: "learning_path_course", object: "Pemrosesan Bahasa Alami"
    """
    raise NotImplementedError("Anggota 2: implementasikan pembangunan knowledge triples dari tabel/visual di sini.")
