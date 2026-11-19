"""Script evaluasi sistem menggunakan 20 pertanyaan ground truth (Accuracy & MRR — PBA14 Slide 64)."""

from pathlib import Path
from typing import Sequence

from config.settings import DEFAULT_EVALUATION_FILE, DEFAULT_EVAL_RESULTS_FILE


def compute_accuracy(is_correct_flags: Sequence[bool]) -> float:
    """Menghitung metrik Accuracy (proporsi jawaban peringkat-1 yang benar)."""
    if not is_correct_flags:
        return 0.0
    return sum(1 for flag in is_correct_flags if flag) / len(is_correct_flags)


def compute_mrr(correct_ranks: Sequence[int | None]) -> float:
    """Menghitung Mean Reciprocal Rank (MRR) sesuai PBA14 Slide 64.

    Args:
        correct_ranks: Daftar peringkat berbasis-1 (1, 2, 3, ...) dari jawaban benar pertama
            pada daftar kandidat top-M untuk tiap pertanyaan, atau `None` / `0` bila tidak ada
            kandidat yang benar.
    """
    if not correct_ranks:
        return 0.0
    reciprocal_sum = sum(
        (1.0 / rank) if (rank is not None and rank > 0) else 0.0
        for rank in correct_ranks
    )
    return reciprocal_sum / len(correct_ranks)


def run_evaluation(
    questions_path: Path = DEFAULT_EVALUATION_FILE,
    output_csv_path: Path = DEFAULT_EVAL_RESULTS_FILE,
) -> dict[str, float]:
    """Menjalankan evaluasi seluruh pertanyaan acuan, menyimpan rekap ke CSV, dan mengembalikan metrik.

    Returns:
        Dict ringkasan metrik (minimal `accuracy` dan `mrr`, opsional `retrieval_recall_at_k`).
    """
    raise NotImplementedError("Anggota 5: implementasikan alur evaluasi 20 pertanyaan (Accuracy + MRR) di sini.")
