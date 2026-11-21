"""Memuat file PDF pedoman kurikulum, memeriksa struktur dasar, & orkestrasi ingestion.

Modul ini merupakan entry point inspeksi metadata dan pelaporan kualitas ekstraksi
untuk Anggota 1 (`src/document_ingestion/`).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

from config.settings import DEFAULT_RAW_PDF, EXTRACTED_DATA_DIR
from src.document_ingestion.extract_tables import DEFAULT_TABLES_OUTPUT, extract_tables
from src.document_ingestion.extract_text import (
    DEFAULT_TEXT_OUTPUT,
    FOOTER_HEIGHT_PT,
    _normalize_whitespace,
    _update_section_state,
    extract_text_pages,
)
from src.document_ingestion.extract_visuals import DEFAULT_VISUALS_OUTPUT, extract_visuals

DEFAULT_METADATA_OUTPUT = EXTRACTED_DATA_DIR / "document_metadata.json"
DEFAULT_REPORT_OUTPUT = EXTRACTED_DATA_DIR / "extraction_report.json"


def _extract_doc_page_fitz(page: pymupdf.Page, pdf_page: int) -> str | None:
    """Mengambil nomor halaman tercetak (`doc_page`) dari area footer halaman."""
    if pdf_page == 1:
        return None
    h = float(page.rect.height)
    w = float(page.rect.width)
    footer_rect = pymupdf.Rect(0.0, max(0.0, h - FOOTER_HEIGHT_PT), w, h)
    footer_txt = re.sub(r"\s+", "", page.get_text("text", clip=footer_rect) or "")
    if re.fullmatch(r"([ivxlcdm]+|\d+)", footer_txt, flags=re.IGNORECASE):
        return footer_txt
    return None


def load_pdf_metadata(
    pdf_path: str | Path = DEFAULT_RAW_PDF,
    *,
    save_output: bool = False,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Memuat dokumen PDF dan mengembalikan informasi struktur dasar (jumlah halaman, orientasi, peta bab).

    Args:
        pdf_path: Path menuju file PDF korpus.
        save_output: Jika True, metadata disimpan ke `document_metadata.json`.
        output_path: Path file tujuan (default: `data/extracted/document_metadata.json`).

    Returns:
        Dict berisi metadata PDF, ringkasan per halaman (`page_overview`), dan rentang bab (`detected_sections`).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File PDF tidak ditemukan: {path}")

    page_overview: list[dict[str, Any]] = []
    section_spans: list[dict[str, Any]] = []
    current_section = "Sampul"
    current_subsection: str | None = None
    current_chapter = 0

    with pymupdf.open(path) as doc:
        raw_meta = doc.metadata or {}
        toc = doc.get_toc()
        total_pages = len(doc)

        for pdf_page in range(1, total_pages + 1):
            page = doc[pdf_page - 1]
            w = float(page.rect.width)
            h = float(page.rect.height)
            orientation = "landscape" if w > h else "portrait"
            doc_page = _extract_doc_page_fitz(page, pdf_page)

            body_rect = pymupdf.Rect(0.0, 0.0, w, max(0.0, h - FOOTER_HEIGHT_PT))
            raw_body_text = _normalize_whitespace(page.get_text("text", clip=body_rect) or "")
            (
                current_section,
                current_subsection,
                current_chapter,
                _,
                _,
            ) = _update_section_state(
                body_text=raw_body_text,
                pdf_page=pdf_page,
                current_section=current_section,
                current_subsection=current_subsection,
                current_chapter=current_chapter,
            )

            if not section_spans or section_spans[-1]["section"] != current_section:
                section_spans.append(
                    {
                        "section": current_section,
                        "start_pdf_page": pdf_page,
                        "end_pdf_page": pdf_page,
                    }
                )
            else:
                section_spans[-1]["end_pdf_page"] = pdf_page

            imgs = page.get_images(full=True)
            drawings_count = len(page.get_drawings())

            page_overview.append(
                {
                    "pdf_page": pdf_page,
                    "doc_page": doc_page,
                    "section": current_section,
                    "orientation": orientation,
                    "width_pt": round(w, 2),
                    "height_pt": round(h, 2),
                    "char_count": len(raw_body_text),
                    "image_count": len(imgs),
                    "drawing_paths": drawings_count,
                    "is_cover": pdf_page == 1 and len(raw_body_text) == 0,
                }
            )

    metadata: dict[str, Any] = {
        "file_name": path.name,
        "file_size_kb": round(path.stat().st_size / 1024.0, 1),
        "pdf_format": raw_meta.get("format", ""),
        "producer": raw_meta.get("producer", ""),
        "creation_date": raw_meta.get("creationDate", ""),
        "total_pages": total_pages,
        "has_embedded_toc": len(toc) > 0,
        "portrait_pages": sum(1 for p in page_overview if p["orientation"] == "portrait"),
        "landscape_pages": sum(1 for p in page_overview if p["orientation"] == "landscape"),
        "pages_with_images": sum(1 for p in page_overview if p["image_count"] > 0),
        "detected_sections": section_spans,
        "page_overview": page_overview,
    }

    if save_output:
        target = Path(output_path) if output_path is not None else DEFAULT_METADATA_OUTPUT
        _save_json(metadata, target)

    return metadata


def build_extraction_report(
    metadata: dict[str, Any],
    text_pages: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    visuals: list[dict[str, Any]],
    *,
    save_output: bool = False,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Menyusun laporan kualitas ekstraksi (sukses, peringatan, anomali dokumen, dan item gagal)."""
    warnings: list[dict[str, Any]] = []
    failed_items: list[dict[str, Any]] = []

    # 1. Deteksi nomor halaman tercetak (`doc_page`) duplikat (mis. "6" pada hal. PDF 13 & 14)
    doc_page_seen: dict[str, list[int]] = {}
    for page in text_pages:
        dp = page.get("doc_page")
        if dp:
            doc_page_seen.setdefault(dp, []).append(page["pdf_page"])
    for dp, pdf_pages in doc_page_seen.items():
        if len(pdf_pages) > 1:
            warnings.append(
                {
                    "category": "text_pagination",
                    "pdf_pages": pdf_pages,
                    "doc_page": dp,
                    "issue": "duplicate_doc_page",
                    "detail": f"Nomor halaman tercetak '{dp}' muncul ganda pada pdf_page {pdf_pages}.",
                }
            )

    # 2. Kumpulkan quality_flags dari hasil ekstraksi tabel
    tables_by_type: dict[str, int] = {}
    for tbl in tables:
        t_type = tbl["table_type"]
        tables_by_type[t_type] = tables_by_type.get(t_type, 0) + 1
        flags = tbl.get("metadata", {}).get("quality_flags", [])
        if "empty_records" in flags:
            failed_items.append(
                {
                    "category": "table",
                    "item_id": tbl["table_id"],
                    "pdf_page": tbl["pdf_page"],
                    "detail": f"Tabel '{tbl['table_title']}' menghasilkan 0 record.",
                }
            )
        for flag in flags:
            if flag != "empty_records":
                warnings.append(
                    {
                        "category": "table",
                        "item_id": tbl["table_id"],
                        "pdf_page": tbl["pdf_page"],
                        "doc_page": tbl["doc_page"],
                        "issue": flag,
                        "detail": f"Terdeteksi '{flag}' pada '{tbl['table_title']}'.",
                    }
                )

    # 3. Kumpulkan catatan perbedaan SKS pada visual Learning Path
    for vis in visuals:
        if vis.get("metadata", {}).get("has_sks_discrepancy_note"):
            notes = [
                f"{rec['course_name']}: {rec['notes']}"
                for rec in vis.get("structured_records", [])
                if rec.get("notes") and "SKS" in str(rec["notes"])
            ]
            warnings.append(
                {
                    "category": "visual",
                    "item_id": vis["visual_id"],
                    "pdf_page": vis["pdf_page"],
                    "doc_page": vis["doc_page"],
                    "issue": "visual_vs_table_sks_discrepancy",
                    "detail": "; ".join(notes),
                }
            )

    cover_or_empty = [
        p["pdf_page"] for p in text_pages if p["metadata"]["raw_char_count"] == 0
    ]

    report: dict[str, Any] = {
        "pdf_file": metadata["file_name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_pages": metadata["total_pages"],
            "pages_with_text_or_tables": metadata["total_pages"] - len(cover_or_empty),
            "narrative_non_empty_pages": sum(1 for p in text_pages if p["text"]),
            "cover_or_empty_pages": cover_or_empty,
            "tables_extracted": len(tables),
            "continuation_tables": sum(1 for t in tables if t["is_continuation"]),
            "unique_syllabus_courses": len(
                {
                    t["metadata"].get("course_code")
                    for t in tables
                    if t["table_type"] == "syllabus_card" and t["metadata"].get("course_code")
                }
            ),
            "visuals_inventoried": len(visuals),
            "visuals_transcribed_for_qa": sum(
                1 for v in visuals if v["extraction_method"] == "structured_transcription"
            ),
            "warning_count": len(warnings),
            "failed_count": len(failed_items),
        },
        "tables_by_type": tables_by_type,
        "warnings": warnings,
        "failed_items": failed_items,
    }

    if save_output:
        target = Path(output_path) if output_path is not None else DEFAULT_REPORT_OUTPUT
        _save_json(report, target)

    return report


