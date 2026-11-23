"""Uji pencocokan jawaban & alur evaluasi memakai jawaban tiruan (tanpa menunggu modul lain)."""

import csv

import pytest

from src.pipeline import evaluation

Q_SKS = {
    "id": "Q17",
    "question": "Berapa SKS mata kuliah Kecerdasan Artifisial?",
    "expected_answer_type_coarse": "NUMERIC",
    "ground_truth": "2 SKS",
    "acceptable_variants": ["2", "dua SKS"],
    "source_pdf_page": 20,
    "other_valid_sources": [{"pdf_page": 19}],
}

Q_GANTI = {
    "id": "Q19",
    "question": "Kecerdasan Buatan diganti menjadi mata kuliah apa?",
    "expected_answer_type_coarse": "ENTITY",
    "ground_truth": "Kecerdasan Artifisial (CIF63110), dengan SKS berubah dari 3 SKS menjadi 2 SKS.",
    "acceptable_variants": ["Kecerdasan Artifisial"],
    "unacceptable_answers": ["Kecerdasan Artifisial Lanjut", "Penerapan Kecerdasan Artifisial"],
    "source_pdf_page": 41,
}

Q_LIST = {
    "id": "Q18",
    "question": "MK pilihan learning path NLP Engineer?",
    "expected_answer_type_coarse": "ENTITY",
    "ground_truth": "Pemrosesan Bahasa Alami (3 SKS) dan Pemerolehan Informasi dan Penambangan Teks (4 SKS).",
    # tanpa variasi ini, jawaban yang tidak menyebut SKS cuma 78% mirip dan dianggap salah
    "acceptable_variants": ["Pemrosesan Bahasa Alami dan Pemerolehan Informasi dan Penambangan Teks"],
    "source_pdf_page": 34,
}


@pytest.mark.parametrize(
    "jawaban, harapan",
    [
        ("2 SKS", True),
        ("2", True),
        ("dua sks", True),
        ("Kecerdasan Artifisial (CIF63110) 2 SKS", True),  # angka dalam kode MK diabaikan
        ("3 SKS", False),
        ("12 SKS", False),
        ("2 SKS atau 3 SKS", False),
        ("", False),
    ],
)
def test_soal_angka(jawaban: str, harapan: bool) -> None:
    benar, _ = evaluation.is_answer_correct(jawaban, Q_SKS)
    assert benar is harapan


def test_soal_kode_mk_tidak_memakai_aturan_angka() -> None:
    q_kode = {
        "expected_answer_type_coarse": "NUMERIC",
        "ground_truth": "CIF62104.",
        "acceptable_variants": [],
    }
    assert evaluation.is_answer_correct("CIF62104", q_kode)[0]
    assert evaluation.is_answer_correct("Kode Basis Data adalah CIF62104", q_kode)[0]
    assert not evaluation.is_answer_correct("CIF62105", q_kode)[0]


def test_jawaban_terlarang_tidak_dianggap_benar() -> None:
    assert evaluation.is_answer_correct("Kecerdasan Artifisial", Q_GANTI)[0]
    assert evaluation.is_answer_correct("CIF63110 - Kecerdasan Artifisial", Q_GANTI)[0]
    assert not evaluation.is_answer_correct("Kecerdasan Artifisial Lanjut", Q_GANTI)[0]


def test_daftar_urutan_bebas_tapi_harus_lengkap() -> None:
    dibalik = "Pemerolehan Informasi dan Penambangan Teks, Pemrosesan Bahasa Alami"
    assert evaluation.is_answer_correct(dibalik, Q_LIST)[0]
    assert not evaluation.is_answer_correct("Pemrosesan Bahasa Alami", Q_LIST)[0]


def test_rank_dan_not_found() -> None:
    output = {
        "status": "answered",
        "answer": "3 SKS",
        "top_candidates": [{"answer": "3 SKS"}, {"answer": "2 SKS"}],
    }
    assert evaluation.find_correct_rank(output, Q_SKS)[0] == 2
    assert evaluation.find_correct_rank({"status": "not_found"}, Q_SKS)[0] is None


def test_soal_tiap_anggota_digabung(tmp_path) -> None:
    import json

    (tmp_path / "eval_q17_q20.json").write_text(json.dumps([Q_SKS]), encoding="utf-8")
    (tmp_path / "eval_q05_q08.json").write_text(json.dumps([{"id": "Q05"}]), encoding="utf-8")
    soal = evaluation.load_questions(tmp_path / "questions.json")  # questions.json sengaja tidak ada
    assert [q["id"] for q in soal] == ["Q05", "Q17"]


def test_run_evaluation_dengan_jawaban_tiruan(tmp_path) -> None:
    questions_file = tmp_path / "questions.json"
    questions_file.write_text(
        __import__("json").dumps([Q_SKS, Q_GANTI, Q_LIST]), encoding="utf-8"
    )
    jawaban_tiruan = {
        Q_SKS["question"]: {  # benar di peringkat 1
            "status": "answered",
            "answer": "2 SKS",
            "source": {"pdf_page": 20, "doc_page": "12"},
            "top_candidates": [{"answer": "2 SKS"}, {"answer": "3 SKS"}],
        },
        Q_GANTI["question"]: {  # benar di peringkat 2
            "status": "answered",
            "answer": "Kecerdasan Artifisial Lanjut",
            "source": {"pdf_page": 41},
            "top_candidates": [
                {"answer": "Kecerdasan Artifisial Lanjut"},
                {"answer": "Kecerdasan Artifisial"},
            ],
        },
    }

    def answer_fn(question: str) -> dict:
        if question not in jawaban_tiruan:
            raise RuntimeError("modul belum siap")  # soal ketiga sengaja error
        return jawaban_tiruan[question]

    csv_file = tmp_path / "hasil.csv"
    summary = evaluation.run_evaluation(questions_file, csv_file, answer_fn=answer_fn)

    assert summary["n_correct"] == 1
    assert summary["accuracy"] == pytest.approx(1 / 3)
    assert summary["mrr"] == pytest.approx((1 + 0.5 + 0) / 3)

    rows = list(csv.DictReader(open(csv_file, encoding="utf-8")))
    assert [r["status"] for r in rows] == ["Benar", "Salah", "Salah"]
    assert "sumber sesuai" in rows[0]["analisis"]
    assert "error saat menjawab" in rows[2]["analisis"]
