"""Uji answer_ranker: bobot fitur, penggabungan kandidat, dan jawaban 'tidak ditemukan'."""

import pytest

from src.answer_processing.answer_ranker import (
    FEATURE_WEIGHTS,
    NOT_FOUND_MESSAGE,
    rank_answer_candidates,
    score_candidate,
    select_best_answer,
)

QUESTION = {"original_question": "Berapa SKS mata kuliah Kecerdasan Artifisial?"}


def _cand(answer, source_id, **features):
    return {"answer": answer, "features": features, "source": {"passage_id": source_id, "pdf_page": 20}}


def test_total_bobot_satu() -> None:
    assert sum(FEATURE_WEIGHTS.values()) == pytest.approx(1.0)


def test_kandidat_mirip_tapi_salah_kalah() -> None:
    # Rapor Q17: kandidat salah unggul di kata kunci, tapi tidak cocok jenis jawaban & pola
    benar = _cand("2 SKS", "p20", answer_type_match=1, pattern_match=1, question_keywords=1,
                  keyword_distance=0.33, novelty_factor=0.5, punctuation_location=1,
                  question_term_seq=0.5, retrieval_score=0.71)
    salah = _cand("Mata kuliah CIF64311 Kecerdasan Artifisial Lanjut, 5 SKS", "p21",
                  answer_type_match=0, pattern_match=0, question_keywords=1, keyword_distance=1,
                  novelty_factor=0.63, punctuation_location=1, question_term_seq=0.5, retrieval_score=0.78)
    ranked = rank_answer_candidates(QUESTION, [salah, benar])
    assert ranked[0]["answer"] == "2 SKS"


def test_jawaban_sama_digabung_dan_dapat_bonus_terbatas() -> None:
    features = {"answer_type_match": 1, "pattern_match": 1}
    sendiri = rank_answer_candidates(QUESTION, [_cand("2 SKS", "p1", **features)])[0]
    banyak = rank_answer_candidates(QUESTION, [_cand(a, f"p{i}", **features) for i, a in
                                               enumerate(["2 SKS", "2 sks", "2 SKS.", "2 SKS", "2 SKS", "2 SKS"])])
    assert len(banyak) == 1  # enam kandidat dengan isi sama jadi satu
    assert banyak[0]["features"]["supporting_sources"] == 6
    assert banyak[0]["score"] == pytest.approx(sendiri["score"] + 0.10)  # bonus mentok di 0.10


def test_skor_di_bawah_ambang_jadi_tidak_ditemukan() -> None:
    lemah = rank_answer_candidates(QUESTION, [_cand("sesuatu", "p1", question_keywords=1)])
    assert score_candidate(lemah[0]) < 0.2
    output = select_best_answer(QUESTION, lemah)
    assert output["status"] == "not_found"
    assert output["answer"] == NOT_FOUND_MESSAGE
    assert output["source"] is None


def test_tanpa_kandidat_tidak_ditemukan() -> None:
    assert select_best_answer(QUESTION, [])["status"] == "not_found"


def test_jawaban_terbaik_membawa_sumber_dan_top_m() -> None:
    kandidat = [_cand(f"{n} SKS", f"p{n}", answer_type_match=1, pattern_match=1 if n == 2 else 0)
                for n in range(1, 8)]
    output = select_best_answer(QUESTION, rank_answer_candidates(QUESTION, kandidat), top_m=5)
    assert output["status"] == "answered"
    assert output["answer"] == "2 SKS"
    assert output["source"]["passage_id"] == "p2"
    assert len(output["top_candidates"]) == 5