def run_full_ingestion(
    pdf_path: str | Path = DEFAULT_RAW_PDF,
    output_dir: str | Path = EXTRACTED_DATA_DIR,
) -> dict[str, Any]:
    """Menjalankan seluruh pipeline Document Ingestion (Anggota 1) secara berurutan."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = load_pdf_metadata(
        pdf_path,
        save_output=True,
        output_path=out_dir / DEFAULT_METADATA_OUTPUT.name,
    )
    text_pages = extract_text_pages(
        pdf_path,
        exclude_tables=True,
        save_output=True,
        output_path=out_dir / DEFAULT_TEXT_OUTPUT.name,
    )
    tables = extract_tables(
        pdf_path,
        save_output=True,
        output_path=out_dir / DEFAULT_TABLES_OUTPUT.name,
    )
    visuals = extract_visuals(
        pdf_path,
        export_images=True,
        visuals_dir=out_dir / "visuals",
        save_output=True,
        output_path=out_dir / DEFAULT_VISUALS_OUTPUT.name,
    )
    report = build_extraction_report(
        metadata=metadata,
        text_pages=text_pages,
        tables=tables,
        visuals=visuals,
        save_output=True,
        output_path=out_dir / DEFAULT_REPORT_OUTPUT.name,
    )
    return {
        "metadata": metadata,
        "text_pages": text_pages,
        "tables": tables,
        "visuals": visuals,
        "report": report,
    }


def _save_json(payload: Any, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return target


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Loader metadata PDF dan runner penuh Document Ingestion (Anggota 1)."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_RAW_PDF,
        help="Path file PDF sumber (default: config.settings.DEFAULT_RAW_PDF).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXTRACTED_DATA_DIR,
        help="Direktori output hasil ekstraksi (default: data/extracted/).",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Hanya jalankan pembacaan metadata PDF (tanpa ekstraksi teks/tabel/visual).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.metadata_only:
        meta = load_pdf_metadata(
            args.pdf,
            save_output=True,
            output_path=args.output_dir / DEFAULT_METADATA_OUTPUT.name,
        )
        print(
            f"Metadata selesai: {meta['file_name']} ({meta['total_pages']} halaman, "
            f"{meta['portrait_pages']} portrait, {meta['landscape_pages']} landscape)."
        )
        return

    result = run_full_ingestion(args.pdf, output_dir=args.output_dir)
    summary = result["report"]["summary"]
    print("Pipeline Document Ingestion (Anggota 1) selesai!")
    print(f"- Total halaman               : {summary['total_pages']}")
    print(f"- Halaman narasi non-kosong   : {summary['narrative_non_empty_pages']}")
    print(f"- Total blok tabel diekstrak  : {summary['tables_extracted']} ({summary['continuation_tables']} lanjutan)")
    print(f"- Mata kuliah silabus unik    : {summary['unique_syllabus_courses']}")
    print(f"- Visual diinventarisasi      : {summary['visuals_inventoried']} ({summary['visuals_transcribed_for_qa']} Learning Path ditranskripsi)")
    print(f"- Peringatan kualitas         : {summary['warning_count']} | Gagal: {summary['failed_count']}")
    print(f"- Direktori output            : {args.output_dir}")


if __name__ == "__main__":
    main()
