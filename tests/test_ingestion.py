"""Pengujian modul Document Ingestion (Anggota 1)."""

from config.settings import DEFAULT_RAW_PDF
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


def test_default_raw_pdf_exists() -> None:
    assert DEFAULT_RAW_PDF.exists(), f"PDF korpus tidak ditemukan di {DEFAULT_RAW_PDF}"


def test_extract_text_pages_schema_and_metadata(tmp_path) -> None:
    output_file = tmp_path / "text_pages.json"
    pages = extract_text.extract_text_pages(
        DEFAULT_RAW_PDF,
        exclude_tables=True,
        save_output=True,
        output_path=output_file,
    )

    assert len(pages) == 100
    assert output_file.exists()

    required_keys = {"page_id", "pdf_page", "doc_page", "section", "content_type", "text", "paragraphs"}
    for item in pages:
        assert required_keys.issubset(item.keys())
        assert item["content_type"] == "text"

    # Halaman 1 adalah sampul tanpa teks dan tanpa nomor halaman tercetak
    assert pages[0]["doc_page"] == ""
    assert pages[0]["section"] == "Sampul"

    # Halaman 2 (Kata Pengantar) bernomor Romawi "i"
    assert pages[1]["doc_page"] == "i"
    assert pages[1]["section"] == "Kata Pengantar"

    # Kasus khusus: nomor halaman tercetak "6" muncul ganda di pdf_page 13 & 14
    assert pages[12]["doc_page"] == "6"
    assert pages[13]["doc_page"] == "6"
    assert pages[13]["metadata"]["orientation"] == "landscape"
    assert pages[13]["section"].startswith("4.")

    # Halaman Bab 11 (pdf_page 50) terdeteksi benar dan area tabel silabus dikecualikan
    assert pages[49]["section"].startswith("11.")
    assert pages[49]["has_tables_excluded"] is True
    assert "11. SILABUS MATA KULIAH" in pages[49]["text"]


def test_extract_tables_all_types_and_continuations(tmp_path) -> None:
    output_file = tmp_path / "tables.json"
    tables = extract_tables.extract_tables(
        DEFAULT_RAW_PDF,
        save_output=True,
        output_path=output_file,
    )

    assert len(tables) >= 100
    assert output_file.exists()

    required_keys = {
        "table_id",
        "pdf_page",
        "doc_page",
        "section",
        "table_title",
        "table_type",
        "headers",
        "rows",
        "records",
        "content_type",
    }
    for tbl in tables:
        assert required_keys.issubset(tbl.keys())
        assert tbl["content_type"] == "table"

    types_found = {t["table_type"] for t in tables}
    assert {"regular", "cpl_matrix", "semester_schedule", "transition_mapping", "syllabus_card"}.issubset(
        types_found
    )

    # Tabel 3.1 (hal. 12) menyimpan kode CPL utuh tanpa pecah underscore
    p12_tables = [t for t in tables if t["pdf_page"] == 12]
    assert len(p12_tables) == 1
    assert any(r["kode_cpl"] == "IF_CPL_S1" for r in p12_tables[0]["records"])

    # Tabel 3.1 lanjutan di hal. 13 terdeteksi sebagai continuation
    p13_tables = [t for t in tables if t["pdf_page"] == 13]
    assert p13_tables[0]["is_continuation"] is True
    assert p13_tables[0]["continuation_of"] == p12_tables[0]["table_id"]

    # Tabel 4.1 (hal. 14) memiliki tepat 10 kode CPL & tanda centang terpetakan
    p14_matrix = [t for t in tables if t["pdf_page"] == 14 and t["table_type"] == "cpl_matrix"]
    assert len(p14_matrix) == 1
    assert len(p14_matrix[0]["headers"]) == 11  # Bahan Kajian + 10 CPL
    assert "IF_CPL_S1" in p14_matrix[0]["records"][0]["cpl_codes"]

    # Tabel Semester 4 (hal. 21) menangkap Kecerdasan Artifisial Lanjut + prasyaratnya
    p21_sem4 = [t for t in tables if t["pdf_page"] == 21 and t["metadata"].get("semester") == 4]
    assert len(p21_sem4) == 1
    ai_lanjut = [r for r in p21_sem4[0]["records"] if r["kode_mk"] == "CIF64311"]
    assert len(ai_lanjut) == 1
    assert ai_lanjut[0]["prasyarat_kode"] == "CIF63110"
    assert ai_lanjut[0]["prasyarat_nilai"] == "C"
    assert ai_lanjut[0]["praktikum"] is True

    # Kartu Silabus yang terbelah lintas halaman (COM60014 hal. 50 -> 51) terdeteksi continuation
    p51_com14 = [
        t
        for t in tables
        if t["pdf_page"] == 51 and t["metadata"].get("course_code") == "COM60014"
    ]
    assert len(p51_com14) == 1
    assert p51_com14[0]["is_continuation"] is True

    # Tabel 7.4 mempertahankan operator ">60" pada syarat SKS
    p36_tables = [t for t in tables if t["pdf_page"] == 36]
    assert p36_tables[0]["records"][0]["sks"] == ">60"

    # Tabel 10.1 lanjutan di hal. 47-49 terdeteksi continuation dari hal. 46
    p46_tbl = [t for t in tables if t["pdf_page"] == 46][0]
    for cont_page in (47, 48, 49):
        cont_tbl = [t for t in tables if t["pdf_page"] == cont_page][0]
        assert cont_tbl["is_continuation"] is True
        assert cont_tbl["continuation_of"] == p46_tbl["table_id"]
        assert cont_tbl["headers"] == ["No", "Kegiatan", "Penjelasan"]


def test_load_pdf_metadata_and_visuals(tmp_path) -> None:
    meta_file = tmp_path / "document_metadata.json"
    meta = document_loader.load_pdf_metadata(
        DEFAULT_RAW_PDF,
        save_output=True,
        output_path=meta_file,
    )
    assert meta_file.exists()
    assert meta["total_pages"] == 100
    assert meta["landscape_pages"] >= 3
    assert len(meta["page_overview"]) == 100

    vis_file = tmp_path / "visuals.json"
    vis_dir = tmp_path / "visuals"
    visuals = extract_visuals.extract_visuals(
        DEFAULT_RAW_PDF,
        export_images=True,
        visuals_dir=vis_dir,
        save_output=True,
        output_path=vis_file,
    )
    assert vis_file.exists()
    assert len(visuals) == 16  # 16 gambar di Daftar Gambar (tanpa cover)

    lp_visuals = [v for v in visuals if v["extraction_method"] == "structured_transcription"]
    assert len(lp_visuals) == 11  # Gambar 7.1 s.d. 7.11

    nlp_vis = [v for v in lp_visuals if v["figure_number"] == "Gambar 7.10"][0]
    nlp_courses = {r["course_name"] for r in nlp_vis["structured_records"]}
    assert "Pemrosesan Bahasa Alami" in nlp_courses
    assert "Pemerolehan Informasi dan Penambangan Teks" in nlp_courses




