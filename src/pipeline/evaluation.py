"""Script evaluasi sistem menggunakan 20 pertanyaan ground truth."""

from pathlib import Path

from config.settings import DEFAULT_EVALUATION_FILE, DEFAULT_EVAL_RESULTS_FILE


def run_evaluation(
    questions_path: Path = DEFAULT_EVALUATION_FILE,
    output_csv_path: Path = DEFAULT_EVAL_RESULTS_FILE,
) -> None:
    """Menjalankan evaluasi seluruh pertanyaan acuan dan menyimpan rekap ke CSV."""
    raise NotImplementedError("Anggota 5: implementasikan alur evaluasi 20 pertanyaan di sini.")
