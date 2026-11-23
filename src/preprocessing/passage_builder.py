"""Pembentukan unit passage terstruktur (IR) dan Knowledge Triples (Hybrid KB-QA).

Modul Anggota 2 (Radit) untuk mengubah output Modul 1 (`text_pages.json`,
`tables.json`, `visuals.json`) menjadi `passages.jsonl` dan `knowledge_triples.jsonl`
sesuai kontrak `src/contracts.py` dan vocabulary GATE-A.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from config.settings import (
    DEFAULT_CORPUS_FILE,
    DEFAULT_KB_FILE,
    EXTRACTED_DATA_DIR,
)
from src.contracts import KnowledgeTriple, PassageRecord
from src.preprocessing.preprocessing import clean_text, preprocess_for_indexing

_SKIP_TEXT_SECTIONS = frozenset({"Sampul", "Daftar Isi", "Daftar Tabel", "Daftar Gambar"})
_HEADING_RE = re.compile(r"^(?:[A-Z]\.\s+|\d+(?:\.\d+)?\s+[A-Z])")
_STANDALONE_CAPTION_RE = re.compile(r"^(?:Tabel|Gambar)\s+\d+\.\d+\b.*$", re.IGNORECASE)
_MAX_TEXT_PASSAGE_CHARS = 1500


def _make_passage(
    passage_id: str,
    raw_text: str,
    *,
    pdf_page: int,
    doc_page: str,
    section: str,
    content_type: str,
    table_title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PassageRecord | None:
    """Membentuk satu `PassageRecord` dengan pipeline clean -> tokenize -> stopword -> stem."""
    cleaned, tokens, stemmed = preprocess_for_indexing(raw_text)
    if not cleaned:
        return None
    return PassageRecord(
        passage_id=passage_id,
        text=cleaned,
        stemmed_text=stemmed,
        tokens=tokens,
        pdf_page=int(pdf_page),
        doc_page=str(doc_page or ""),
        source_page=int(pdf_page),
        section=section or "",
        content_type=content_type,  # type: ignore[typeddict-item]
        table_title=table_title,
        metadata=metadata or {},
    )


def _is_heading_paragraph(para: str) -> bool:
    """Mendeteksi apakah paragraf adalah judul bab/subbab pendek tanpa titik akhir."""
    stripped = para.strip()
    if len(stripped) > 100 or stripped.endswith("."):
        return False
    if _HEADING_RE.match(stripped):
        return True
    return stripped.isupper() and len(stripped.split()) <= 10


def _group_page_paragraphs(paragraphs: list[str]) -> list[str]:
    """Mengelompokkan heading + isi paragraf berurutan menjadi unit passage koheren."""
    groups: list[str] = []
    current: list[str] = []
    current_len = 0

    for raw_para in paragraphs:
        para = clean_text(raw_para)
        if not para:
            continue
        if _STANDALONE_CAPTION_RE.match(para) and len(para) < 120:
            continue

        is_heading = _is_heading_paragraph(para)
        if is_heading and current:
            # Flush hanya jika grup saat ini sudah memiliki isi (bukan sekadar heading lain).
            if any(not _is_heading_paragraph(item) for item in current):
                groups.append(" ".join(current))
                current = []
                current_len = 0

        if not is_heading and current and current_len + len(para) > _MAX_TEXT_PASSAGE_CHARS:
            groups.append(" ".join(current))
            current = []
            current_len = 0

        current.append(para)
        current_len += len(para) + 1

    if current:
        groups.append(" ".join(current))
    return groups


def _merge_continuation_tables(table_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Menggabungkan blok tabel lanjutan (`is_continuation`) ke tabel induknya (`continuation_of`)."""
    merged_by_id: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []

    def _stamp_record_source(rec: dict[str, Any], tbl: dict[str, Any]) -> dict[str, Any]:
        stamped = dict(rec)
        stamped["_src_pdf_page"] = tbl.get("pdf_page", 1)
        stamped["_src_doc_page"] = str(tbl.get("doc_page") or "")
        return stamped

    for tbl in table_items:
        tid = tbl.get("table_id") or f"tbl_{len(ordered_ids) + 1}"
        parent_id = tbl.get("continuation_of")
        if tbl.get("is_continuation") and parent_id and parent_id in merged_by_id:
            parent = merged_by_id[parent_id]
            parent["_pdf_pages"].append(tbl.get("pdf_page"))
            if tbl.get("doc_page"):
                parent["_doc_pages"].append(str(tbl.get("doc_page")))
            if tbl.get("table_type") == "syllabus_card":
                _merge_syllabus_records(parent, tbl)
            else:
                parent["records"] = list(parent.get("records") or []) + [
                    _stamp_record_source(r, tbl) for r in (tbl.get("records") or [])
                ]
                parent["rows"] = list(parent.get("rows") or []) + list(tbl.get("rows") or [])
        else:
            copy = dict(tbl)
            copy["records"] = [_stamp_record_source(r, tbl) for r in (tbl.get("records") or [])]
            copy["rows"] = list(tbl.get("rows") or [])
            copy["_pdf_pages"] = [tbl.get("pdf_page")]
            copy["_doc_pages"] = [str(tbl.get("doc_page") or "")]
            merged_by_id[tid] = copy
            ordered_ids.append(tid)

    return [merged_by_id[tid] for tid in ordered_ids]


