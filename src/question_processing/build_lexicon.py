"""Script pembangun gazetteer mata kuliah secara read-only dari PDF Kurikulum 2024."""

import json
import re
from pathlib import Path
from typing import Any

import pdfplumber
import pymupdf

from config.settings import DATA_DIR, DEFAULT_RAW_PDF

COURSE_CODE_RE = re.compile(r"\b([A-Z]{3}\d{5}(?:-\d)?)\b")

# Alias umum yang dikurasi manual dari PDF & istilah mahasiswa TIF UB
CURATED_ALIASES: dict[str, list[str]] = {
    "COM60016": ["pengantar keilmuan komputer", "pkk"],
    "COM60014": ["pemrograman dasar", "pemdas", "progdass"],
    "COM60011": ["arsitektur dan organisasi komputer", "aok", "arkom"],
    "COM60025": ["kalkulus"],
    "COM60015": ["matematika diskrit", "matematika diskret", "matdis"],
    "COM60024": ["pemrograman lanjut", "pemlan"],
    "COM60004": ["algoritma dan struktur data", "asd"],
    "COM60051": ["metodologi penelitian dan penulisan ilmiah", "metpen", "mppi"],
    "COM60052": ["etika profesi", "etprof"],
    "COM60061": ["capstone project", "capstone"],
    "CIF61101": ["rekayasa perangkat lunak", "rpl"],
    "CIF61302": ["statistika dan teori peluang", "statpel"],
    "CIF62203": ["sistem operasi", "sisop", "so"],
    "CIF62104": ["basis data", "basdat"],
    "CIF62305": ["aljabar linear", "aljabar linier", "aljin"],
    "CIF63106": ["aps", "adpl"],
    "CIF63207": ["jaringan komputer", "jarkom"],
    "CIF63108": ["imk"],
    "CIF63309": ["metode numerik", "metnum"],
    "CIF63110": ["kecerdasan buatan", "ka", "ai"],
    "CIF64311": ["ka lanjut", "ai lanjut", "kal"],
    "CIF64112": ["desain dan analisis algoritma", "daa"],
    "CIF64213": ["keamanan informasi", "kamin"],
    "CIF64114": ["pengembangan aplikasi web", "paw", "pemrograman web"],
    "CIF65115": ["pemrograman aplikasi perangkat bergerak", "papb"],
    "CIF65116": ["komputer grafis", "komgraf"],
    "CIF65217": ["jaringan nirkabel", "jarnik"],
    "CIF65318": ["jaringan saraf tiruan", "jst", "jaringan syaraf tiruan"],
    "CIF65319": ["statistika inferensi", "statinf"],
    "CIF61339": ["pengolahan citra digital dan visi komputer", "pcd", "computer vision"],
    "CIF62340": ["pemerolehan informasi dan penambangan teks", "pipt", "ir"],
    "CIF61341": ["pemrosesan bahasa alami", "pba", "nlp"],
    "CIF62342": ["algoritma evolusi dan kecerdasan berkoloni", "algoritma evolusi"],
    "CIF62343": ["sistem berbasis pengetahuan", "sbp", "knowledge based system"],
    "CIF62344": ["analitik big data", "abd", "big data"],
    "CIF62345": ["rekayasa data dan visualisasi", "rdv", "data engineering"],
    "CIF61346": ["deep learning", "dl"],
    "CIF61347": ["penerapan kecerdasan artifisial", "penerapan ka", "penerapan ai"],
    "CIF60048": ["mlops", "machine learning operations"],
    "CIF62120": ["penjaminan kualitas perangkat lunak", "pkpl", "sqa"],
    "CIF61121": ["pola perancangan", "design pattern"],
    "CIF62122": ["enterprise application integration", "eai"],
    "CIF62123": ["perancangan pengalaman pengguna", "ux design", "ui ux"],
    "CIF61124": ["arsitektur berbasis layanan", "soa"],
    "CIF61125": ["pemrograman gim", "pemrograman game"],
    "CIF61126": ["realitas terkembang", "ar vr", "extended reality"],
    "CIF62127": ["pemrograman sistem interaktif", "psi"],
    "CIF62128": ["pengujian perangkat lunak", "ppl", "software testing"],
    "CIF62229": ["sistem komputasi terdistribusi", "skt", "sistem terdistribusi"],
    "CIF61230": ["jaringan komputer lanjut", "jarkom lanjut"],
    "CIF62231": ["penyediaan dan automasi layanan", "automasi layanan"],
    "CIF62232": ["arsitektur jaringan modern", "ajm"],
    "CIF61233": ["administrasi sistem server", "admin server"],
    "CIF62234": ["jaringan sensor nirkabel", "jsn", "wsn"],
    "CIF61235": ["forensik digital", "digital forensics"],
    "CIF61236": ["keamanan jaringan", "kamjar"],
    "CIF62237": ["keamanan aplikasi berbasis web", "keamanan web"],
    "CIF60038": ["devsecops"],
    "UBU60001": ["tugas akhir", "skripsi", "ta"],
    "UBU60002": ["praktik kerja lapangan", "pkl"],
    "UBU60003": ["kewirausahaan", "kwu"],
    "UBU60004": ["bahasa inggris", "bing"],
    "UBU60005": ["pengabdian kepada masyarakat", "pkm"],
    "MPK60007": ["bahasa indonesia", "bindo"],
    "MPK60001": ["agama islam"],
    "MPK60002": ["agama katholik", "agama katolik"],
    "MPK60003": ["agama kristen", "agama protestan"],
    "MPK60004": ["agama hindu"],
    "MPK60005": ["agama budha", "agama buddha"],
    "MPK60006": ["kewarganegaraan", "pkn"],
    "MPK60008": ["pancasila"],
    "MPK60001-5": ["agama"],
}

