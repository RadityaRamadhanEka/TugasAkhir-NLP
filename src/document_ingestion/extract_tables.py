"""Ekstraksi tabel kurikulum dari PDF menggunakan pdfplumber.

Modul ini merupakan bagian dari tugas Anggota 1 (`src/document_ingestion/`) untuk
mengekstrak seluruh tabel dari Buku Pedoman Kurikulum 2024 TIF UB secara deterministik
(tanpa LLM) ke dalam struktur JSON yang siap dikonsumsi Anggota 2 (`build_passages` dan
`build_knowledge_triples`).

Menangani 5 kategori tabel utama pada dokumen:
1. `regular`            : Versi dokumen, Tabel 3.1 (CPL), 6.1-6.4, 7.1-7.4, 9.9-9.10, 10.1 (MBKM)
2. `cpl_matrix`         : Tabel 4.1 (Matriks Bahan Kajian vs 10 kode CPL bertanda centang `✓`)
3. `semester_schedule`  : Tabel distribusi Semester 1-8, Semester Antara (A/B), & Tabel 9.11
4. `transition_mapping` : Tabel 9.1-9.8 (Kurikulum Lama 2020 vs Kurikulum Baru 2024)
5. `syllabus_card`      : Kartu Silabus Mata Kuliah di Bab 11 (hal. PDF 50-100)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

from config.settings import DEFAULT_RAW_PDF, EXTRACTED_DATA_DIR
from src.document_ingestion.extract_text import (
    FOOTER_HEIGHT_PT,
    _extract_doc_page,
    _normalize_whitespace,
    _update_section_state,
)

TABLE_SETTINGS: dict[str, Any] = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
}

DEFAULT_TABLES_OUTPUT = EXTRACTED_DATA_DIR / "tables.json"

SEMESTER_HEADERS = [
    "No",
    "Kode MK",
    "Nama MK",
    "SKS",
    "Praktikum",
    "Prasyarat_Kode",
    "Prasyarat_MK",
    "Prasyarat_Nilai",
]

TRANSITION_HEADERS = [
    "Lama_Kode_MK",
    "Lama_Nama_MK",
    "Lama_SKS",
    "Baru_Kode_MK",
    "Baru_Nama_MK",
    "Baru_SKS",
]

SYLLABUS_HEADERS = ["Kode MK", "Nama MK", "SKS", "Bagian", "Isi"]


def _clean_cell(value: str | None, *, preserve_newlines: bool = False) -> str:
    """Membersihkan nilai sel tabel dari spasi berlebih dan artefak pemenggalan kode MK."""
    if not value:
        return ""
    if preserve_newlines:
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in value.splitlines()]
        text = "\n".join(ln for ln in lines if ln)
    else:
        text = re.sub(r"\s+", " ", value).strip()
    # Perbaiki kode MK yang terpotong tanda hubung (mis. "MPK60001- 5" -> "MPK60001-5")
    text = re.sub(r"\b([A-Z]{3}\d{5})-\s+(\d+)\b", r"\1-\2", text)
    return text


def _parse_int(value: str) -> int | None:
    """Mengonversi teks angka (mis. '3' atau '1.') menjadi int bila memungkinkan."""
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def _detect_caption_above(
    body_crop: pdfplumber.page.CroppedPage,
    table_bbox: tuple[float, float, float, float],
    page_width: float,
    prev_table_bottom: float = 0.0,
) -> str | None:
    """Mencari judul tabel (`Tabel X.Y ...`) tepat di atas bounding box tabel."""
    _, top, _, _ = table_bbox
    search_top = max(prev_table_bottom, top - 45.0, 0.0)
    if top - search_top < 6.0:
        return None

    above_crop = body_crop.crop((0.0, search_top, page_width, top))
    above_text = (above_crop.extract_text(x_tolerance=2, y_tolerance=3) or "").strip()
    if not above_text:
        return None

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in above_text.splitlines() if ln.strip()]
    for idx in range(len(lines) - 1, -1, -1):
        if re.match(r"^Tabel\s+\d+\.\d+", lines[idx], flags=re.IGNORECASE):
            # Gabungkan jika judul tabel terbungkus ke baris berikutnya
            caption = lines[idx]
            if idx + 1 < len(lines) and not re.match(r"^(Tabel|Gambar|\d+\.)", lines[idx + 1]):
                caption = f"{caption} {lines[idx + 1]}"
            return caption.strip()

    # Kasus khusus halaman 3: tabel versi dokumen
    for ln in reversed(lines):
        if "Versi dan Revisi Dokumen" in ln:
            return ln

    return None


def _collapse_padded_grid(
    table: pdfplumber.table.Table,
    raw_rows: list[list[str | None]],
    *,
    preserve_newlines: bool = False,
) -> list[list[str]]:
    """Menyusutkan kolom padding/spacer dari tabel MS Word berdasarkan overlap koordinat X.

    Pada banyak tabel Word yang memiliki padding/shading header (mis. 12 kolom untuk 4 kolom asli),
    teks header jatuh di kolom spacer bagian dalam sedangkan teks isi di kolom luar.
    Fungsi ini menentukan interval kolom sejati dari baris-baris isi lalu memetakan setiap sel
    ke kolom yang tumpang tindih secara horizontal.
    """
    if not raw_rows:
        return []

    # Kumpulkan baris-baris yang punya isi teks dan ekstrak interval (x0, x1) tiap sel non-kosong
    row_cell_items: list[list[tuple[float, float, str]]] = []
    for r_idx, raw_row in enumerate(raw_rows):
        row_obj = table.rows[r_idx]
        items: list[tuple[float, float, str]] = []
        for c_idx, val in enumerate(raw_row):
            cleaned = _clean_cell(val, preserve_newlines=preserve_newlines)
            if not cleaned:
                continue
            cell_bbox = row_obj.cells[c_idx]
            if cell_bbox is None:
                continue
            items.append((float(cell_bbox[0]), float(cell_bbox[2]), cleaned))
        if items:
            row_cell_items.append(items)

    if not row_cell_items:
        return []

    # Pilih jumlah kolom target dari baris dengan jumlah sel non-kosong terbanyak
    max_cols = max(len(items) for items in row_cell_items)
    # Kumpulkan interval X referensi dari baris-baris yang memiliki tepat `max_cols` sel
    ref_rows = [items for items in row_cell_items if len(items) == max_cols]
    col_intervals: list[tuple[float, float]] = []
    for k in range(max_cols):
        x0 = min(r[k][0] for r in ref_rows)
        x1 = max(r[k][1] for r in ref_rows)
        col_intervals.append((x0, x1))

    # Petakan setiap baris ke `max_cols` kolom sejati berdasarkan overlap horizontal terbesar
    collapsed: list[list[str]] = []
    for items in row_cell_items:
        mapped = [""] * max_cols
        for x0, x1, text in items:
            cx = (x0 + x1) / 2.0
            best_col = 0
            best_score = -1.0
            for k, (ix0, ix1) in enumerate(col_intervals):
                overlap = max(0.0, min(x1, ix1) - max(x0, ix0))
                if overlap > best_score:
                    best_score = overlap
                    best_col = k
            if best_score <= 0.0:
                # Fallback ke kolom dengan titik tengah terdekat
                best_col = min(
                    range(max_cols),
                    key=lambda k: abs(cx - (col_intervals[k][0] + col_intervals[k][1]) / 2.0),
                )
            mapped[best_col] = f"{mapped[best_col]} {text}".strip() if mapped[best_col] else text
        collapsed.append(mapped)

    return collapsed


def _is_syllabus_table(raw_rows: list[list[str | None]]) -> bool:
    """Mendeteksi apakah tabel merupakan Kartu Silabus Mata Kuliah (Bab 11)."""
    if not raw_rows or len(raw_rows[0]) < 3:
        return False
    c0 = _clean_cell(raw_rows[0][0])
    c1 = _clean_cell(raw_rows[0][1])
    return c0.startswith("Kode MK") and c1.startswith("Nama MK")


def _is_cpl_matrix_table(raw_rows: list[list[str | None]]) -> bool:
    """Mendeteksi apakah tabel merupakan Tabel 4.1 (Matriks Bahan Kajian vs CPL)."""
    joined_top = " ".join(
        _clean_cell(cell)
        for row in raw_rows[:6]
        for cell in row
        if cell
    )
    return "Bahan Kajian" in joined_top and "IF_CPL" in joined_top


def _is_semester_schedule_table(raw_rows: list[list[str | None]]) -> bool:
    """Mendeteksi tabel distribusi MK per semester (Bab 6) atau Tabel 9.11 (8 kolom dgn Prasyarat)."""
    if not raw_rows or len(raw_rows[0]) != 8:
        return False
    top_text = " ".join(
        _clean_cell(cell)
        for row in raw_rows[:5]
        for cell in row
        if cell
    )
    return "Prasyarat" in top_text and "Kode MK" in top_text and "SKS" in top_text


def _is_transition_table(raw_rows: list[list[str | None]]) -> bool:
    """Mendeteksi Tabel 9.1-9.8 (Kurikulum Lama 2020 vs Kurikulum Baru 2024)."""
    top_text = " ".join(
        _clean_cell(cell)
        for row in raw_rows[:3]
        for cell in row
        if cell
    ).upper()
    return "KURIKULUM LAMA" in top_text and "KURIKULUM BARU" in top_text


def _parse_cpl_matrix(
    table: pdfplumber.table.Table,
    raw_rows: list[list[str | None]],
) -> tuple[list[str], list[list[str]], list[dict[str, Any]], list[str]]:
    """Mem-parse Tabel 4.1 (Matriks Bahan Kajian vs 10 kode CPL) memakai penyelarasan X."""
    quality_flags: list[str] = []

    # Cari baris header CPL (biasanya terpecah 2 baris: 'IF_CPL' dan '_S1', atau 'IF_CP' + 'L_KK3')
    cpl_header_rows: list[int] = []
    for r_idx, row in enumerate(raw_rows[:8]):
        row_txt = " ".join(_clean_cell(c) for c in row if c)
        if "IF_CP" in row_txt or re.search(r"_(S\d|P\d|KU\d|KK\d)", row_txt):
            cpl_header_rows.append(r_idx)

    # Kumpulkan koordinat X dan gabungan label untuk setiap kolom CPL
    cpl_cols_by_colidx: dict[int, dict[str, Any]] = {}
    for r_idx in cpl_header_rows:
        row_obj = table.rows[r_idx]
        for c_idx, val in enumerate(raw_rows[r_idx]):
            cleaned = _clean_cell(val)
            if not cleaned:
                continue
            bbox = row_obj.cells[c_idx]
            if bbox is None:
                continue
            if c_idx not in cpl_cols_by_colidx:
                cpl_cols_by_colidx[c_idx] = {
                    "x0": float(bbox[0]),
                    "x1": float(bbox[2]),
                    "parts": [cleaned],
                }
            else:
                cpl_cols_by_colidx[c_idx]["parts"].append(cleaned)

    cpl_columns: list[tuple[str, float]] = []
    for c_idx in sorted(cpl_cols_by_colidx):
        info = cpl_cols_by_colidx[c_idx]
        code = "".join(info["parts"]).replace(" ", "")
        cx = (info["x0"] + info["x1"]) / 2.0
        cpl_columns.append((code, cx))

    cpl_codes = [code for code, _ in cpl_columns]
    headers = ["Bahan Kajian", *cpl_codes]

    data_start = (max(cpl_header_rows) + 1) if cpl_header_rows else 6
    clean_rows: list[list[str]] = []
    records: list[dict[str, Any]] = []

    for r_idx in range(data_start, len(raw_rows)):
        row_vals = raw_rows[r_idx]
        row_obj = table.rows[r_idx]
        bahan_kajian = _clean_cell(row_vals[0]) if row_vals else ""
        if not bahan_kajian:
            continue

        checked_flags = [""] * len(cpl_columns)
        matched_cpls: list[str] = []

        for c_idx in range(1, len(row_vals)):
            cell_txt = _clean_cell(row_vals[c_idx])
            if "✓" not in cell_txt and "✔" not in cell_txt and cell_txt.lower() != "v":
                continue
            bbox = row_obj.cells[c_idx]
            if bbox is None:
                continue
            x0, x1 = float(bbox[0]), float(bbox[2])
            # Cocokkan ke kolom CPL yang titik tengahnya berada dalam interval sel tanda centang
            matched_idx = None
            for k, (_, cx) in enumerate(cpl_columns):
                if (x0 - 2.0) <= cx <= (x1 + 2.0):
                    matched_idx = k
                    break
            if matched_idx is None and cpl_columns:
                cell_cx = (x0 + x1) / 2.0
                matched_idx = min(range(len(cpl_columns)), key=lambda k: abs(cell_cx - cpl_columns[k][1]))
            if matched_idx is not None:
                checked_flags[matched_idx] = "✓"
                code = cpl_columns[matched_idx][0]
                if code not in matched_cpls:
                    matched_cpls.append(code)

        clean_rows.append([bahan_kajian, *checked_flags])
        records.append(
            {
                "bahan_kajian": bahan_kajian,
                "cpl_codes": matched_cpls,
                "cpl_count": len(matched_cpls),
            }
        )

    if len(cpl_codes) != 10:
        quality_flags.append(f"unexpected_cpl_column_count:{len(cpl_codes)}")

    return headers, clean_rows, records, quality_flags


def _parse_semester_schedule(
    raw_rows: list[list[str | None]],
    caption_above: str | None,
) -> tuple[str, list[str], list[list[str]], list[dict[str, Any]], dict[str, Any]]:
    """Mem-parse tabel distribusi semester (Bab 6) dan Tabel 9.11."""
    semester_label: str | None = None
    semester_num: int | str | None = None
    data_start = 0

    for r_idx, row in enumerate(raw_rows[:6]):
        c0 = _clean_cell(row[0])
        if re.match(r"^Semester\s+", c0, flags=re.IGNORECASE):
            semester_label = c0
            num_match = re.search(r"Semester\s+(\d+)", c0, flags=re.IGNORECASE)
            if num_match:
                semester_num = int(num_match.group(1))
            else:
                semester_num = c0
        row_joined = " ".join(_clean_cell(c) for c in row if c)
        if "Mata Kuliah" in row_joined and "Nilai" in row_joined:
            data_start = r_idx + 1

    if semester_label:
        table_title = f"Distribusi Mata Kuliah {semester_label}"
    elif caption_above:
        table_title = caption_above
    else:
        table_title = "Distribusi Mata Kuliah"

    clean_rows: list[list[str]] = []
    records: list[dict[str, Any]] = []
    total_sks: int | None = None

    for row in raw_rows[data_start:]:
        cleaned = [_clean_cell(c) for c in row]
        if not any(cleaned):
            continue

        # Baris Total SKS
        if cleaned[0].lower() == "total":
            total_sks = _parse_int(cleaned[3])
            clean_rows.append(cleaned)
            continue

        no_val = cleaned[0]
        kode_mk = cleaned[1]
        nama_mk = cleaned[2]
        sks_str = cleaned[3]
        praktikum_str = cleaned[4]
        prasyarat_kode = cleaned[5]
        prasyarat_mk = cleaned[6]
        prasyarat_nilai = cleaned[7]

        # Tangani baris lanjutan (mis. jika satu MK punya 2 baris prasyarat tanpa No/Nama MK)
        if not no_val and not nama_mk and records and (prasyarat_kode or prasyarat_mk):
            prev = records[-1]
            extra_kode = prasyarat_kode
            extra_mk = prasyarat_mk
            extra_nilai = prasyarat_nilai
            if extra_kode:
                prev["prasyarat_kode"] = (
                    f"{prev['prasyarat_kode']}; {extra_kode}".strip("; ")
                    if prev["prasyarat_kode"]
                    else extra_kode
                )
            if extra_mk:
                prev["prasyarat_mk"] = (
                    f"{prev['prasyarat_mk']}; {extra_mk}".strip("; ")
                    if prev["prasyarat_mk"]
                    else extra_mk
                )
            if extra_nilai:
                prev["prasyarat_nilai"] = (
                    f"{prev['prasyarat_nilai']}; {extra_nilai}".strip("; ")
                    if prev["prasyarat_nilai"]
                    else extra_nilai
                )
            clean_rows.append(cleaned)
            continue

        clean_rows.append(cleaned)
        record: dict[str, Any] = {
            "no": _parse_int(no_val),
            "kode_mk": kode_mk or None,
            "nama_mk": nama_mk,
            "sks": _parse_int(sks_str),
            "praktikum": ("✓" in praktikum_str or "✔" in praktikum_str),
            "prasyarat_kode": prasyarat_kode or None,
            "prasyarat_mk": prasyarat_mk or None,
            "prasyarat_nilai": prasyarat_nilai or None,
        }
        if semester_num is not None:
            record["semester"] = semester_num
        records.append(record)

    extra_meta: dict[str, Any] = {}
    if semester_num is not None:
        extra_meta["semester"] = semester_num
    if total_sks is not None:
        extra_meta["total_sks"] = total_sks

    return table_title, SEMESTER_HEADERS, clean_rows, records, extra_meta


def _parse_transition_mapping(
    table: pdfplumber.table.Table,
    raw_rows: list[list[str | None]],
) -> tuple[list[str], list[list[str]], list[dict[str, Any]]]:
    """Mem-parse Tabel 9.1-9.8 (Kurikulum Lama 2020 vs Kurikulum Baru 2024)."""
    # Jika jumlah kolom > 6 (mis. Tabel 9.8 punya 7 kolom karena kolom kosong), buang kolom yang seluruhnya kosong
    num_cols = len(raw_rows[0]) if raw_rows else 0
    if num_cols > 6:
        non_empty_cols = [
            c_idx
            for c_idx in range(num_cols)
            if any(_clean_cell(r[c_idx]) for r in raw_rows if c_idx < len(r))
        ]
        normalized_rows = [
            [_clean_cell(r[c_idx]) for c_idx in non_empty_cols]
            for r in raw_rows
        ]
    else:
        normalized_rows = [[_clean_cell(c) for c in r] for r in raw_rows]

    # Lewati baris-baris header ("KURIKULUM LAMA", "Kode MK", baris kosong)
    data_start = 0
    for r_idx, row in enumerate(normalized_rows[:4]):
        joined = " ".join(row).upper()
        if "KODE MK" in joined and "NAMA MATA KULIAH" in joined:
            data_start = r_idx + 1

    clean_rows: list[list[str]] = []
    records: list[dict[str, Any]] = []

    for row in normalized_rows[data_start:]:
        if not any(row):
            continue
        # Pastikan panjang 6 kolom
        padded = (row + [""] * 6)[:6]

        # Gabungkan baris pecahan teks (mis. di Tabel 9.8: ['', '', '', '', 'Komputer', ''])
        has_codes_or_sks = bool(padded[0] or padded[2] or padded[3] or padded[5])
        if not has_codes_or_sks and records:
            if padded[1]:
                records[-1]["lama_nama_mk"] = f"{records[-1]['lama_nama_mk'] or ''} {padded[1]}".strip()
                clean_rows[-1][1] = f"{clean_rows[-1][1]} {padded[1]}".strip()
            if padded[4]:
                records[-1]["baru_nama_mk"] = f"{records[-1]['baru_nama_mk'] or ''} {padded[4]}".strip()
                clean_rows[-1][4] = f"{clean_rows[-1][4]} {padded[4]}".strip()
            continue

        clean_rows.append(padded)
        records.append(
            {
                "lama_kode_mk": padded[0] or None,
                "lama_nama_mk": padded[1] or None,
                "lama_sks": _parse_int(padded[2]),
                "baru_kode_mk": padded[3] or None,
                "baru_nama_mk": padded[4] or None,
                "baru_sks": _parse_int(padded[5]),
            }
        )

    return TRANSITION_HEADERS, clean_rows, records


def _parse_cpmk_items(cpmk_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Memecah blok teks CPMK pada kartu silabus menjadi list terstruktur & mendeteksi artefak."""
    flags: list[str] = []
    if re.search(r"CPMK-\d+\s*\(%\)", cpmk_text):
        flags.append("syllabus_template_artifact")
    if "(CPL: )" in cpmk_text or "(CPL:)" in cpmk_text:
        flags.append("empty_cpl_reference")

    # Hapus judul bagian jika ada di awal
    cleaned = re.sub(
        r"^(?:Sub\s+)?Capaian\s+Pembelajar(?:an)?\s+Mata\s+Kuliah\s*:?\s*",
        "",
        cpmk_text,
        flags=re.IGNORECASE,
    ).strip()

    items: list[dict[str, Any]] = []
    matches = list(re.finditer(r"(CPMK-\d+)\s*[:.]\s*", cleaned))
    for i, m in enumerate(matches):
        code = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
        body = re.sub(r"\s+", " ", cleaned[start:end]).strip()
        cpls = re.findall(r"IF_CPL_[A-Z]+\d+", body)
        items.append({"kode": code, "deskripsi": body, "cpl": cpls})

    return items, flags


