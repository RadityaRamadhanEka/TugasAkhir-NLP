"""Script evaluasi sistem menggunakan 20 pertanyaan ground truth (Accuracy & MRR — PBA14 Slide 64)."""

import csv
import json
import re
from pathlib import Path
from typing import Any, Callable, Sequence

from config.settings import (
    DEFAULT_ANSWER_TOP_M,
    DEFAULT_CORPUS_FILE,
    DEFAULT_EVALUATION_FILE,
    DEFAULT_EVAL_RESULTS_FILE,
    DEFAULT_KB_FILE,
)

# Kolom CSV mengikuti header di reports/evaluation_results.csv
CSV_COLUMNS = [
    "id",
    "pertanyaan",
    "speech_act",
    "question_category",
    "answer_type",
    "jawaban_acuan",
    "jawaban_sistem",
    "top_candidates",
    "correct_rank",
    "reciprocal_rank",
    "sumber_pdf_page",
    "sumber_doc_page",
    "status",
    "analisis",
]

# Minimal 80% kata penting di kunci jawaban harus muncul di jawaban sistem
TOKEN_RECALL_THRESHOLD = 0.8

# Kata sambung tidak dihitung saat membandingkan kata
COMPARE_STOPWORDS = {
    "dan", "yang", "di", "ke", "dari", "atau", "serta", "dengan",
    "untuk", "pada", "dalam", "adalah", "ini", "itu", "sks",
}

NUMBER_WORDS = {
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10,
}

# Kode MK seperti CIF63110 atau MPK60001 (sudah dalam huruf kecil)
COURSE_CODE_PATTERN = re.compile(r"\b[a-z]{3}\d{5}\b")


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


# ---------------------------------------------------------------------------
# Pencocokan jawaban sistem dengan kunci jawaban
# ---------------------------------------------------------------------------

def normalize_answer(text: str) -> str:
    """Huruf kecil, buang tanda baca, rapikan spasi. Kode MK dan angka tetap utuh."""
    text = str(text or "").lower().replace("&amp;", "&")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_numbers(text: str) -> list[int]:
    """Ambil angka dari teks. Angka di dalam kode MK diabaikan, angka tertulis ikut dihitung."""
    norm = COURSE_CODE_PATTERN.sub(" ", normalize_answer(text))
    numbers = [int(n) for n in re.findall(r"\b\d+\b", norm)]
    numbers += [NUMBER_WORDS[w] for w in norm.split() if w in NUMBER_WORDS]
    return numbers


def content_tokens(text: str) -> set[str]:
    return {tok for tok in normalize_answer(text).split() if tok not in COMPARE_STOPWORDS}


def token_recall(reference: str, candidate: str) -> float:
    """Berapa persen kata penting di kunci jawaban yang juga ada di jawaban sistem."""
    ref_tokens = content_tokens(reference)
    if not ref_tokens:
        return 0.0
    return len(ref_tokens & content_tokens(candidate)) / len(ref_tokens)


