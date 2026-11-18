"""Pengujian modul Document Ingestion (Anggota 1)."""

from src.document_ingestion import (
    document_loader,
    extract_tables,
    extract_text,
    extract_visuals,
)


def test_ingestion_module_imports() -> None:
    assert hasattr(document_loader, "load_pdf_metadata")
    assert hasattr(extract_text, "extract_text_pages")
    assert hasattr(extract_tables, "extract_tables")
    assert hasattr(extract_visuals, "extract_visuals")