def _parse_syllabus_card(
    raw_rows: list[list[str | None]],
) -> tuple[str, list[str], list[list[str]], list[dict[str, Any]], dict[str, Any], list[str]]:
    """Mem-parse satu blok Kartu Silabus Mata Kuliah (Bab 11)."""
    quality_flags: list[str] = []

    kode_raw = _clean_cell(raw_rows[0][0], preserve_newlines=True)
    nama_raw = _clean_cell(raw_rows[0][1], preserve_newlines=True)
    sks_raw = _clean_cell(raw_rows[0][2], preserve_newlines=True)

    kode_mk = re.sub(r"^Kode\s+MK\s*:?\s*", "", kode_raw, flags=re.IGNORECASE).strip()
    kode_mk = re.sub(r"\s+", "", kode_mk)
    nama_mk = re.sub(r"^Nama\s+MK\s*:?\s*", "", nama_raw, flags=re.IGNORECASE).strip()
    nama_mk = re.sub(r"\s+", " ", nama_mk)
    sks = _parse_int(sks_raw)

    deskripsi = ""
    bahan_kajian_text = ""
    cpmk_text = ""
    other_segments: list[str] = []
    clean_rows: list[list[str]] = []

    for row in raw_rows[1:]:
        cell_text = _clean_cell(
            " ".join(c for c in row if c),
            preserve_newlines=True,
        )
        if not cell_text:
            continue

        lower = cell_text.lower()
        if lower.startswith("deskripsi mata kuliah"):
            val = re.sub(r"^Deskripsi\s+Mata\s+Kuliah\s*:?\s*", "", cell_text, flags=re.IGNORECASE).strip()
            deskripsi = f"{deskripsi}\n{val}".strip() if deskripsi else val
            clean_rows.append([kode_mk, nama_mk, str(sks or ""), "Deskripsi", val])
        elif lower.startswith("bahan kajian"):
            val = re.sub(r"^Bahan\s+Kajian\s*:?\s*", "", cell_text, flags=re.IGNORECASE).strip()
            bahan_kajian_text = f"{bahan_kajian_text}\n{val}".strip() if bahan_kajian_text else val
            clean_rows.append([kode_mk, nama_mk, str(sks or ""), "Bahan Kajian", val])
        elif "capaian pembelajar" in lower[:60] or re.match(r"^CPMK-\d+", cell_text):
            cpmk_text = f"{cpmk_text}\n{cell_text}".strip() if cpmk_text else cell_text
            clean_rows.append([kode_mk, nama_mk, str(sks or ""), "CPMK", cell_text])
        else:
            # Pada beberapa silabus (mis. P099) baris deskripsi tidak diawali label "Deskripsi Mata Kuliah:",
            # atau pada halaman lanjutan baris berisi lanjutan Bahan Kajian bernomor "1) ..." / "4) ..."
            if not deskripsi and not bahan_kajian_text and not cpmk_text and not re.match(r"^\d+[.)]\s*", cell_text):
                deskripsi = cell_text
                clean_rows.append([kode_mk, nama_mk, str(sks or ""), "Deskripsi", cell_text])
            elif re.match(r"^\d+[.)]\s*", cell_text):
                bahan_kajian_text = f"{bahan_kajian_text}\n{cell_text}".strip() if bahan_kajian_text else cell_text
                clean_rows.append([kode_mk, nama_mk, str(sks or ""), "Bahan Kajian (Lanjutan)", cell_text])
            else:
                other_segments.append(cell_text)
                clean_rows.append([kode_mk, nama_mk, str(sks or ""), "Lanjutan", cell_text])

    # Pecah bahan kajian menjadi daftar butir bila bernomor
    bahan_kajian_list: list[str] = []
    if bahan_kajian_text:
        bk_splits = re.split(r"(?:^|\n)\s*\d+\s*[.)]\s*", bahan_kajian_text)
        bahan_kajian_list = [
            re.sub(r"\s+", " ", part).strip()
            for part in bk_splits
            if part.strip()
        ]

    cpmk_items, cpmk_flags = _parse_cpmk_items(cpmk_text)
    quality_flags.extend(cpmk_flags)

    table_title = f"Silabus {kode_mk} - {nama_mk}" if kode_mk else f"Silabus {nama_mk}"
    record: dict[str, Any] = {
        "kode_mk": kode_mk,
        "nama_mk": nama_mk,
        "sks": sks,
        "deskripsi": re.sub(r"\s+", " ", deskripsi).strip() or None,
        "bahan_kajian": bahan_kajian_list,
        "cpmk": cpmk_items,
        "other_text": " ".join(other_segments).strip() or None,
    }
    extra_meta = {
        "course_code": kode_mk,
        "course_name": nama_mk,
        "sks": sks,
    }
    return table_title, SYLLABUS_HEADERS, clean_rows, [record], extra_meta, quality_flags


