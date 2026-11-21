"""Inventarisasi gambar/diagram/grafik dan ekstraksi transkripsi terstruktur.

Modul ini merupakan bagian dari tugas Anggota 1 (`src/document_ingestion/`) untuk:
1. Mengekspor seluruh gambar/diagram tertanam dari PDF secara otomatis via `pymupdf`.
2. Memasangkan setiap gambar dengan metadata sumber (`pdf_page`, `doc_page`, `section`,
   `caption`, serta dimensi gambar).
3. Menyediakan representasi teks & `structured_records` terverifikasi untuk 11 diagram
   prioritas tinggi **Gambar 7.1–7.11** (Mata Kuliah Pilihan *Learning Path*), yang
   informasinya hanya tersedia dalam bentuk visual (sesuai Batasan #6 Brief).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pymupdf

from config.settings import BASE_DIR, DEFAULT_RAW_PDF, EXTRACTED_DATA_DIR
from src.document_ingestion.extract_text import (
    FOOTER_HEIGHT_PT,
    _normalize_whitespace,
    _update_section_state,
)

DEFAULT_VISUALS_DIR = EXTRACTED_DATA_DIR / "visuals"
DEFAULT_VISUALS_OUTPUT = EXTRACTED_DATA_DIR / "visuals.json"

# Transkripsi terstruktur terverifikasi untuk 11 diagram Learning Path (Gambar 7.1-7.11).
# Seluruh nama MK dan angka SKS dicatat persis sesuai isi diagram PNG di PDF asli;
# perbedaan angka SKS terhadap Tabel 7.1-7.3 dicatat di field `notes`.
LEARNING_PATH_TRANSCRIPTIONS: dict[str, dict[str, Any]] = {
    "Gambar 7.1": {
        "learning_path": "Frontend Developer",
        "prerequisite_root": "MK wajib",
        "courses": [
            {
                "learning_path": "Frontend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Perancangan Pengalaman Pengguna",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Frontend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Pengujian Perangkat Lunak",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Frontend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Pemrograman Sistem Interaktif",
                "sks": 4,
                "notes": None,
            },
            {
                "learning_path": "Frontend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Arsitektur berbasis layanan",
                "sks": 4,
                "notes": None,
            },
        ],
    },
    "Gambar 7.2": {
        "learning_path": "Backend Developer",
        "prerequisite_root": "MK wajib",
        "courses": [
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Penjaminan Kualitas PL",
                "sks": 4,
                "notes": "Pada Tabel 7.1 (hal. PDF 23) tertulis Penjaminan Kualitas Perangkat Lunak 3 SKS.",
            },
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Pengujian Perangkat Lunak",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Arsitektur berbasis layanan",
                "sks": 4,
                "notes": None,
            },
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Capstone",
                "sks": 3,
                "notes": "Merujuk pada Capstone Project (COM60061, 3 SKS).",
            },
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Keamanan aplikasi berbasis web",
                "sks": 4,
                "notes": None,
            },
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Administrasi sistem server",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Penyediaan dan otomasi layanan",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Backend Developer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "DevSecOps",
                "sks": 4,
                "notes": None,
            },
        ],
    },
    "Gambar 7.3": {
        "learning_path": "Game Developer",
        "prerequisite_root": "MK wajib",
        "courses": [
            {
                "learning_path": "Game Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Pengujian Perangkat Lunak",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Game Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Perancangan Pengalaman Pengguna",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Game Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Arsitektur berbasis layanan",
                "sks": 4,
                "notes": None,
            },
            {
                "learning_path": "Game Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Pemrograman Gim",
                "sks": 4,
                "notes": None,
            },
            {
                "learning_path": "Game Developer",
                "group": "Perekayasa Perangkat Lunak",
                "course_name": "Realitas terkembang",
                "sks": 3,
                "notes": None,
            },
        ],
    },
    "Gambar 7.4": {
        "learning_path": "Cloud Engineer",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "Cloud Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Administrasi sistem server",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Cloud Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Penyediaan dan otomasi layanan",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Cloud Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "DevSecOps",
                "sks": 4,
                "notes": None,
            },
        ],
    },
    "Gambar 7.5": {
        "learning_path": "Security Engineer",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "Security Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Keamanan jaringan",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Security Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Keamanan aplikasi berbasis web",
                "sks": 3,
                "notes": "Pada Tabel 7.2 (hal. PDF 23) & Gambar 7.2 tertulis 4 SKS.",
            },
            {
                "learning_path": "Security Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Forensik digital",
                "sks": 3,
                "notes": None,
            },
        ],
    },
    "Gambar 7.6": {
        "learning_path": "Network Engineer",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "Network Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Jaringan komputer lanjut",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Network Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Jaringan sensor nirkabel",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Network Engineer",
                "group": "Perekayasa Infrastruktur Komputasi",
                "course_name": "Arsitektur jaringan modern",
                "sks": 3,
                "notes": None,
            },
        ],
    },
    "Gambar 7.7": {
        "learning_path": "AI/ML Engineer",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "AI/ML Engineer",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Deep Learning",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "AI/ML Engineer",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Big Data Analytics",
                "sks": 3,
                "notes": "Pada Tabel 7.3 tertulis Analitik Big Data (CIF62344).",
            },
            {
                "learning_path": "AI/ML Engineer",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "MLOps",
                "sks": 4,
                "notes": "Pada Tabel 7.3 tertulis Machine Learning Operations (MLOps).",
            },
        ],
    },
    "Gambar 7.8": {
        "learning_path": "Computer Vision Engineer",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "Computer Vision Engineer",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Deep Learning",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "Computer Vision Engineer",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Pengolahan Citra dan Visi Komputer Digital",
                "sks": 4,
                "notes": "Pada Tabel 7.3 tertulis Pengolahan Citra Digital (CIF61339).",
            },
        ],
    },
    "Gambar 7.9": {
        "learning_path": "Data Scientist",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "Data Scientist",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Big Data Analytics",
                "sks": 3,
                "notes": "Pada Tabel 7.3 tertulis Analitik Big Data (CIF62344).",
            },
            {
                "learning_path": "Data Scientist",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Rekayasa Data dan Visualisasi",
                "sks": 4,
                "notes": "Pada Tabel 7.3 (hal. PDF 24) tertulis 3 SKS.",
            },
        ],
    },
    "Gambar 7.10": {
        "learning_path": "NLP Engineer",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "NLP Engineer",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Pemrosesan Bahasa Alami",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "NLP Engineer",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Pemerolehan Informasi dan Penambangan Teks",
                "sks": 4,
                "notes": None,
            },
        ],
    },
    "Gambar 7.11": {
        "learning_path": "AI Research Scientist",
        "prerequisite_root": "MK Wajib",
        "courses": [
            {
                "learning_path": "AI Research Scientist",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Algoritma Evolusi dan Kecerdasan Berkoloni",
                "sks": 3,
                "notes": None,
            },
            {
                "learning_path": "AI Research Scientist",
                "group": "Perekayasa Komputasi Cerdas",
                "course_name": "Sistem Berbasis Pengetahuan",
                "sks": 3,
                "notes": "Pada Tabel 7.3 (hal. PDF 24) tertulis 4 SKS.",
            },
        ],
    },
}

NON_LP_VISUAL_METADATA: dict[str, dict[str, Any]] = {
    "Gambar 3.1": {
        "relevant_for_qa": False,
        "priority": "low",
        "summary": (
            "Diagram alur pembentukan CPL Program Studi Sarjana Teknik Informatika "
            "(penjelasan rinci proses perumusan CPL sudah tersedia pada teks naratif Bab 3)."
        ),
    },
    "Gambar 5.1": {
        "relevant_for_qa": False,
        "priority": "low",
        "summary": (
            "Diagram skema pemetaan tidak langsung dari Bahan Kajian ke Sub Bahan Kajian, "
            "CPMK, hingga Mata Kuliah (penjelasan rinci sudah tersedia pada teks Bab 5)."
        ),
    },
    "Gambar 8.1": {
        "relevant_for_qa": True,
        "priority": "medium",
        "summary": (
            "Diagram alir mata kuliah untuk skema Perkuliahan Reguler (semester 1 hingga 8 "
            "beserta panah keterkaitan prasyarat antar mata kuliah)."
        ),
    },
    "Gambar 8.2": {
        "relevant_for_qa": True,
        "priority": "medium",
        "summary": (
            "Diagram alir mata kuliah untuk skema Perkuliahan Reguler dan MBKM 1 Semester "
            "di luar kampus pada semester 6 (konversi 10 hingga 20 SKS)."
        ),
    },
    "Gambar 8.3": {
        "relevant_for_qa": True,
        "priority": "medium",
        "summary": (
            "Diagram alir mata kuliah untuk skema Perkuliahan Reguler dan MBKM 2 Semester "
            "di luar kampus pada semester 7 dan 8."
        ),
    },
}


def _to_repo_relative_posix(path: Path) -> str:
    """Mengubah path file menjadi path relatif berformat POSIX agar portabel antar-anggota."""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _extract_doc_page_fitz(page: pymupdf.Page, pdf_page: int) -> str:
    """Mengambil `doc_page` dari zona footer menggunakan PyMuPDF."""
    if pdf_page == 1:
        return ""
    h = float(page.rect.height)
    w = float(page.rect.width)
    footer_rect = pymupdf.Rect(0.0, max(0.0, h - FOOTER_HEIGHT_PT), w, h)
    footer_txt = re.sub(r"\s+", "", page.get_text("text", clip=footer_rect) or "")
    if re.fullmatch(r"([ivxlcdm]+|\d+)", footer_txt, flags=re.IGNORECASE):
        return footer_txt
    return ""


def _build_learning_path_text(fig_num: str, lp_data: dict[str, Any]) -> str:
    """Menyusun deskripsi tekstual yang kaya kata kunci untuk indeks BM25/TF-IDF."""
    lp_name = lp_data["learning_path"]
    prereq_root = lp_data["prerequisite_root"]
    course_parts = [f"{c['course_name']} ({c['sks']} SKS)" for c in lp_data["courses"]]
    groups = sorted({c["group"] for c in lp_data["courses"]})
    return (
        f"{fig_num} - Mata Kuliah Pilihan Learning Path {lp_name}. "
        f"Kelompok kompetensi: {', '.join(groups)}. "
        f"Setelah menempuh {prereq_root}, mahasiswa pada Learning Path {lp_name} "
        f"direkomendasikan mengambil mata kuliah pilihan: {', '.join(course_parts)}."
    )


def extract_visuals(
    pdf_path: str | Path = DEFAULT_RAW_PDF,
    *,
    export_images: bool = True,
    visuals_dir: str | Path | None = None,
    include_cover: bool = False,
    save_output: bool = False,
    output_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Menginventarisasi konten visual dan menyertakan transkripsi terstruktur (prioritas Gambar 7.1-7.11).

    Args:
        pdf_path: Path menuju file PDF korpus.
        export_images: Jika True, gambar tertanam diekspor ke `visuals_dir`.
        visuals_dir: Direktori tujuan file gambar PNG (default: `data/extracted/visuals/`).
        include_cover: Jika True, halaman sampul (hal. 1) ikut dicatat di daftar visual.
        save_output: Jika True, hasil inventarisasi langsung disimpan ke JSON.
        output_path: Path file JSON keluaran (default: `data/extracted/visuals.json`).

    Returns:
        List dict berisi `visual_id`, `figure_number`, `pdf_page`, `doc_page`, `section`,
        `caption`, `relevant_for_qa`, `priority`, `image_path`, `text`, `structured_records`,
        dan `content_type="visual"`.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File PDF tidak ditemukan: {path}")

    out_img_dir = Path(visuals_dir) if visuals_dir is not None else DEFAULT_VISUALS_DIR
    if export_images:
        out_img_dir.mkdir(parents=True, exist_ok=True)

    visuals: list[dict[str, Any]] = []
    current_section = "Sampul"
    current_subsection: str | None = None
    current_chapter = 0

    with pymupdf.open(path) as doc:
        for pdf_page in range(1, len(doc) + 1):
            page = doc[pdf_page - 1]
            w = float(page.rect.width)
            h = float(page.rect.height)
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

            images = page.get_images(full=True)
            if not images:
                continue
            if pdf_page == 1 and not include_cover:
                continue

            captions = [
                ln.strip()
                for ln in raw_body_text.splitlines()
                if re.match(r"^Gambar\s+\d+\.\d+", ln.strip(), flags=re.IGNORECASE)
            ]

            for img_idx, img in enumerate(images, start=1):
                xref = img[0]
                img_info = doc.extract_image(xref)
                ext = img_info.get("ext", "png")
                width_px = int(img_info.get("width", 0))
                height_px = int(img_info.get("height", 0))

                caption = captions[img_idx - 1] if img_idx - 1 < len(captions) else ""
                fig_match = re.match(r"^(Gambar\s+(\d+)\.(\d+))", caption, flags=re.IGNORECASE)

                if pdf_page == 1:
                    figure_number = "Sampul"
                    visual_id = "vis_00_cover"
                    file_name = f"page_001_cover.{ext}"
                    caption = "Halaman Sampul Panduan Kurikulum Program Studi Teknik Informatika 2024"
                elif fig_match:
                    major, minor = int(fig_match.group(2)), int(fig_match.group(3))
                    figure_number = f"Gambar {major}.{minor}"
                    visual_id = f"vis_{major:02d}_{minor:02d}"
                    file_name = f"page_{pdf_page:03d}_gambar_{major}_{minor}.{ext}"
                else:
                    figure_number = f"Visual Hal. {pdf_page}"
                    visual_id = f"vis_p{pdf_page:03d}_{img_idx:02d}"
                    file_name = f"page_{pdf_page:03d}_img_{img_idx}.{ext}"

                saved_image_path: str | None = None
                if export_images:
                    img_target = out_img_dir / file_name
                    img_target.write_bytes(img_info["image"])
                    saved_image_path = _to_repo_relative_posix(img_target)

                # Tentukan isi teks & structured_records berdasarkan inventarisasi
                if figure_number in LEARNING_PATH_TRANSCRIPTIONS:
                    lp_data = LEARNING_PATH_TRANSCRIPTIONS[figure_number]
                    relevant_for_qa = True
                    priority = "high"
                    extraction_method = "structured_transcription"
                    text = _build_learning_path_text(figure_number, lp_data)
                    structured_records = list(lp_data["courses"])
                    verified_manually = True
                    extra_meta = {
                        "learning_path": lp_data["learning_path"],
                        "course_count": len(structured_records),
                        "has_sks_discrepancy_note": any(
                            c.get("notes") and "SKS" in str(c["notes"]) for c in structured_records
                        ),
                    }
                elif figure_number in NON_LP_VISUAL_METADATA:
                    meta_info = NON_LP_VISUAL_METADATA[figure_number]
                    relevant_for_qa = meta_info["relevant_for_qa"]
                    priority = meta_info["priority"]
                    extraction_method = "inventory_summary"
                    text = meta_info["summary"]
                    structured_records = []
                    verified_manually = True
                    extra_meta = {}
                else:
                    relevant_for_qa = False
                    priority = "low"
                    extraction_method = "inventory_only"
                    text = caption or f"Konten visual pada halaman PDF {pdf_page}."
                    structured_records = []
                    verified_manually = False
                    extra_meta = {}

                visuals.append(
                    {
                        "visual_id": visual_id,
                        "figure_number": figure_number,
                        "pdf_page": pdf_page,
                        "doc_page": doc_page,
                        "section": current_section,
                        "caption": caption,
                        "content_type": "visual",
                        "relevant_for_qa": relevant_for_qa,
                        "priority": priority,
                        "image_path": saved_image_path,
                        "image_info": {
                            "width_px": width_px,
                            "height_px": height_px,
                            "format": ext,
                            "size_kb": round(len(img_info["image"]) / 1024.0, 1),
                        },
                        "extraction_method": extraction_method,
                        "ocr_raw_text": None,
                        "text": text,
                        "structured_records": structured_records,
                        "metadata": {
                            "verified_manually": verified_manually,
                            "extraction_library": "pymupdf",
                            **extra_meta,
                        },
                    }
                )

    if save_output:
        target = Path(output_path) if output_path is not None else DEFAULT_VISUALS_OUTPUT
        save_extracted_visuals(visuals, target)

    return visuals


def save_extracted_visuals(
    visuals: list[dict[str, Any]],
    output_path: str | Path = DEFAULT_VISUALS_OUTPUT,
) -> Path:
    """Menyimpan hasil inventarisasi dan transkripsi visual ke file JSON."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        json.dump(visuals, file, ensure_ascii=False, indent=2)
    return target


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventarisasi gambar & transkripsi terstruktur PDF Kurikulum 2024 TIF UB."
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
        default=DEFAULT_VISUALS_OUTPUT,
        help="Path file JSON keluaran (default: data/extracted/visuals.json).",
    )
    parser.add_argument(
        "--visuals-dir",
        type=Path,
        default=DEFAULT_VISUALS_DIR,
        help="Folder penyimpanan gambar PNG hasil ekspor (default: data/extracted/visuals/).",
    )
    parser.add_argument(
        "--no-export-images",
        action="store_true",
        help="Jangan mengekspor file PNG, hanya bangun metadata & transkripsi JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    visuals = extract_visuals(
        pdf_path=args.pdf,
        export_images=not args.no_export_images,
        visuals_dir=args.visuals_dir,
        save_output=True,
        output_path=args.output,
    )
    transcribed = sum(1 for v in visuals if v["extraction_method"] == "structured_transcription")
    total_lp_records = sum(len(v["structured_records"]) for v in visuals)
    print(f"Ekstraksi visual selesai: {len(visuals)} gambar diinventarisasi.")
    print(f"- Visual Learning Path ditranskripsi : {transcribed} ({total_lp_records} record MK)")
    print(f"- Output disimpan di                 : {args.output}")


if __name__ == "__main__":
    main()