def _merge_syllabus_records(parent: dict[str, Any], cont: dict[str, Any]) -> None:
    """Menggabungkan isi record kartu silabus lintas halaman ke kartu induk."""
    p_recs = parent.get("records") or []
    c_recs = cont.get("records") or []
    if not p_recs or not c_recs:
        return

    base = p_recs[0]
    ext = c_recs[0]

    if ext.get("deskripsi"):
        base["deskripsi"] = (
            f"{base['deskripsi']} {ext['deskripsi']}".strip()
            if base.get("deskripsi")
            else ext["deskripsi"]
        )

    existing_bk = list(base.get("bahan_kajian") or [])
    for bk in ext.get("bahan_kajian") or []:
        if bk not in existing_bk:
            existing_bk.append(bk)
    base["bahan_kajian"] = existing_bk

    existing_cpmk = list(base.get("cpmk") or [])
    seen_codes = {item.get("kode") for item in existing_cpmk if item.get("kode")}
    for cpmk in ext.get("cpmk") or []:
        kode = cpmk.get("kode")
        if kode and kode in seen_codes:
            continue
        existing_cpmk.append(cpmk)
        if kode:
            seen_codes.add(kode)
    base["cpmk"] = existing_cpmk

    if ext.get("other_text"):
        base["other_text"] = (
            f"{base['other_text']} {ext['other_text']}".strip()
            if base.get("other_text")
            else ext["other_text"]
        )


def _format_semester_row_text(table_title: str, rec: dict[str, Any]) -> str:
    """Mengonversi satu baris jadwal semester menjadi kalimat eksplisit (termasuk status praktikum)."""
    kode = rec.get("kode_mk") or "-"
    nama = rec.get("nama_mk") or "-"
    sks = rec.get("sks")
    sem = rec.get("semester")
    praktikum_str = "Ya" if rec.get("praktikum") else "Tidak"
    parts = [f"{table_title}: Mata kuliah {kode} {nama}"]
    if sem is not None:
        parts.append(f"Semester {sem}")
    if sks is not None:
        parts.append(f"{sks} SKS")
    parts.append(f"Praktikum: {praktikum_str}")
    if rec.get("prasyarat_mk") or rec.get("prasyarat_kode"):
        prereq = " ".join(p for p in (rec.get("prasyarat_kode"), rec.get("prasyarat_mk")) if p)
        if rec.get("prasyarat_nilai"):
            prereq = f"{prereq} (nilai minimal {rec['prasyarat_nilai']})"
        parts.append(f"Prasyarat: {prereq}")
    else:
        parts.append("Prasyarat: Tidak ada")
    return ", ".join(parts) + "."