def _parse_regular_table(
    table: pdfplumber.table.Table,
    raw_rows: list[list[str | None]],
    *,
    prev_table: dict[str, Any] | None,
    has_caption_above: bool,
) -> tuple[list[str], list[list[str]], list[dict[str, Any]], bool]:
    """Mem-parse tabel reguler (Versi dokumen, Tabel 3.1, 6.1-6.4, 7.1-7.4, 9.9-9.10, 10.1)."""
    # Cek apakah tabel ini merupakan lanjutan lintas halaman (tanpa header & tanpa caption baru)
    is_continuation = False
    first_non_empty = next(
        ([_clean_cell(c) for c in r] for r in raw_rows if any(_clean_cell(c) for c in r)),
        [],
    )
    first_joined = " ".join(first_non_empty).lower()
    looks_like_header = len(first_joined) <= 90 and any(
        kw in first_joined
        for kw in ("kode mk", "kode cpl", "versi", "kegiatan", "learning path", "nama mk")
    )

    if not has_caption_above and not looks_like_header and prev_table is not None:
        is_continuation = True

    # Untuk Tabel 10.1 (teks sangat panjang) & Tabel 3.1 (CPL) tidak perlu collapse agresif bila sudah 3 kolom
    raw_col_count = len(raw_rows[0]) if raw_rows else 0
    if is_continuation and prev_table and raw_col_count == len(prev_table["headers"]):
        collapsed = [[_clean_cell(c) for c in r] for r in raw_rows if any(_clean_cell(c) for c in r)]
    elif raw_col_count <= 5 and not any(
        all(_clean_cell(r[c]) == "" for r in raw_rows) for c in range(raw_col_count)
    ):
        collapsed = [[_clean_cell(c) for c in r] for r in raw_rows if any(_clean_cell(c) for c in r)]
    else:
        collapsed = _collapse_padded_grid(table, raw_rows)

    if not collapsed:
        return [], [], [], is_continuation

    if is_continuation and prev_table is not None:
        headers = list(prev_table["headers"])
        data_rows = collapsed
    else:
        headers = [h or f"col_{i + 1}" for i, h in enumerate(collapsed[0])]
        data_rows = collapsed[1:]

    # Khusus Tabel 3.1 (CPL): gabungkan baris pecahan deskripsi (kolom No & Kode CPL kosong) & tandai kategori A/B/C/D
    is_cpl_table = headers == ["No", "Kode CPL", "Deskripsi CPL"]
    if is_cpl_table:
        merged_rows: list[list[str]] = []
        records: list[dict[str, Any]] = []
        current_group = (
            prev_table["metadata"].get("last_cpl_group")
            if (is_continuation and prev_table)
            else None
        )
        for row in data_rows:
            padded = (row + [""] * 3)[:3]
            no_col, kode_col, desc_col = padded
            # Baris judul kelompok CPL (mis. ['A', 'SIKAP', ''] atau ['D', 'KETERAMPILAN KHUSUS (KK)', ''])
            if re.fullmatch(r"[A-D]", no_col) and not desc_col:
                current_group = f"{no_col}. {kode_col}"
                merged_rows.append(padded)
                continue
            # Baris lanjutan deskripsi CPL (kolom No & Kode CPL kosong)
            if not no_col and not kode_col and desc_col and records:
                records[-1]["deskripsi_cpl"] = f"{records[-1]['deskripsi_cpl']} {desc_col}".strip()
                merged_rows[-1][2] = f"{merged_rows[-1][2]} {desc_col}".strip()
                continue
            merged_rows.append(padded)
            records.append(
                {
                    "kategori_cpl": current_group,
                    "kode_cpl": kode_col,
                    "deskripsi_cpl": desc_col,
                }
            )
        return headers, merged_rows, records, is_continuation

    # Tabel reguler umum -> konversi setiap baris menjadi dict berbasis `headers`
    clean_rows: list[list[str]] = []
    records = []
    col_keys = [re.sub(r"[^a-z0-9]+", "_", h.lower()).strip("_") or f"col_{i+1}" for i, h in enumerate(headers)]

    for row in data_rows:
        padded = (row + [""] * len(headers))[: len(headers)]
        if not any(padded):
            continue
        clean_rows.append(padded)
        rec: dict[str, Any] = {}
        for key, val in zip(col_keys, padded):
            if key in {"sks", "no"} and re.fullmatch(r"\d+\.?", val):
                rec[key] = _parse_int(val)
            else:
                rec[key] = val or None
        records.append(rec)

    return headers, clean_rows, records, is_continuation


