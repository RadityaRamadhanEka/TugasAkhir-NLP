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

# Nama file default yang disepakati tim (sesuai berkas aktual di data/raw/)
DEFAULT_RAW_PDF = RAW_DATA_DIR / "Buku-Pedoman-Pelaksanaan-Kurikulum-2024-TIF-V.1.0.pdf"
DEFAULT_CORPUS_FILE = PROCESSED_DATA_DIR / "passages.jsonl"
DEFAULT_KB_FILE = PROCESSED_DATA_DIR / "knowledge_triples.jsonl"
DEFAULT_EVALUATION_FILE = EVALUATION_DATA_DIR / "questions.json"
DEFAULT_EVAL_RESULTS_FILE = REPORTS_DIR / "evaluation_results.csv"

# Parameter default retrieval, candidate ranking (MRR), & fallback
DEFAULT_TOP_K = 5
DEFAULT_ANSWER_TOP_M = 5
MIN_CONFIDENCE_THRESHOLD = 0.2