def _format_syllabus_text(table_title: str, rec: dict[str, Any]) -> str:
    """Menyusun teks utuh satu kartu silabus hasil penggabungan lintas halaman."""
    kode = rec.get("kode_mk") or ""
    nama = rec.get("nama_mk") or ""
    sks = rec.get("sks")
    header = f"{table_title} ({kode} {nama}, {sks} SKS)." if sks else f"{table_title} ({kode} {nama})."
    sections = [header]
    if rec.get("deskripsi"):
        sections.append(f"Deskripsi Mata Kuliah: {rec['deskripsi']}")
    if rec.get("bahan_kajian"):
        bk_joined = "; ".join(rec["bahan_kajian"])
        sections.append(f"Bahan Kajian: {bk_joined}.")
    if rec.get("cpmk"):
        cpmk_strs = []
        for item in rec["cpmk"]:
            cpls = ", ".join(item.get("cpl") or [])
            suffix = f" [CPL: {cpls}]" if cpls else ""
            cpmk_strs.append(f"{item.get('kode')}: {item.get('deskripsi', '')}{suffix}")
        sections.append("CPMK: " + " ".join(cpmk_strs))
    if rec.get("other_text"):
        sections.append(str(rec["other_text"]))
    return " ".join(sections)


def _format_transition_row_text(table_title: str, rec: dict[str, Any]) -> str:
    """Mengonversi satu baris tabel penyetaraan kurikulum 2020->2024 menjadi teks eksplisit."""
    lama = " ".join(
        p for p in (rec.get("lama_kode_mk"), rec.get("lama_nama_mk")) if p
    ) or "Tidak ada"
    lama_sks = f" ({rec['lama_sks']} SKS)" if rec.get("lama_sks") is not None else ""
    baru = " ".join(
        p for p in (rec.get("baru_kode_mk"), rec.get("baru_nama_mk")) if p
    ) or "Tidak ada"
    baru_sks = f" ({rec['baru_sks']} SKS)" if rec.get("baru_sks") is not None else ""
    return (
        f"{table_title}: Kurikulum Lama (2020) {lama}{lama_sks} "
        f"disetarakan dengan Kurikulum Baru (2024) {baru}{baru_sks}."
    )