def extract_tables(
    pdf_path: str | Path = DEFAULT_RAW_PDF,
    *,
    save_output: bool = False,
    output_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Mengekstrak seluruh tabel dari PDF beserta judul tabel, `pdf_page`, dan `doc_page`.

    Args:
        pdf_path: Path menuju file PDF korpus.
        save_output: Jika True, hasil ekstraksi langsung disimpan ke file JSON.
        output_path: Path file tujuan (default: `data/extracted/tables.json`).

    Returns:
        List dict berisi `table_id`, `pdf_page`, `doc_page`, `section`, `table_title`,
        `table_type`, `is_continuation`, `continuation_of`, `headers`, `rows`, `records`,
        `content_type="table"`, dan `metadata`.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File PDF tidak ditemukan: {path}")

    extracted_tables: list[dict[str, Any]] = []
    current_section = "Sampul"
    current_subsection: str | None = None
    current_chapter = 0

    with pdfplumber.open(path) as pdf:
        for pdf_page, page in enumerate(pdf.pages, start=1):
            width = float(page.width)
            height = float(page.height)
            doc_page = _extract_doc_page(page, pdf_page)
            body_crop = page.crop((0.0, 0.0, width, max(0.0, height - FOOTER_HEIGHT_PT)))

            raw_body_text = _normalize_whitespace(
                body_crop.extract_text(x_tolerance=2, y_tolerance=3) or ""
            )
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

            found_tables = body_crop.find_tables(table_settings=TABLE_SETTINGS)
            prev_bottom = 0.0
            valid_idx = 0

            for tbl in found_tables:
                raw_rows = tbl.extract()
                if not raw_rows or (len(raw_rows) < 2 and len(raw_rows[0]) < 2):
                    continue

                valid_idx += 1
                table_id = f"tbl_p{pdf_page:03d}_{valid_idx:02d}"
                caption_above = _detect_caption_above(body_crop, tbl.bbox, width, prev_table_bottom=prev_bottom)
                prev_bottom = float(tbl.bbox[3])

                prev_table = extracted_tables[-1] if extracted_tables else None
                quality_flags: list[str] = []
                extra_meta: dict[str, Any] = {}
                is_continuation = False
                continuation_of: str | None = None

                # Klasifikasi dan parsing sesuai tipe tabel
                if _is_syllabus_table(raw_rows):
                    table_type = "syllabus_card"
                    (
                        table_title,
                        headers,
                        clean_rows,
                        records,
                        extra_meta,
                        quality_flags,
                    ) = _parse_syllabus_card(raw_rows)

                    if (
                        prev_table is not None
                        and prev_table["table_type"] == "syllabus_card"
                        and prev_table["metadata"].get("course_code") == extra_meta.get("course_code")
                        and extra_meta.get("course_code")
                    ):
                        is_continuation = True
                        continuation_of = prev_table["continuation_of"] or prev_table["table_id"]

                elif _is_cpl_matrix_table(raw_rows):
                    table_type = "cpl_matrix"
                    headers, clean_rows, records, quality_flags = _parse_cpl_matrix(tbl, raw_rows)
                    if caption_above:
                        table_title = caption_above
                    elif prev_table is not None and prev_table["table_type"] == "cpl_matrix":
                        is_continuation = True
                        continuation_of = prev_table["continuation_of"] or prev_table["table_id"]
                        table_title = prev_table["table_title"]
                    else:
                        table_title = "Tabel 4.1 Pemetaan Bahan Kajian dengan Capaian Pembelajaran Lulusan (CPL)"

                elif _is_semester_schedule_table(raw_rows):
                    table_type = "semester_schedule"
                    (
                        table_title,
                        headers,
                        clean_rows,
                        records,
                        extra_meta,
                    ) = _parse_semester_schedule(raw_rows, caption_above)

                elif _is_transition_table(raw_rows):
                    table_type = "transition_mapping"
                    headers, clean_rows, records = _parse_transition_mapping(tbl, raw_rows)
                    if caption_above:
                        table_title = caption_above
                    elif prev_table is not None and prev_table["table_type"] == "transition_mapping":
                        is_continuation = True
                        continuation_of = prev_table["continuation_of"] or prev_table["table_id"]
                        table_title = prev_table["table_title"]
                    else:
                        table_title = "Tabel Perubahan Kurikulum"

                else:
                    table_type = "regular"
                    headers, clean_rows, records, is_continuation = _parse_regular_table(
                        tbl,
                        raw_rows,
                        prev_table=prev_table,
                        has_caption_above=bool(caption_above),
                    )
                    if is_continuation and prev_table is not None:
                        continuation_of = prev_table["continuation_of"] or prev_table["table_id"]
                        table_title = prev_table["table_title"]
                    else:
                        table_title = caption_above or f"Tabel Halaman {pdf_page}"

                    # Simpan kategori CPL terakhir agar halaman lanjutan Tabel 3.1 tetap mewarisinya
                    if headers == ["No", "Kode CPL", "Deskripsi CPL"] and records:
                        extra_meta["last_cpl_group"] = records[-1].get("kategori_cpl")

                if not records:
                    quality_flags.append("empty_records")

                extracted_tables.append(
                    {
                        "table_id": table_id,
                        "pdf_page": pdf_page,
                        "doc_page": doc_page,
                        "section": current_section,
                        "table_title": table_title,
                        "table_type": table_type,
                        "content_type": "table",
                        "is_continuation": is_continuation,
                        "continuation_of": continuation_of,
                        "headers": headers,
                        "rows": clean_rows,
                        "records": records,
                        "metadata": {
                            "row_count": len(clean_rows),
                            "record_count": len(records),
                            "col_count": len(headers),
                            "bbox": [round(float(v), 2) for v in tbl.bbox],
                            "extraction_library": "pdfplumber",
                            "quality_flags": quality_flags,
                            **extra_meta,
                        },
                    }
                )

    if save_output:
        target = Path(output_path) if output_path is not None else DEFAULT_TABLES_OUTPUT
        save_extracted_tables(extracted_tables, target)

    return extracted_tables


def save_extracted_tables(
    tables: list[dict[str, Any]],
    output_path: str | Path = DEFAULT_TABLES_OUTPUT,
) -> Path:
    """Menyimpan hasil ekstraksi tabel ke file JSON."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        json.dump(tables, file, ensure_ascii=False, indent=2)
    return target


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ekstraksi tabel kurikulum dari PDF Kurikulum 2024 TIF UB dengan pdfplumber."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_RAW_PDF,
        help="Path file PDF sumber (default: config.settings.DEFAULT_RAW_PDF).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_TABLES_OUTPUT,
        help="Path file JSON keluaran (default: data/extracted/tables.json).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    tables = extract_tables(
        pdf_path=args.pdf,
        save_output=True,
        output_path=args.output,
    )
    by_type: dict[str, int] = {}
    continuations = 0
    flagged = 0
    for tbl in tables:
        t_type = tbl["table_type"]
        by_type[t_type] = by_type.get(t_type, 0) + 1
        if tbl["is_continuation"]:
            continuations += 1
        if tbl["metadata"]["quality_flags"]:
            flagged += 1

    print(f"Ekstraksi tabel selesai: {len(tables)} blok tabel diekstrak.")
    for t_type, count in sorted(by_type.items()):
        print(f"  - {t_type:20s}: {count}")
    print(f"- Tabel lanjutan lintas halaman : {continuations}")
    print(f"- Tabel dengan quality_flags    : {flagged}")
    print(f"- Output disimpan di            : {args.output}")


if __name__ == "__main__":
    main()