# Inkonsistensi kode antar bab di PDF (kode duplikat -> kode kanonik)
KNOWN_DUPLICATE_CODE_ALIASES: dict[str, str] = {
    "CIF60050": "CIF60048",  # MLOps: Tabel 7.3/9.7 CIF60048, Silabus hal. 99-100 CIF60050
    "CIF63107": "CIF63106",  # APS: Tabel 6.4/Sem 3 CIF63106, Sem 5/Silabus CIF63107
    "CIF63109": "CIF63108",  # IMK: Tabel 6.4/Sem 3 CIF63108, Sem 5/Silabus CIF63109
    "CIF63310": "CIF63110",  # Kecerdasan Artifisial: Tabel 6.4/Sem 3 CIF63110, Silabus hal. 66-67 CIF63310
    "UBU60007": "MPK60007",  # Bahasa Indonesia: Sem 5/Tabel 9.11/Silabus MPK60007, Tabel 6.1 UBU60007
}

# Pengecualian kode bertabrakan di Tabel 6.2 (MPK60003 dipakai untuk Agama Kristen di silabus)
TABLE_PAGE18_OVERRIDES: dict[str, str] = {
    "MPK60003": "UBU60003",  # Kewirausahaan kanonik ada di Sem 4 & Silabus hal. 69
}


def _clean_cell(val: str | None) -> str:
    if not val:
        return ""
    return re.sub(r"\s+", " ", val.replace("-\n", "-").replace("\n", " ")).strip()


def _extract_code(text: str) -> str | None:
    cleaned = text.replace("- ", "-")
    m = COURSE_CODE_RE.search(cleaned)
    return m.group(1) if m else None


def _add_course_2024(
    courses: dict[str, dict[str, Any]],
    code: str,
    name: str,
    page: int,
    sks: int | None = None,
) -> None:
    if not code or not name or code in KNOWN_DUPLICATE_CODE_ALIASES:
        return
    clean_name = re.sub(r"\s+", " ", name).strip(" .")
    if not clean_name or clean_name.lower() in {"kode mk", "nama mk", "nama mata kuliah", "mk pilihan"}:
        return
    entry = courses.setdefault(
        code,
        {"name": clean_name, "sks": sks, "alt_codes": [], "aliases": [], "sources": []},
    )
    if page not in entry["sources"]:
        entry["sources"].append(page)
    if entry["sks"] is None and sks is not None:
        entry["sks"] = sks


