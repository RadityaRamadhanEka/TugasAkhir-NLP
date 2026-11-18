"""Pengaturan path dan parameter global proyek QA Kurikulum 2024 TIF UB.

Seluruh modul wajib mengambil path dari file ini agar tidak ada path lokal
yang hanya bekerja di komputer satu anggota.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
EXTRACTED_DATA_DIR = DATA_DIR / "extracted"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EVALUATION_DATA_DIR = DATA_DIR / "evaluation"

REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"

# Nama file default yang disepakati tim (dapat disesuaikan bersama)
DEFAULT_RAW_PDF = RAW_DATA_DIR / "pedoman_kurikulum_2024_tif.pdf"
DEFAULT_CORPUS_FILE = PROCESSED_DATA_DIR / "passages.jsonl"
DEFAULT_EVALUATION_FILE = EVALUATION_DATA_DIR / "questions.json"
DEFAULT_EVAL_RESULTS_FILE = REPORTS_DIR / "evaluation_results.csv"

# Parameter default retrieval & fallback
DEFAULT_TOP_K = 5
MIN_CONFIDENCE_THRESHOLD = 0.2