def is_answer_correct(candidate: str, question: dict[str, Any]) -> tuple[bool, str]:
    """Menentukan apakah satu jawaban sistem benar menurut kunci soal.

    Urutan cek: kosong -> jawaban terlarang -> angka (khusus NUMERIC)
    -> sama persis -> memuat kunci -> kemiripan kata.
    Mengembalikan (benar/salah, alasan singkat) supaya hasilnya bisa dijelaskan di Bab V.
    """
    cand_norm = normalize_answer(candidate)
    if not cand_norm:
        return False, "jawaban kosong"

    for wrong in question.get("unacceptable_answers", []):
        if normalize_answer(wrong) in cand_norm:
            return False, f"menyebut jawaban yang salah ({wrong})"

    references = [question.get("ground_truth", "")] + list(question.get("acceptable_variants", []))
    references = [ref for ref in references if normalize_answer(ref)]

    # Soal angka: angka yang disebut sistem harus sama dengan angka di kunci.
    # Kunci berupa kode MK (NUMERIC:code, mis. CIF62104) tidak punya angka biasa,
    # jadi soal seperti itu dicek dengan aturan teks di bawah.
    gold_numbers = set(extract_numbers(question.get("ground_truth", "")))
    if question.get("expected_answer_type_coarse") == "NUMERIC" and gold_numbers:
        cand_numbers = set(extract_numbers(candidate))
        if cand_numbers == gold_numbers:
            return True, f"angka sesuai ({', '.join(map(str, sorted(gold_numbers)))})"
        return False, f"angka tidak sesuai (sistem: {sorted(cand_numbers) or '-'})"

    for ref in references:
        if cand_norm == normalize_answer(ref):
            return True, "sama persis dengan kunci/variasi"

    for ref in references:
        if normalize_answer(ref) in cand_norm:
            return True, "jawaban memuat kunci/variasi"

    best = max((token_recall(ref, candidate) for ref in references), default=0.0)
    if best >= TOKEN_RECALL_THRESHOLD:
        return True, f"{best:.0%} kata penting kunci ada di jawaban"
    return False, f"hanya {best:.0%} kata penting kunci yang muncul"


def find_correct_rank(
    answer_output: dict[str, Any],
    question: dict[str, Any],
    top_m: int = DEFAULT_ANSWER_TOP_M,
) -> tuple[int | None, str]:
    """Mencari peringkat kandidat benar pertama di top-M. None jika tidak ada yang benar."""
    if answer_output.get("status") == "not_found":
        return None, "sistem menyatakan jawaban tidak ditemukan"

    candidates = [c.get("answer", "") for c in answer_output.get("top_candidates", [])[:top_m]]
    if not candidates and answer_output.get("answer"):
        candidates = [answer_output["answer"]]

    last_reason = "tidak ada kandidat jawaban"
    for rank, text in enumerate(candidates, start=1):
        correct, reason = is_answer_correct(text, question)
        if correct:
            return rank, reason
        if rank == 1:
            last_reason = reason
    return None, last_reason


def check_source(answer_output: dict[str, Any], question: dict[str, Any]) -> str:
    """Catatan apakah halaman sumber jawaban sistem sama dengan halaman di kunci."""
    source = answer_output.get("source") or {}
    page = source.get("pdf_page", source.get("page"))
    if page is None:
        return "sumber tidak dicantumkan"

    valid_pages = {question.get("source_pdf_page")}
    valid_pages |= {s.get("pdf_page") for s in question.get("other_valid_sources", [])}
    if page in valid_pages:
        return f"sumber sesuai (hal. PDF {page})"
    return f"sumber berbeda (sistem hal. PDF {page})"


# ---------------------------------------------------------------------------
# Menjalankan evaluasi
# ---------------------------------------------------------------------------

def load_questions(questions_path: Path = DEFAULT_EVALUATION_FILE) -> list[dict[str, Any]]:
    """Baca soal evaluasi.

    Kalau questions.json ada, file itu yang dipakai. Kalau belum ada, semua file
    eval_q*.json milik tiap anggota di folder yang sama digabung lalu diurutkan per ID.
    """
    questions_path = Path(questions_path)
    if questions_path.exists():
        with open(questions_path, encoding="utf-8") as f:
            return json.load(f)

    member_files = sorted(questions_path.parent.glob("eval_q*.json"))
    if not member_files:
        raise FileNotFoundError(f"Tidak ada file soal di {questions_path.parent}")

    questions: list[dict[str, Any]] = []
    for path in member_files:
        with open(path, encoding="utf-8") as f:
            questions.extend(json.load(f))
    return sorted(questions, key=lambda q: q.get("id", ""))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_default_answer_fn() -> Callable[[str], dict[str, Any]]:
    """Menyiapkan pipeline asli: baca korpus Anggota 2, bangun indeks Anggota 4, lalu jawab."""
    from src.pipeline.qa_pipeline import answer_question
    from src.retrieval.index_builder import build_index

    if not DEFAULT_CORPUS_FILE.exists():
        raise FileNotFoundError(
            f"Korpus belum ada di {DEFAULT_CORPUS_FILE}. Modul preprocessing perlu dijalankan dulu."
        )
    passages = _load_jsonl(DEFAULT_CORPUS_FILE)
    triples = _load_jsonl(DEFAULT_KB_FILE) if DEFAULT_KB_FILE.exists() else None
    index = build_index(passages, triples=triples)
    return lambda question: answer_question(question, index=index)