def _build_table_passages(merged_tables: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Menghasilkan daftar pasangan `(raw_text, context_kwargs)` dari tabel yang sudah digabungkan."""
    entries: list[tuple[str, dict[str, Any]]] = []

    for tbl in merged_tables:
        ttype = tbl.get("table_type", "regular")
        title = tbl.get("table_title") or "Tabel Kurikulum"
        records = tbl.get("records") or []
        base_meta = {
            "table_id": tbl.get("table_id"),
            "table_type": ttype,
            "pdf_pages": tbl.get("_pdf_pages") or [tbl.get("pdf_page")],
            "doc_pages": tbl.get("_doc_pages") or [str(tbl.get("doc_page") or "")],
            **(tbl.get("metadata") or {}),
        }
        common = {
            "pdf_page": tbl.get("pdf_page", 1),
            "doc_page": str(tbl.get("doc_page") or ""),
            "section": tbl.get("section") or "",
            "content_type": "table",
            "table_title": title,
        }

        def _row_ctx(rec: dict[str, Any], extra_meta: dict[str, Any]) -> dict[str, Any]:
            return {
                **common,
                "pdf_page": rec.get("_src_pdf_page", common["pdf_page"]),
                "doc_page": rec.get("_src_doc_page", common["doc_page"]),
                "metadata": extra_meta,
            }

        if ttype == "semester_schedule":
            sem = base_meta.get("semester")
            total_sks = base_meta.get("total_sks")
            mk_list = ", ".join(
                f"{r.get('kode_mk') or '-'} {r.get('nama_mk')} ({r.get('sks')} SKS)"
                for r in records
                if r.get("nama_mk")
            )
            summary_head = f"{title}"
            if total_sks is not None:
                summary_head += f" (Total {total_sks} SKS)"
            entries.append((f"{summary_head}: Daftar mata kuliah: {mk_list}.", {**common, "metadata": {**base_meta, "granularity": "table_summary"}}))
            for rec in records:
                if rec.get("nama_mk") == "MK Pilihan" and not rec.get("kode_mk"):
                    continue
                row_meta = {**base_meta, "granularity": "row", "course_code": rec.get("kode_mk"), "semester": sem}
                entries.append((_format_semester_row_text(title, rec), _row_ctx(rec, row_meta)))

        elif ttype == "syllabus_card":
            for rec in records:
                row_meta = {
                    **base_meta,
                    "course_code": rec.get("kode_mk"),
                    "course_name": rec.get("nama_mk"),
                    "sks": rec.get("sks"),
                }
                entries.append((_format_syllabus_text(title, rec), {**common, "metadata": row_meta}))

        elif ttype == "cpl_matrix":
            for rec in records:
                cpls = ", ".join(rec.get("cpl_codes") or []) or "Tidak ada"
                txt = (
                    f"{title}: Bahan kajian {rec.get('bahan_kajian')} "
                    f"mendukung {rec.get('cpl_count', 0)} CPL yaitu {cpls}."
                )
                entries.append((txt, _row_ctx(rec, {**base_meta, "bahan_kajian": rec.get("bahan_kajian")})))

        elif ttype == "transition_mapping":
            for rec in records:
                entries.append((_format_transition_row_text(title, rec), _row_ctx(rec, {**base_meta, "granularity": "row"})))

        else:  # regular tables (3.1, 6.1-6.4, 7.1-7.4, 9.9-9.10, 10.1, versi)
            if records and "kegiatan" in records[0]:  # Tabel 10.1 MBKM
                for rec in records:
                    txt = f"{title} - {rec.get('kegiatan')}: {rec.get('penjelasan')}"
                    entries.append((txt, _row_ctx(rec, {**base_meta, "activity": rec.get("kegiatan")})))
            elif records and "kode_cpl" in records[0]:  # Tabel 3.1 CPL
                for rec in records:
                    txt = f"{title} ({rec.get('kategori_cpl', '')}): Kode {rec.get('kode_cpl')} - {rec.get('deskripsi_cpl')}"
                    entries.append((txt, _row_ctx(rec, {**base_meta, "cpl_code": rec.get("kode_cpl")})))
            elif records and "learning_path" in records[0]:  # Tabel 7.4
                for rec in records:
                    txt = f"{title}: Learning Path {rec.get('learning_path')}, prasyarat MK: {rec.get('prasyarat_mk')}, syarat SKS: {rec.get('sks')}."
                    entries.append((txt, _row_ctx(rec, {**base_meta, "learning_path": rec.get("learning_path")})))
            elif records and "kode_mk" in records[0]:  # Tabel 6.1-6.4, 7.1-7.3, 9.9-9.10
                items_txt = "; ".join(
                    f"{r.get('kode_mk')} {r.get('nama_mk')} ({r.get('sks')} SKS"
                    + (f", Semester {r['semester']}" if r.get("semester") else "")
                    + ")"
                    for r in records
                )
                entries.append((f"{title}: {items_txt}.", {**common, "metadata": {**base_meta, "granularity": "table_summary"}}))
                for rec in records:
                    sem_part = f", Semester {rec['semester']}" if rec.get("semester") else ""
                    txt = f"{title}: {rec.get('kode_mk')} {rec.get('nama_mk')} ({rec.get('sks')} SKS{sem_part})."
                    entries.append((txt, _row_ctx(rec, {**base_meta, "granularity": "row", "course_code": rec.get("kode_mk")})))
            elif records:
                summary = "; ".join(", ".join(f"{k}: {v}" for k, v in r.items() if k not in {"_src_pdf_page", "_src_doc_page"} and v is not None) for r in records)
                entries.append((f"{title}: {summary}.", {**common, "metadata": base_meta}))

    return entries


def build_passages(extracted_items: list[dict[str, Any]]) -> list[PassageRecord]:
    """Mengubah hasil ekstraksi (teks, tabel, visual) menjadi list `PassageRecord`.

    Menangani penggabungan tabel/silabus lintas halaman, konversi tanda centang,
    serta penyimpanan `pdf_page`, `doc_page`, `tokens`, dan `stemmed_text`.
    """
    passages: list[PassageRecord] = []
    seen_texts: set[str] = set()
    table_items = [item for item in extracted_items if item.get("content_type") == "table"]
    text_items = [item for item in extracted_items if item.get("content_type") == "text"]
    visual_items = [item for item in extracted_items if item.get("content_type") == "visual"]

    def _append(raw_text: str, **kwargs: Any) -> None:
        pid = f"p_{len(passages) + 1:04d}"
        rec = _make_passage(pid, raw_text, **kwargs)
        if rec is None:
            return
        dedup_key = f"{rec['content_type']}::{rec['text'].lower()}"
        if dedup_key in seen_texts:
            return
        seen_texts.add(dedup_key)
        passages.append(rec)

    # 1. Teks naratif per halaman (kecuali sampul & front matter daftar isi/tabel/gambar)
    for page in text_items:
        section = page.get("section") or ""
        if int(page.get("pdf_page") or 0) == 1 or section in _SKIP_TEXT_SECTIONS:
            continue
        paragraphs = page.get("paragraphs") or ([page["text"]] if page.get("text") else [])
        for idx, group_text in enumerate(_group_page_paragraphs(paragraphs), start=1):
            _append(
                group_text,
                pdf_page=page.get("pdf_page", 1),
                doc_page=str(page.get("doc_page") or ""),
                section=section,
                content_type="text",
                table_title=None,
                metadata={
                    "page_id": page.get("page_id"),
                    "subsection": page.get("subsection"),
                    "chunk_index": idx,
                },
            )

    # 2. Tabel terstruktur (digabung lintas halaman terlebih dahulu)
    merged_tables = _merge_continuation_tables(table_items)
    for raw_text, ctx in _build_table_passages(merged_tables):
        _append(raw_text, **ctx)

    # 3. Visual relevan untuk QA (11 transkripsi Learning Path + 3 diagram alir)
    for vis in visual_items:
        if not vis.get("relevant_for_qa"):
            continue
        fig_num = vis.get("figure_number") or ""
        caption = vis.get("caption") or fig_num
        raw_text = vis.get("text") or ""
        _append(
            raw_text,
            pdf_page=vis.get("pdf_page", 1),
            doc_page=str(vis.get("doc_page") or ""),
            section=vis.get("section") or "",
            content_type="visual",
            table_title=caption,
            metadata={
                "visual_id": vis.get("visual_id"),
                "figure_number": fig_num,
                "image_path": vis.get("image_path"),
                "extraction_method": vis.get("extraction_method"),
            },
        )

    return passages


def _extract_elective_group(table_title: str) -> str:
    """Menormalkan nama kelompok MK pilihan dari judul Tabel 7.1–7.3 sesuai GATE-A."""
    low = table_title.lower()
    if "perangkat lunak" in low:
        return "Perekayasa Perangkat Lunak"
    if "infrastruktur komputasi" in low:
        return "Perekayasa Infrastruktur Komputasi"
    if "komputasi cerdas" in low:
        return "Perekayasa Komputasi Cerdas"
    return table_title


def build_knowledge_triples(extracted_items: list[dict[str, Any]]) -> list[KnowledgeTriple]:
    """Membangun RDF-like triples `(subject, predicate, object)` dari tabel & transkripsi visual.

    Menggunakan vocabulary predikat standar GATE-A (`docs/question_taxonomy.md`) sehingga
    `retrieve_triples()` Anggota 4 & Answer Extraction Anggota 5 dapat mencocokkan langsung.
    """
    triples: list[KnowledgeTriple] = []
    seen_keys: set[tuple[str, str, str]] = set()

    def _add_triple(
        subject: str | None,
        predicate: str,
        obj: Any,
        *,
        pdf_page: int,
        doc_page: str,
        section: str,
        table_title: str | None,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not subject or not predicate or obj is None or obj == "":
            return
        subj_clean = clean_text(str(subject))
        obj_clean = clean_text(str(obj)) if isinstance(obj, str) else obj
        dedup = (subj_clean.lower(), predicate, str(obj_clean).lower())
        if dedup in seen_keys:
            return
        seen_keys.add(dedup)
        triples.append(
            KnowledgeTriple(
                triple_id=f"t_{len(triples) + 1:04d}",
                subject=subj_clean,
                predicate=predicate,
                object=obj_clean,
                pdf_page=int(pdf_page),
                doc_page=str(doc_page or ""),
                section=section or "",
                table_title=table_title,
                content_type=content_type,  # type: ignore[typeddict-item]
                metadata=metadata or {},
            )
        )

    table_items = [item for item in extracted_items if item.get("content_type") == "table"]
    merged_tables = _merge_continuation_tables(table_items)

    # Fakta total SKS program studi (144 SKS) & komponen muatan dari judul tabel resmi
    for tbl in merged_tables:
        ttype = tbl.get("table_type", "regular")
        title = tbl.get("table_title") or ""
        records = tbl.get("records") or []
        meta = tbl.get("metadata") or {}
        src = {
            "pdf_page": tbl.get("pdf_page", 1),
            "doc_page": str(tbl.get("doc_page") or ""),
            "section": tbl.get("section") or "",
            "table_title": title,
            "content_type": "table",
        }

        if ttype == "semester_schedule":
            sem = meta.get("semester")
            if sem is not None and meta.get("total_sks") is not None:
                _add_triple(f"semester {sem}", "total_sks", meta["total_sks"], **src)
            for rec in records:
                kode = rec.get("kode_mk")
                nama = rec.get("nama_mk")
                if not nama or (nama == "MK Pilihan" and not kode):
                    continue
                subjects = [s for s in (nama, kode) if s]
                if kode and nama:
                    _add_triple(kode, "course_name", nama, **src)
                    _add_triple(nama, "course_code", kode, **src)
                for subj in subjects:
                    if rec.get("sks") is not None:
                        _add_triple(subj, "sks", rec["sks"], **src)
                    if sem is not None:
                        _add_triple(subj, "semester", str(sem), **src)
                    _add_triple(subj, "has_practicum", bool(rec.get("praktikum")), **src)
                    if rec.get("prasyarat_mk") or rec.get("prasyarat_kode"):
                        prereq_val = " ".join(
                            p for p in (rec.get("prasyarat_kode"), rec.get("prasyarat_mk")) if p
                        )
                        _add_triple(subj, "prerequisite_of", prereq_val, **src)
                    if rec.get("prasyarat_nilai"):
                        _add_triple(subj, "min_grade", rec["prasyarat_nilai"], **src)

        elif ttype == "syllabus_card":
            for rec in records:
                kode = rec.get("kode_mk")
                nama = rec.get("nama_mk")
                if kode and nama:
                    _add_triple(kode, "course_name", nama, **src)
                    _add_triple(nama, "course_code", kode, **src)
                for subj in (s for s in (nama, kode) if s):
                    if rec.get("sks") is not None:
                        _add_triple(subj, "sks", rec["sks"], **src)
                    if rec.get("deskripsi"):
                        _add_triple(subj, "course_description", rec["deskripsi"], **src)

        elif ttype == "cpl_matrix":
            for rec in records:
                bk = rec.get("bahan_kajian")
                row_src = {
                    **src,
                    "pdf_page": rec.get("_src_pdf_page", src["pdf_page"]),
                    "doc_page": rec.get("_src_doc_page", src["doc_page"]),
                }
                for cpl in rec.get("cpl_codes") or []:
                    _add_triple(bk, "supports_cpl", cpl, **row_src)

        elif ttype == "transition_mapping":
            for rec in records:
                baru = " ".join(
                    p for p in (rec.get("baru_kode_mk"), rec.get("baru_nama_mk")) if p
                )
                if not baru:
                    continue
                row_src = {
                    **src,
                    "pdf_page": rec.get("_src_pdf_page", src["pdf_page"]),
                    "doc_page": rec.get("_src_doc_page", src["doc_page"]),
                }
                for old_subj in (s for s in (rec.get("lama_nama_mk"), rec.get("lama_kode_mk")) if s):
                    _add_triple(old_subj, "equivalent_to", baru, **row_src)

        else:  # regular tables
            sks_match = re.search(r"(\d+)\s*SKS", title, flags=re.IGNORECASE)
            if sks_match:
                low_title = title.lower()
                if "muatan program studi" in low_title:
                    _add_triple("muatan program studi", "total_sks", int(sks_match.group(1)), **src)
                elif "muatan nasional" in low_title:
                    _add_triple("muatan nasional", "total_sks", int(sks_match.group(1)), **src)
                elif "muatan universitas" in low_title:
                    _add_triple("muatan universitas", "total_sks", int(sks_match.group(1)), **src)
                elif "muatan fakultas" in low_title:
                    _add_triple("muatan fakultas", "total_sks", int(sks_match.group(1)), **src)

            if records and "kode_cpl" in records[0]:
                for rec in records:
                    row_src = {
                        **src,
                        "pdf_page": rec.get("_src_pdf_page", src["pdf_page"]),
                        "doc_page": rec.get("_src_doc_page", src["doc_page"]),
                    }
                    _add_triple(rec.get("kode_cpl"), "cpl_description", rec.get("deskripsi_cpl"), **row_src)
            elif records and "kode_mk" in records[0]:
                is_elective = any(k in title.lower() for k in ("tabel 7.1", "tabel 7.2", "tabel 7.3"))
                group_name = _extract_elective_group(title) if is_elective else None
                for rec in records:
                    kode = rec.get("kode_mk")
                    nama = rec.get("nama_mk")
                    if kode and nama:
                        _add_triple(kode, "course_name", nama, **src)
                        _add_triple(nama, "course_code", kode, **src)
                    for subj in (s for s in (nama, kode) if s):
                        if rec.get("sks") is not None:
                            _add_triple(subj, "sks", rec["sks"], **src)
                        if rec.get("semester"):
                            _add_triple(subj, "semester", str(rec["semester"]), **src)
                        if group_name:
                            _add_triple(subj, "elective_group_member", group_name, **src)

    # Visual Learning Path (Gambar 7.1–7.11)
    for vis in extracted_items:
        if vis.get("content_type") != "visual" or vis.get("extraction_method") != "structured_transcription":
            continue
        src = {
            "pdf_page": vis.get("pdf_page", 1),
            "doc_page": str(vis.get("doc_page") or ""),
            "section": vis.get("section") or "",
            "table_title": vis.get("caption") or vis.get("figure_number"),
            "content_type": "visual",
        }
        for rec in vis.get("structured_records") or []:
            course = rec.get("course_name")
            lp = rec.get("learning_path")
            _add_triple(course, "learning_path_member", lp, **src)
            if rec.get("group"):
                _add_triple(course, "elective_group_member", rec["group"], **src)
            if rec.get("sks") is not None:
                _add_triple(course, "learning_path_sks", rec["sks"], **src)

    return triples


def load_extracted_items(extracted_dir: str | Path = EXTRACTED_DATA_DIR) -> list[dict[str, Any]]:
    """Memuat seluruh hasil ekstraksi Modul 1 (`text_pages.json`, `tables.json`, `visuals.json`)."""
    base = Path(extracted_dir)
    items: list[dict[str, Any]] = []
    for filename in ("text_pages.json", "tables.json", "visuals.json"):
        file_path = base / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File hasil ekstraksi Modul 1 tidak ditemukan: {file_path}")
        with file_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            items.extend(data)
    return items


def save_jsonl(records: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Menyimpan daftar dict/TypedDict ke berkas JSONL UTF-8."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return target


def build_and_save_corpus(
    extracted_dir: str | Path = EXTRACTED_DATA_DIR,
    *,
    passages_output: str | Path = DEFAULT_CORPUS_FILE,
    triples_output: str | Path = DEFAULT_KB_FILE,
) -> dict[str, Any]:
    """Orkestrator offline Modul 2: memuat data Modul 1 dan menyimpan `passages.jsonl` & `knowledge_triples.jsonl`."""
    extracted_items = load_extracted_items(extracted_dir)
    passages = build_passages(extracted_items)
    triples = build_knowledge_triples(extracted_items)
    save_jsonl(passages, passages_output)  # type: ignore[arg-type]
    save_jsonl(triples, triples_output)  # type: ignore[arg-type]
    return {
        "passages_count": len(passages),
        "triples_count": len(triples),
        "passages_output": str(passages_output),
        "triples_output": str(triples_output),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocessing & Pembentukan Korpus Passage + Knowledge Triples (Anggota 2)."
    )
    parser.add_argument("--extracted-dir", type=Path, default=EXTRACTED_DATA_DIR)
    parser.add_argument("--passages-out", type=Path, default=DEFAULT_CORPUS_FILE)
    parser.add_argument("--triples-out", type=Path, default=DEFAULT_KB_FILE)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    summary = build_and_save_corpus(
        args.extracted_dir,
        passages_output=args.passages_out,
        triples_output=args.triples_out,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
