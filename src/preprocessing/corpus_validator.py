"""Validasi kualitas dataset korpus (passage kosong, duplikat, metadata halaman, & triples)."""

from typing import Any

from src.contracts import KnowledgeTriple, PassageRecord


def validate_corpus(
    passages: list[PassageRecord],
    triples: list[KnowledgeTriple] | None = None,
) -> dict[str, Any]:
    """Memeriksa kualitas daftar passage & knowledge triples lalu mengembalikan laporan ringkas.

    Mengecek: passage kosong, duplikat, kelengkapan `pdf_page`/`doc_page`,
    distribusi `content_type`, serta integritas triple `(subject, predicate, object)`.
    """
    raise NotImplementedError("Anggota 2: implementasikan validasi korpus & knowledge triples di sini.")
