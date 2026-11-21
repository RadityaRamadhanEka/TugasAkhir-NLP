"""Ekstraksi teks per halaman menggunakan pdfplumber beserta metadata sumber.

Modul ini merupakan bagian dari tugas Anggota 1 (`src/document_ingestion/`) untuk
mengekstrak teks naratif dari PDF pedoman kurikulum secara deterministik (tanpa LLM),
memisahkan nomor halaman tercetak (`doc_page`) dari area footer, melacak bab/subbab
(`section`/`subsection`), serta mengecualikan area tabel agar tidak terjadi duplikasi
saat Anggota 2 membentuk dataset passage.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

from config.settings import DEFAULT_RAW_PDF, EXTRACTED_DATA_DIR

# Batas zona footer (dalam point dari tepi bawah halaman).
# Terverifikasi untuk seluruh 100 halaman (portrait 842 pt maupun landscape 595 pt).
FOOTER_HEIGHT_PT = 68.0
TABLE_BBOX_MARGIN_PT = 1.5

FRONT_MATTER_HEADINGS: dict[str, str] = {
    "KATA PENGANTAR": "Kata Pengantar",
    "VERSI DAN REVISI DOKUMEN PANDUAN KURIKULUM": "Versi dan Revisi Dokumen Panduan Kurikulum",
    "DAFTAR ISI": "Daftar Isi",
    "DAFTAR TABEL": "Daftar Tabel",
    "DAFTAR GAMBAR": "Daftar Gambar",
    "TIM PENYUSUN KURIKULUM": "Tim Penyusun Kurikulum",
}

FRONT_MATTER_SKIP_SUBSECTIONS = {"Daftar Isi", "Daftar Tabel", "Daftar Gambar"}

CHAPTER_TITLE_CASE_FIXES: dict[str, str] = {
    "(Cpl)": "(CPL)",
    "Cpl": "CPL",
    "Dan": "dan",
    "Pada": "pada",
    "Untuk": "untuk",
}

DEFAULT_TEXT_OUTPUT = EXTRACTED_DATA_DIR / "text_pages.json"


def _normalize_whitespace(text: str) -> str:
    """Merapikan spasi berlebih pada tiap baris sambil mempertahankan baris baru."""
    cleaned_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    # Hilangkan baris kosong di awal/akhir dan padatkan baris kosong beruntun
    result: list[str] = []
    for line in cleaned_lines:
        if not line:
            if result and result[-1] != "":
                result.append("")
        else:
            result.append(line)
    while result and result[-1] == "":
        result.pop()
    return "\n".join(result)


def _format_chapter_title(num: int, raw_title: str) -> str:
    """Mengubah judul bab kapital penuh menjadi format judul yang konsisten."""
    words = raw_title.strip().split()
    formatted = " ".join(
        word if word in {"(CPL)", "CPL", "MBKM", "SKS", "TIF", "UB"} else word.capitalize()
        for word in words
    )
    for wrong, right in CHAPTER_TITLE_CASE_FIXES.items():
        formatted = re.sub(rf"\b{re.escape(wrong)}\b", right, formatted)
    formatted = formatted.replace("(Cpl)", "(CPL)")
    return f"{num}. {formatted}"


def _extract_doc_page(page: pdfplumber.page.Page, pdf_page: int) -> str:
    """Mengambil nomor halaman tercetak (`doc_page`) dari area footer halaman."""
    if pdf_page == 1:
        return ""
    footer_top = max(0.0, float(page.height) - FOOTER_HEIGHT_PT)
    footer_crop = page.crop((0.0, footer_top, float(page.width), float(page.height)))
    footer_text = (footer_crop.extract_text(x_tolerance=2, y_tolerance=3) or "").strip()
    footer_compact = re.sub(r"\s+", "", footer_text)
    if re.fullmatch(r"([ivxlcdm]+|\d+)", footer_compact, flags=re.IGNORECASE):
        return footer_compact
    return ""


def _get_table_bboxes(body_crop: pdfplumber.page.CroppedPage) -> list[tuple[float, float, float, float]]:
    """Mendeteksi bounding box tabel bergaris di area isi halaman."""
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
    }
    bboxes: list[tuple[float, float, float, float]] = []
    for table in body_crop.find_tables(table_settings=table_settings):
        # Hanya anggap tabel valid bila memiliki minimal 2 baris atau 2 kolom
        rows = table.rows or []
        cols = table.columns or []
        if len(rows) >= 2 or len(cols) >= 2:
            bboxes.append(tuple(float(v) for v in table.bbox))
    return bboxes


def _is_inside_any_bbox(
    obj: dict[str, Any],
    bboxes: list[tuple[float, float, float, float]],
    margin: float = TABLE_BBOX_MARGIN_PT,
) -> bool:
    """Mengecek apakah titik tengah objek PDF berada di dalam salah satu bbox tabel."""
    if "x0" not in obj or "top" not in obj:
        return False
    cx = (float(obj["x0"]) + float(obj["x1"])) / 2.0
    cy = (float(obj["top"]) + float(obj["bottom"])) / 2.0
    for x0, top, x1, bottom in bboxes:
        if (x0 - margin) <= cx <= (x1 + margin) and (top - margin) <= cy <= (bottom + margin):
            return True
    return False


def _is_heading_line(line: str) -> bool:
    """Mendeteksi apakah satu baris merupakan judul bab, subbab, atau caption tabel/gambar."""
    stripped = line.strip()
    return bool(
        re.match(r"^(\d{1,2}\.\s+[A-Z]{2,}|\d{1,2}\.\d+\s+[A-Z]|[A-K]\.\s+(?:Deskripsi|Visi|Misi|Tujuan|Learning Path\s+))", stripped)
        or re.match(r"^(Tabel|Gambar)\s+\d+\.\d+", stripped)
        or stripped.upper() in FRONT_MATTER_HEADINGS
    )


def _extract_paragraphs(cropped_page: pdfplumber.page.CroppedPage) -> list[str]:
    """Membagi teks non-tabel pada halaman menjadi daftar paragraf berdasarkan jarak vertikal."""
    words = cropped_page.extract_words(
        x_tolerance=2,
        y_tolerance=3,
        keep_blank_chars=False,
        use_text_flow=False,
    )
    if not words:
        return []

    # Kelompokkan kata ke dalam baris berdasarkan koordinat `top`
    words_sorted = sorted(words, key=lambda w: (round(float(w["top"]), 1), float(w["x0"])))
    lines: list[dict[str, Any]] = []
    for word in words_sorted:
        w_top = float(word["top"])
        w_bottom = float(word["bottom"])
        if lines and abs(w_top - lines[-1]["top"]) <= 3.5:
            lines[-1]["words"].append(word)
            lines[-1]["bottom"] = max(lines[-1]["bottom"], w_bottom)
        else:
            lines.append({"top": w_top, "bottom": w_bottom, "words": [word]})

    formatted_lines: list[dict[str, Any]] = []
    for line in lines:
        line_words = sorted(line["words"], key=lambda w: float(w["x0"]))
        line_text = " ".join(w["text"] for w in line_words).strip()
        if line_text:
            formatted_lines.append(
                {
                    "top": line["top"],
                    "bottom": line["bottom"],
                    "height": max(line["bottom"] - line["top"], 8.0),
                    "text": line_text,
                }
            )

    if not formatted_lines:
        return []

    # Hitung jarak antar-baris untuk memisahkan paragraf / heading / butir daftar
    paragraphs: list[str] = []
    current_lines: list[str] = [formatted_lines[0]["text"]]

    for prev, curr in zip(formatted_lines, formatted_lines[1:]):
        gap = curr["top"] - prev["bottom"]
        is_wrapped_allcaps_heading = (
            _is_heading_line(prev["text"])
            and bool(re.fullmatch(r"[A-Z][A-Z\s,()/-]{2,}", curr["text"]))
        )
        is_new_block = (
            gap > max(prev["height"] * 0.75, 7.0)
            or _is_heading_line(curr["text"])
            or (_is_heading_line(prev["text"]) and not is_wrapped_allcaps_heading)
            or bool(re.match(r"^\d{1,2}\.\s+", curr["text"]))
        )
        if is_new_block:
            paragraphs.append(" ".join(current_lines).strip())
            current_lines = [curr["text"]]
        else:
            current_lines.append(curr["text"])

    if current_lines:
        paragraphs.append(" ".join(current_lines).strip())

    return [re.sub(r"\s+", " ", p).strip() for p in paragraphs if p.strip()]


def _update_section_state(
    body_text: str,
    pdf_page: int,
    current_section: str,
    current_subsection: str | None,
    current_chapter: int,
) -> tuple[str, str | None, int, list[str], list[str]]:
    """Memperbarui state `section` dan `subsection` berdasarkan heading pada halaman.

    Returns:
        Tuple `(section_akhir, subsection_akhir, chapter_akhir, sections_on_page, subsections_on_page)`.
    """
    if pdf_page == 1:
        return "Sampul", None, current_chapter, ["Sampul"], []

    lines = [ln.strip() for ln in body_text.splitlines() if ln.strip()]
    if not lines:
        return current_section, current_subsection, current_chapter, [current_section], (
            [current_subsection] if current_subsection else []
        )

    # 1. Cek judul bagian awal (front matter) di bagian atas halaman (pdf_page 2-7)
    if pdf_page <= 7:
        first_upper = lines[0].upper()
        for key, label in FRONT_MATTER_HEADINGS.items():
            if first_upper.startswith(key):
                return label, None, current_chapter, [label], []
        return current_section, current_subsection, current_chapter, [current_section], []

    sections_on_page: list[str] = []
    subsections_on_page: list[str] = []

    def _record_section(sec: str) -> None:
        if sec not in sections_on_page:
            sections_on_page.append(sec)

    def _record_subsection(sub: str | None) -> None:
        if sub and sub not in subsections_on_page:
            subsections_on_page.append(sub)

    # Jika baris pertama bukan judul bab baru, halaman ini melanjutkan bab sebelumnya
    first_is_new_chapter = False
    first_chap_match = re.match(r"^(\d{1,2})\.\s+([A-Z][A-Z0-9\s,()/-]{3,})$", lines[0])
    if first_chap_match and int(first_chap_match.group(1)) == current_chapter + 1:
        first_is_new_chapter = True
    if not first_is_new_chapter and current_section:
        _record_section(current_section)

    idx = 0
    while idx < len(lines):
        line = lines[idx]

        # 2. Deteksi Bab utama berurutan (1 s.d. 11) agar tidak tertukar dengan list bernomor (mis. "3. IISMA")
        chapter_match = re.match(r"^(\d{1,2})\.\s+([A-Z][A-Z0-9\s,()/-]{3,})$", line)
        if chapter_match:
            chap_num = int(chapter_match.group(1))
            if chap_num == current_chapter + 1:
                title_part = chapter_match.group(2).strip()
                # Tangani judul bab yang terpotong ke baris berikutnya (mis. Bab 9 -> "PERALIHAN")
                if idx + 1 < len(lines) and re.fullmatch(r"[A-Z][A-Z\s,()/-]{2,}", lines[idx + 1]):
                    next_line = lines[idx + 1].strip()
                    if not re.match(r"^(TABEL|GAMBAR|KODE)\b", next_line):
                        title_part = f"{title_part} {next_line}"
                        idx += 1
                current_chapter = chap_num
                current_section = _format_chapter_title(chap_num, title_part)
                current_subsection = None
                _record_section(current_section)
                idx += 1
                continue

        # 3. Deteksi subbab bernomor yang cocok dengan nomor bab aktif (mis. 7.1, 8.2, 9.1)
        if current_chapter > 0:
            sub_num_match = re.match(rf"^({current_chapter}\.\d+)\s+(.+)$", line)
            if sub_num_match:
                sub_title = sub_num_match.group(2).strip().rstrip(":")
                current_subsection = f"{sub_num_match.group(1)} {sub_title}"
                _record_subsection(current_subsection)
                idx += 1
                continue

            # 4. Deteksi subbab berhuruf pada Bab 1 (A-D) dan Bab 7 (A-K Learning Path)
            if current_chapter == 1:
                sub_alpha_b1 = re.match(r"^([A-D]\.\s+(?:Deskripsi|Visi|Misi|Tujuan))$", line)
                if sub_alpha_b1:
                    current_subsection = sub_alpha_b1.group(1).strip()
                    _record_subsection(current_subsection)
            elif current_chapter == 7:
                sub_alpha_b7 = re.match(r"^([A-K]\.\s+Learning Path\s+.+)$", line)
                if sub_alpha_b7:
                    current_subsection = sub_alpha_b7.group(1).strip()
                    _record_subsection(current_subsection)

        idx += 1

    if not subsections_on_page and current_subsection:
        _record_subsection(current_subsection)

    return current_section, current_subsection, current_chapter, sections_on_page, subsections_on_page


def extract_text_pages(
    pdf_path: str | Path = DEFAULT_RAW_PDF,
    *,
    exclude_tables: bool = True,
    save_output: bool = False,
    output_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Mengekstrak teks per halaman dari PDF menggunakan `pdfplumber`.

    Args:
        pdf_path: Path menuju file PDF korpus.
        exclude_tables: Jika True, teks di dalam bounding box tabel dikecualikan dari
            field `text` dan `paragraphs` (tetap disimpan di `raw_text`) untuk mencegah
            duplikasi dengan hasil `extract_tables.py`.
        save_output: Jika True, hasil ekstraksi langsung disimpan ke file JSON.
        output_path: Path tujuan file JSON (default: `data/extracted/text_pages.json`).

    Returns:
        List dict berisi minimal `pdf_page`, `doc_page`, `section`,
        `content_type="text"`, dan `text`, serta metadata pendukung.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File PDF tidak ditemukan: {path}")

    extracted_pages: list[dict[str, Any]] = []
    current_section = "Sampul"
    current_subsection: str | None = None
    current_chapter = 0

    with pdfplumber.open(path) as pdf:
        for pdf_page, page in enumerate(pdf.pages, start=1):
            width = float(page.width)
            height = float(page.height)
            orientation = "landscape" if width > height else "portrait"

            doc_page = _extract_doc_page(page, pdf_page)

            # Potong area badan halaman (di atas zona footer)
            body_bottom = max(0.0, height - FOOTER_HEIGHT_PT)
            body_crop = page.crop((0.0, 0.0, width, body_bottom))

            raw_body_text = _normalize_whitespace(
                body_crop.extract_text(x_tolerance=2, y_tolerance=3) or ""
            )

            # Perbarui pelacakan bab/subbab menggunakan teks badan halaman
            (
                current_section,
                current_subsection,
                current_chapter,
                sections_on_page,
                subsections_on_page,
            ) = _update_section_state(
                body_text=raw_body_text,
                pdf_page=pdf_page,
                current_section=current_section,
                current_subsection=current_subsection,
                current_chapter=current_chapter,
            )

            table_bboxes = _get_table_bboxes(body_crop) if exclude_tables else []
            has_tables_excluded = bool(table_bboxes)

            if table_bboxes:
                narrative_crop = body_crop.filter(
                    lambda obj, bboxes=table_bboxes: not _is_inside_any_bbox(obj, bboxes)
                )
            else:
                narrative_crop = body_crop

            narrative_text = _normalize_whitespace(
                narrative_crop.extract_text(x_tolerance=2, y_tolerance=3) or ""
            )
            paragraphs = _extract_paragraphs(narrative_crop)

            extracted_pages.append(
                {
                    "page_id": f"page_{pdf_page:03d}",
                    "pdf_page": pdf_page,
                    "doc_page": doc_page,
                    "section": current_section,
                    "subsection": subsections_on_page[0] if subsections_on_page else current_subsection,
                    "content_type": "text",
                    "text": narrative_text,
                    "raw_text": raw_body_text,
                    "paragraphs": paragraphs,
                    "has_tables_excluded": has_tables_excluded,
                    "has_visuals": len(page.images) > 0,
                    "metadata": {
                        "orientation": orientation,
                        "width_pt": round(width, 2),
                        "height_pt": round(height, 2),
                        "char_count": len(narrative_text),
                        "raw_char_count": len(raw_body_text),
                        "table_count_excluded": len(table_bboxes),
                        "image_count": len(page.images),
                        "sections_on_page": sections_on_page,
                        "subsections_on_page": subsections_on_page,
                        "extraction_library": "pdfplumber",
                    },
                }
            )

    if save_output:
        target = Path(output_path) if output_path is not None else DEFAULT_TEXT_OUTPUT
        save_extracted_text(extracted_pages, target)

    return extracted_pages


def save_extracted_text(
    pages: list[dict[str, Any]],
    output_path: str | Path = DEFAULT_TEXT_OUTPUT,
) -> Path:
    """Menyimpan hasil ekstraksi teks per halaman ke file JSON."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        json.dump(pages, file, ensure_ascii=False, indent=2)
    return target


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ekstraksi teks per halaman PDF Kurikulum 2024 TIF UB dengan pdfplumber."
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
        default=DEFAULT_TEXT_OUTPUT,
        help="Path file JSON keluaran (default: data/extracted/text_pages.json).",
    )
    parser.add_argument(
        "--include-tables",
        action="store_true",
        help="Sertakan teks di dalam area tabel ke field `text` (tidak mengecualikan bbox tabel).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    pages = extract_text_pages(
        pdf_path=args.pdf,
        exclude_tables=not args.include_tables,
        save_output=True,
        output_path=args.output,
    )
    non_empty = sum(1 for p in pages if p["text"])
    excluded_pages = sum(1 for p in pages if p["has_tables_excluded"])
    print(f"Ekstraksi teks selesai: {len(pages)} halaman diproses.")
    print(f"- Halaman dengan teks naratif non-kosong : {non_empty}")
    print(f"- Halaman dengan area tabel dikecualikan : {excluded_pages}")
    print(f"- Output disimpan di                     : {args.output}")


if __name__ == "__main__":
    main()
