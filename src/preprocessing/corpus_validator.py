"""Validasi kualitas dataset korpus (passage kosong, duplikat, metadata halaman, & triples)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from config.settings import DEFAULT_CORPUS_FILE, DEFAULT_KB_FILE, PROCESSED_DATA_DIR
from src.contracts import KnowledgeTriple, PassageRecord


def validate_corpus(
    passages: list[PassageRecord],
    triples: list[KnowledgeTriple] | None = None,
) -> dict[str, Any]:
    """Memeriksa kualitas daftar passage & knowledge triples lalu mengembalikan laporan ringkas.

    Mengecek: passage kosong, duplikat, kelengkapan `pdf_page`/`doc_page`,
    distribusi `content_type`, serta integritas triple `(subject, predicate, object)`.
    """
    empty_passages: list[str] = []
    empty_stemmed: list[str] = []
    empty_tokens: list[str] = []
    missing_metadata_passages: list[str] = []
    duplicate_passage_ids: list[str] = []
    duplicate_passage_texts: list[str] = []

    seen_pids: set[str] = set()
    seen_texts: set[str] = set()
    content_type_dist: Counter[str] = Counter()
    unique_pdf_pages: set[int] = set()

    for idx, p in enumerate(passages):
        pid = str(p.get("passage_id") or f"index_{idx}")
        if pid in seen_pids:
            duplicate_passage_ids.append(pid)
        seen_pids.add(pid)

        text = (p.get("text") or "").strip()
        if not text:
            empty_passages.append(pid)
        else:
            key = f"{p.get('content_type', '')}::{text.lower()}"
            if key in seen_texts:
                duplicate_passage_texts.append(pid)
            seen_texts.add(key)

        if not (p.get("stemmed_text") or "").strip():
            empty_stemmed.append(pid)
        if not p.get("tokens"):
            empty_tokens.append(pid)

        pdf_page = p.get("pdf_page")
        doc_page = p.get("doc_page")
        section = (p.get("section") or "").strip()
        if not isinstance(pdf_page, int) or pdf_page <= 0 or not doc_page or not section:
            missing_metadata_passages.append(pid)
        else:
            unique_pdf_pages.add(pdf_page)

        ctype = str(p.get("content_type") or "unknown")
        content_type_dist[ctype] += 1

    triple_report: dict[str, Any] = {
        "total_triples": 0,
        "invalid_triples": [],
        "duplicate_triple_ids": [],
        "duplicate_triples": [],
        "missing_metadata_triples": [],
        "predicate_distribution": {},
    }

    if triples is not None:
        seen_tids: set[str] = set()
        seen_spo: set[tuple[str, str, str]] = set()
        pred_dist: Counter[str] = Counter()
        invalid_triples: list[str] = []
        dup_tids: list[str] = []
        dup_spo: list[str] = []
        missing_meta_t: list[str] = []

        for idx, t in enumerate(triples):
            tid = str(t.get("triple_id") or f"triple_{idx}")
            if tid in seen_tids:
                dup_tids.append(tid)
            seen_tids.add(tid)

            subj = str(t.get("subject") or "").strip()
            pred = str(t.get("predicate") or "").strip()
            obj = t.get("object")
            if not subj or not pred or obj is None or obj == "":
                invalid_triples.append(tid)
            else:
                spo = (subj.lower(), pred, str(obj).strip().lower())
                if spo in seen_spo:
                    dup_spo.append(tid)
                seen_spo.add(spo)
                pred_dist[pred] += 1

            pdf_page = t.get("pdf_page")
            doc_page = t.get("doc_page")
            if not isinstance(pdf_page, int) or pdf_page <= 0 or not doc_page:
                missing_meta_t.append(tid)

        triple_report = {
            "total_triples": len(triples),
            "invalid_triples": invalid_triples,
            "duplicate_triple_ids": dup_tids,
            "duplicate_triples": dup_spo,
            "missing_metadata_triples": missing_meta_t,
            "predicate_distribution": dict(sorted(pred_dist.items())),
        }

    is_valid = (
        len(passages) > 0
        and not empty_passages
        and not empty_stemmed
        and not empty_tokens
        and not missing_metadata_passages
        and not duplicate_passage_ids
        and not duplicate_passage_texts
        and not triple_report["invalid_triples"]
        and not triple_report["duplicate_triple_ids"]
        and not triple_report["duplicate_triples"]
        and not triple_report["missing_metadata_triples"]
    )

    return {
        "is_valid": is_valid,
        "total_passages": len(passages),
        "unique_pdf_pages_covered": len(unique_pdf_pages),
        "content_type_distribution": dict(sorted(content_type_dist.items())),
        "empty_passages": empty_passages,
        "empty_stemmed": empty_stemmed,
        "empty_tokens": empty_tokens,
        "missing_metadata_passages": missing_metadata_passages,
        "duplicate_passage_ids": duplicate_passage_ids,
        "duplicate_passage_texts": duplicate_passage_texts,
        "triples": triple_report,
    }


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Membaca berkas JSONL menjadi list dict."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File JSONL tidak ditemukan: {file_path}")
    rows: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def validate_corpus_files(
    passages_path: str | Path = DEFAULT_CORPUS_FILE,
    triples_path: str | Path = DEFAULT_KB_FILE,
    *,
    report_output: str | Path | None = PROCESSED_DATA_DIR / "corpus_validation_report.json",
) -> dict[str, Any]:
    """Memvalidasi file JSONL korpus dan opsional menyimpan laporan validasi."""
    passages: list[PassageRecord] = load_jsonl(passages_path)  # type: ignore[assignment]
    triples: list[KnowledgeTriple] | None = (
        load_jsonl(triples_path) if Path(triples_path).exists() else None  # type: ignore[assignment]
    )
    report = validate_corpus(passages, triples)
    if report_output is not None:
        out = Path(report_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validasi dataset korpus Modul 2 (Anggota 2).")
    parser.add_argument("--passages", type=Path, default=DEFAULT_CORPUS_FILE)
    parser.add_argument("--triples", type=Path, default=DEFAULT_KB_FILE)
    parser.add_argument(
        "--report-out",
        type=Path,
        default=PROCESSED_DATA_DIR / "corpus_validation_report.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = validate_corpus_files(
        args.passages,
        args.triples,
        report_output=args.report_out,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