def extract_courses_from_pdf(pdf_path: Path = DEFAULT_RAW_PDF) -> dict[str, Any]:
    """Mengekstrak daftar mata kuliah 2024, mata kuliah 2020, dan alias kode dari PDF."""
    courses_2024: dict[str, dict[str, Any]] = {}
    courses_2020: dict[str, dict[str, Any]] = {}

    with pdfplumber.open(pdf_path) as pdf:
        # 1. Sumber primer Kurikulum 2024: Tabel 6.1-6.4, Semester 1-8, & Tabel 7.1-7.3 (hal. 18-24)
        for page_num in range(18, 25):
            for table in pdf.pages[page_num - 1].extract_tables():
                for row in table:
                    cells = [_clean_cell(c) for c in row if c is not None]
                    if len(cells) < 3:
                        continue
                    # Cari kolom kode MK pertama di baris (bukan kolom prasyarat di akhir)
                    code = _extract_code(cells[1]) if len(cells) > 1 else None
                    if code and len(cells) >= 4:
                        if page_num == 18 and code in TABLE_PAGE18_OVERRIDES:
                            code = TABLE_PAGE18_OVERRIDES[code]
                        code = KNOWN_DUPLICATE_CODE_ALIASES.get(code, code)
                        name = cells[2]
                        sks_val = int(cells[3]) if cells[3].isdigit() else None
                        _add_course_2024(courses_2024, code, name, page_num, sks_val)

        # 2. Tabel Penyetaraan Kurikulum 2020 vs 2024 (hal. 40-43)
        for page_num in range(40, 44):
            for table in pdf.pages[page_num - 1].extract_tables():
                for row in table:
                    cells = [_clean_cell(c) for c in row]
                    if len(cells) < 6:
                        continue
                    old_code = _extract_code(cells[0])
                    old_name = cells[1]
                    new_code = _extract_code(cells[3])
                    new_name = cells[4]
                    new_sks = int(cells[5]) if cells[5].isdigit() else None
                    if new_code and new_name and new_name.lower() not in {"nama mata kuliah", "nama mk"}:
                        canonical_new = KNOWN_DUPLICATE_CODE_ALIASES.get(new_code, new_code)
                        _add_course_2024(courses_2024, canonical_new, new_name, page_num, new_sks)
                    if old_code and old_name and old_name.lower() not in {"nama mata kuliah", "nama mk"}:
                        canon_eq = KNOWN_DUPLICATE_CODE_ALIASES.get(new_code or "", new_code)
                        eq_name = (
                            courses_2024[canon_eq]["name"]
                            if canon_eq and canon_eq in courses_2024
                            else new_name
                        )
                        courses_2020[old_code] = {
                            "name": old_name,
                            "equivalent_2024_code": canon_eq,
                            "equivalent_2024_name": eq_name or None,
                            "sources": [page_num],
                        }

    # 3. Lengkapi dari header silabus Bab 11 (hal. 50-100), mis. MPK60001-5 (Agama per keyakinan)
    doc = pymupdf.open(pdf_path)
    for page_num in range(50, len(doc) + 1):
        txt = doc[page_num - 1].get_text()
        for m in re.finditer(
            r"Kode MK:\s*\n?\s*([A-Z]{3}\d{5}(?:-\d)?)\s*\n?\s*Nama MK:\s*\n?\s*([^\n]+)(?:\s*\n\s*SKS\s*\n\s*(\d+))?",
            txt,
        ):
            code = m.group(1).strip()
            name = re.sub(r"\s+", " ", m.group(2)).strip()
            sks_val = int(m.group(3)) if m.group(3) else None
            canon = KNOWN_DUPLICATE_CODE_ALIASES.get(code, code)
            if canon != code and canon in courses_2024:
                if code not in courses_2024[canon]["alt_codes"]:
                    courses_2024[canon]["alt_codes"].append(code)
            else:
                _add_course_2024(courses_2024, code, name, page_num, sks_val)

    # 4. Gabungkan alias kurasi & link alt_codes
    for dup_code, canon_code in KNOWN_DUPLICATE_CODE_ALIASES.items():
        if canon_code in courses_2024 and dup_code not in courses_2024[canon_code]["alt_codes"]:
            courses_2024[canon_code]["alt_codes"].append(dup_code)

    for code, entry in courses_2024.items():
        curated = CURATED_ALIASES.get(code, [])
        merged = sorted({a.lower() for a in [*entry["aliases"], *curated] if a.lower() != entry["name"].lower()})
        entry["aliases"] = merged

    return {
        "courses_2024": dict(sorted(courses_2024.items())),
        "courses_2020": dict(sorted(courses_2020.items())),
        "code_aliases": dict(sorted(KNOWN_DUPLICATE_CODE_ALIASES.items())),
    }


def main() -> None:
    """Menjalankan ekstraksi leksikon mata kuliah dan menyimpannya ke JSON."""
    out_path = DATA_DIR / "question_processing" / "lexicon" / "course_lexicon.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lexicon = extract_courses_from_pdf(DEFAULT_RAW_PDF)
    out_path.write_text(json.dumps(lexicon, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Saved {len(lexicon['courses_2024'])} courses_2024, "
        f"{len(lexicon['courses_2020'])} courses_2020, "
        f"{len(lexicon['code_aliases'])} code_aliases -> {out_path}"
    )


if __name__ == "__main__":
    main()
