"""Pengujian modul Passage Retrieval, Relation Retrieval, & Reranking (Anggota 4).

Memverifikasi fungsi:
1. Pembuatan indeks retrieval klasik (BM25 & TF-IDF) dan indeks relasi Knowledge Base.
2. Pencarian top-k passage dengan perpaduan kata kunci dan query expansion.
3. Ekstraksi 6 fitur pemeringkatan passage sesuai materi PBA14 Slide 52.
4. Pemeringkatan ulang kandidat passage (Passage Reranking).
5. Pengambilan fakta terstruktur (Relation Retrieval) dari KB Triples.
6. Integrasi penuh dengan dataset korpus Kurikulum 2024 dan 4 soal evaluasi Q13-Q16.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.contracts import KnowledgeTriple, PassageRecord, QuestionAnalysis, RetrievedPassage
from src.retrieval import index_builder, ranking, retriever

BASE_DIR = Path(__file__).resolve().parent.parent
PASSAGES_PATH = BASE_DIR / "data" / "processed" / "passages.jsonl"
TRIPLES_PATH = BASE_DIR / "data" / "processed" / "knowledge_triples.jsonl"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "question_analysis_samples.json"
EVAL_Q13_Q16_PATH = BASE_DIR / "data" / "evaluation" / "eval_q13_q16.json"


def test_retrieval_module_imports() -> None:
    """Memastikan seluruh fungsi publik modul retrieval tersedia."""
    assert hasattr(index_builder, "build_index")
    assert hasattr(retriever, "retrieve_passages")
    assert hasattr(retriever, "retrieve_triples")
    assert hasattr(ranking, "extract_passage_ranking_features")
    assert hasattr(ranking, "rank_passages")


def test_build_index_bm25_and_tfidf() -> None:
    """Menguji pembuatan indeks BM25 dan TF-IDF pada dataset kecil."""
    mock_passages: list[PassageRecord] = [
        {
            "passage_id": "p_01",
            "text": "Mata kuliah Kecerdasan Artifisial berbobot 3 SKS pada semester 4.",
            "stemmed_text": "mata kuliah cerdas artifisial bobot 3 sks semester 4",
            "tokens": ["mata", "kuliah", "kecerdasan", "artifisial", "berbobot", "3", "sks", "semester", "4"],
            "pdf_page": 20,
            "doc_page": "12",
            "section": "6. Struktur Kurikulum",
            "content_type": "table",
        },
        {
            "passage_id": "p_02",
            "text": "Prasyarat Kecerdasan Artifisial Lanjut adalah Kecerdasan Artifisial nilai minimum C.",
            "stemmed_text": "syarat cerdas artifisial lanjut cerdas artifisial nilai minimum c",
            "tokens": ["prasyarat", "kecerdasan", "artifisial", "lanjut", "nilai", "minimum", "c"],
            "pdf_page": 21,
            "doc_page": "13",
            "section": "6. Struktur Kurikulum",
            "content_type": "table",
        },
    ]

    mock_triples: list[KnowledgeTriple] = [
        {
            "triple_id": "t_01",
            "subject": "Kecerdasan Artifisial Lanjut",
            "predicate": "prerequisite_of",
            "object": "Kecerdasan Artifisial",
            "pdf_page": 21,
            "doc_page": "13",
            "section": "6. Struktur Kurikulum",
            "content_type": "table",
        }
    ]

    # Uji pembuatan indeks BM25
    idx_bm25 = index_builder.build_index(mock_passages, method="bm25", triples=mock_triples)
    assert idx_bm25.method == "bm25"
    assert idx_bm25.total_docs == 2
    assert "kecerdasan" in idx_bm25.vocab
    assert "artifisial" in idx_bm25.vocab
    assert idx_bm25.avg_dl > 0
    assert ("kecerdasan artifisial lanjut", "prerequisite_of") in idx_bm25.kb_pair_index

    # Uji pembuatan indeks TF-IDF
    idx_tfidf = index_builder.build_index(mock_passages, method="tfidf", triples=mock_triples)
    assert idx_tfidf.method == "tfidf"
    assert idx_tfidf.total_docs == 2
    assert idx_tfidf.doc_vectors is not None
    assert len(idx_tfidf.doc_vectors) == 2


def test_passage_ranking_features_slide52() -> None:
    """Menguji ekstraksi 6 fitur pemeringkatan passage sesuai materi perkuliahan PBA14 Slide 52."""
    cand: RetrievedPassage = {
        "passage_id": "p_02",
        "score": 12.5,
        "doc_rank": 1,
        "rerank_score": 12.5,
        "rerank_features": {},
        "text": "Prasyarat mata kuliah Kecerdasan Artifisial Lanjut adalah CIF63110 Kecerdasan Artifisial dengan nilai minimum C.",
        "pdf_page": 21,
        "doc_page": "13",
        "section": "6. Struktur Kurikulum",
        "content_type": "table",
    }

    qa: QuestionAnalysis = {
        "original_question": "Apa prasyarat Kecerdasan Artifisial Lanjut?",
        "normalized_question": "apa prasyarat kecerdasan artifisial lanjut",
        "tokens": ["apa", "prasyarat", "kecerdasan", "artifisial", "lanjut"],
        "speech_act": "wh",
        "question_category": "factoid",
        "intent": "course_prerequisite",
        "answer_type_coarse": "ENTITY",
        "answer_type": "ENTITY:prerequisite",
        "focus": "prasyarat",
        "query_keywords": ["prasyarat", "Kecerdasan Artifisial Lanjut", "CIF64311"],
        "expanded_queries": ["syarat Kecerdasan Artifisial Lanjut"],
        "entities": [{"type": "course_name", "value": "kecerdasan artifisial lanjut", "normalized_value": "Kecerdasan Artifisial Lanjut"}],
        "relations": [{"predicate": "prerequisite_of", "subject": "Kecerdasan Artifisial Lanjut", "object": None}],
    }

    features = ranking.extract_passage_ranking_features(cand, qa)

    # Verifikasi 6 fitur wajib PBA14 Slide 52
    assert "answer_type_ne_count" in features
    assert "keyword_match_count" in features
    assert "longest_keyword_seq" in features
    assert "source_doc_rank" in features
    assert "keyword_proximity" in features
    assert "ngram_overlap" in features

    # Nilai harus valid, positif, dan terukur
    assert features["keyword_match_count"] >= 3.0
    assert features["longest_keyword_seq"] >= 2.0
    assert features["source_doc_rank"] == 1.0  # 1 / rank 1 = 1.0
    assert features["keyword_proximity"] > 0.0
    assert features["ngram_overlap"] > 0.0


def test_rank_passages_reranking() -> None:
    """Menguji pemeringkatan ulang kandidat passage dengan pembaruan doc_rank dan rerank_score."""
    c1: RetrievedPassage = {
        "passage_id": "p_01",
        "score": 10.0,
        "doc_rank": 1,
        "rerank_score": 10.0,
        "rerank_features": {},
        "text": "Struktur kurikulum mencakup berbagai mata kuliah umum.",
        "pdf_page": 10,
        "doc_page": "2",
        "section": "Pendahuluan",
        "content_type": "text",
    }
    c2: RetrievedPassage = {
        "passage_id": "p_02",
        "score": 8.0,
        "doc_rank": 2,
        "rerank_score": 8.0,
        "rerank_features": {},
        "text": "Prasyarat mata kuliah Kecerdasan Artifisial Lanjut adalah Kecerdasan Artifisial nilai minimum C.",
        "pdf_page": 21,
        "doc_page": "13",
        "section": "6. Struktur Kurikulum",
        "content_type": "table",
    }

    qa: QuestionAnalysis = {
        "original_question": "Apa prasyarat Kecerdasan Artifisial Lanjut?",
        "normalized_question": "apa prasyarat kecerdasan artifisial lanjut",
        "tokens": ["apa", "prasyarat", "kecerdasan", "artifisial", "lanjut"],
        "speech_act": "wh",
        "question_category": "factoid",
        "intent": "course_prerequisite",
        "answer_type_coarse": "ENTITY",
        "answer_type": "ENTITY:prerequisite",
        "focus": "prasyarat",
        "query_keywords": ["prasyarat", "Kecerdasan Artifisial Lanjut"],
        "expanded_queries": [],
        "entities": [],
        "relations": [],
    }

    reranked = ranking.rank_passages([c1, c2], qa)
    assert len(reranked) == 2
    # Passage 2 memiliki kesesuaian kata kunci, sequence, dan tipe entitas yang jauh lebih tinggi
    assert reranked[0]["passage_id"] == "p_02"
    assert reranked[0]["doc_rank"] == 1
    assert reranked[1]["doc_rank"] == 2
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]


def test_relation_retrieval_triples() -> None:
    """Menguji pengambilan fakta terstruktur (triple) dari relasi dan entitas pertanyaan."""
    triples: list[KnowledgeTriple] = [
        {
            "triple_id": "t_100",
            "subject": "Pemrograman Lanjut",
            "predicate": "prerequisite_of",
            "object": "COM60014 Pemrograman Dasar",
            "pdf_page": 20,
            "doc_page": "12",
            "section": "6. Struktur Kurikulum",
            "content_type": "table",
        },
        {
            "triple_id": "t_101",
            "subject": "Pemrograman Lanjut",
            "predicate": "min_grade",
            "object": "D",
            "pdf_page": 20,
            "doc_page": "12",
            "section": "6. Struktur Kurikulum",
            "content_type": "table",
        },
    ]

    idx = index_builder.build_index([], method="bm25", triples=triples)

    qa: QuestionAnalysis = {
        "original_question": "Apa prasyarat Pemrograman Lanjut?",
        "normalized_question": "apa prasyarat pemrograman lanjut",
        "tokens": ["apa", "prasyarat", "pemrograman", "lanjut"],
        "speech_act": "wh",
        "question_category": "factoid",
        "intent": "course_prerequisite",
        "answer_type_coarse": "ENTITY",
        "answer_type": "ENTITY:prerequisite",
        "focus": "prasyarat",
        "query_keywords": ["prasyarat", "Pemrograman Lanjut"],
        "expanded_queries": [],
        "entities": [{"type": "course_name", "value": "pemrograman lanjut", "normalized_value": "Pemrograman Lanjut"}],
        "relations": [{"predicate": "prerequisite_of", "subject": "Pemrograman Lanjut", "object": None}],
    }

    res_triples = retriever.retrieve_triples(qa, idx)
    assert len(res_triples) >= 1
    assert any(t["object"] == "COM60014 Pemrograman Dasar" for t in res_triples)


def test_real_corpus_retrieval_and_eval_q13_q16() -> None:
    """Menguji integrasi menyeluruh modul retrieval pada korpus 392 passage dan 1.177 knowledge triples."""
    if not PASSAGES_PATH.exists() or not TRIPLES_PATH.exists():
        return

    with open(PASSAGES_PATH, "r", encoding="utf-8") as f:
        passages = [json.loads(line) for line in f]
    with open(TRIPLES_PATH, "r", encoding="utf-8") as f:
        triples = [json.loads(line) for line in f]

    assert len(passages) >= 300
    assert len(triples) >= 1000

    idx_bm25 = index_builder.build_index(passages, method="bm25", triples=triples)
    idx_tfidf = index_builder.build_index(passages, method="tfidf", triples=triples)

    # Uji 4 soal evaluasi Anggota 4 (Q13 - Q16)
    if EVAL_Q13_Q16_PATH.exists():
        with open(EVAL_Q13_Q16_PATH, "r", encoding="utf-8") as f:
            q13_q16 = json.load(f)

        assert len(q13_q16) == 4

        for item in q13_q16:
            qa: QuestionAnalysis = {
                "original_question": item["question"],
                "normalized_question": item["question"].lower(),
                "tokens": item["question"].lower().split(),
                "speech_act": item["speech_act"],
                "question_category": item["question_category"],
                "intent": item["question_type"],
                "answer_type_coarse": item["expected_answer_type_coarse"],
                "answer_type": item["expected_answer_type"],
                "query_keywords": item["question"].replace("?", "").split(),
                "expanded_queries": [],
                "entities": [],
                "relations": [],
            }

            ret_res = retriever.retrieve_passages(qa, idx_bm25, top_k=5)
            assert len(ret_res["results"]) > 0

            # Verifikasi bahwa minimal satu passage di top-5 cocok dengan nomor halaman sumber soal
            expected_page = item["source_pdf_page"]
            found_pages = [p["pdf_page"] for p in ret_res["results"]]
            assert expected_page in found_pages, f"Soal {item['id']} halaman sumber {expected_page} tidak ditemukan di top-5: {found_pages}"