def evaluate_question(
    question: dict[str, Any],
    answer_fn: Callable[[str], dict[str, Any]],
    top_m: int = DEFAULT_ANSWER_TOP_M,
) -> dict[str, Any]:
    """Menjalankan satu soal ke sistem lalu mengubah hasilnya menjadi satu baris CSV."""
    try:
        output = answer_fn(question["question"])
        error_note = ""
    except Exception as exc:  # modul lain belum jadi tetap dicatat, evaluasi tidak berhenti
        output = {"answer": "", "status": "not_found", "top_candidates": []}
        error_note = f"error saat menjawab: {type(exc).__name__}: {exc}"

    rank, reason = find_correct_rank(output, question, top_m=top_m)
    source = output.get("source") or {}
    candidates = output.get("top_candidates", [])[:top_m]

    notes = [error_note] if error_note else []
    notes.append(reason)
    if output.get("status") != "not_found":
        notes.append(check_source(output, question))

    return {
        "id": question.get("id", ""),
        "pertanyaan": question.get("question", ""),
        "speech_act": question.get("speech_act", ""),
        "question_category": question.get("question_category", ""),
        "answer_type": question.get("expected_answer_type", ""),
        "jawaban_acuan": question.get("ground_truth", ""),
        "jawaban_sistem": output.get("answer", ""),
        "top_candidates": " | ".join(
            f"{i}) {c.get('answer', '')}" for i, c in enumerate(candidates, start=1)
        ),
        "correct_rank": rank if rank is not None else "",
        "reciprocal_rank": round(1.0 / rank, 4) if rank else 0.0,
        "sumber_pdf_page": source.get("pdf_page", source.get("page", "")),
        "sumber_doc_page": source.get("doc_page", ""),
        "status": "Benar" if rank == 1 else "Salah",
        "analisis": "; ".join(notes),
    }


def run_evaluation(
    questions_path: Path = DEFAULT_EVALUATION_FILE,
    output_csv_path: Path = DEFAULT_EVAL_RESULTS_FILE,
    answer_fn: Callable[[str], dict[str, Any]] | None = None,
    top_m: int = DEFAULT_ANSWER_TOP_M,
) -> dict[str, float]:
    """Menjalankan evaluasi seluruh pertanyaan acuan, menyimpan rekap ke CSV, dan mengembalikan metrik.

    `answer_fn` bisa diisi fungsi tiruan untuk uji coba sebelum semua modul selesai.
    Kalau dibiarkan kosong, dipakai pipeline asli.

    Returns:
        Dict ringkasan metrik (minimal `accuracy` dan `mrr`, opsional `retrieval_recall_at_k`).
    """
    questions = load_questions(questions_path)
    if answer_fn is None:
        answer_fn = build_default_answer_fn()

    rows = [evaluate_question(q, answer_fn, top_m=top_m) for q in questions]

    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    ranks = [row["correct_rank"] or None for row in rows]
    flags = [row["status"] == "Benar" for row in rows]
    n_correct = sum(flags)
    return {
        "n_questions": len(rows),
        "n_correct": n_correct,
        "n_wrong": len(rows) - n_correct,
        "accuracy": compute_accuracy(flags),
        "mrr": compute_mrr(ranks),
    }


if __name__ == "__main__":
    summary = run_evaluation()
    print(f"Jumlah soal : {summary['n_questions']}")
    print(f"Benar/Salah : {summary['n_correct']}/{summary['n_wrong']}")
    print(f"Accuracy    : {summary['accuracy']:.2%}")
    print(f"MRR         : {summary['mrr']:.4f}")
