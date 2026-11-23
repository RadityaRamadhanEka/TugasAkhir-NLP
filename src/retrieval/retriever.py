"""Pencarian top-k passage (IR-based) & relation retrieval dari Knowledge Base (Hybrid QA).

Modul ini mengimplementasikan pencarian korpus hybrid sesuai materi PBA14 (Slide 52, 66-75):
1. retrieve_passages : Menghitung relevansi teks (BM25 / TF-IDF Cosine) memanfaatkan query keywords,
                       expanded queries, dan entitas, lalu memeringkat ulang kandidat dengan 6 fitur reranking.
2. retrieve_triples  : Mengambil fakta terstruktur (subject, predicate, object) dari tabel & transkripsi visual
                       berdasarkan analisis relasi semantik dan entitas pertanyaan.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from src.contracts import KnowledgeTriple, QuestionAnalysis, RetrievalResult, RetrievedPassage
from src.retrieval.index_builder import RetrievalIndex, _normalize_kb_key, _tokenize_text
from src.retrieval.ranking import rank_passages


def _score_bm25_query(
    query_tokens: list[str],
    index: RetrievalIndex,
) -> dict[int, float]:
    """Menghitung skor Okapi BM25 untuk satu daftar token kueri terhadap seluruh dokumen."""
    scores: dict[int, float] = Counter()
    k1 = index.bm25_k1
    b = index.bm25_b
    avg_dl = index.avg_dl if index.avg_dl > 0 else 1.0

    q_counts = Counter(query_tokens)
    for term, q_tf in q_counts.items():
        if term not in index.inverted_index:
            continue
        idf_weight = index.idf.get(term, 0.0)
        postings = index.inverted_index[term]

        for doc_idx, doc_tf in postings:
            doc_len = index.doc_lens[doc_idx]
            denom = doc_tf + k1 * (1.0 - b + b * (doc_len / avg_dl))
            numer = doc_tf * (k1 + 1.0)
            score_term = idf_weight * (numer / denom) if denom > 0 else 0.0
            scores[doc_idx] += score_term

    return scores


def _score_tfidf_query(
    query_tokens: list[str],
    index: RetrievalIndex,
) -> dict[int, float]:
    """Menghitung skor TF-IDF Cosine Similarity untuk satu daftar token kueri terhadap seluruh dokumen."""
    scores: dict[int, float] = Counter()
    if not index.doc_vectors:
        return scores

    q_counts = Counter(query_tokens)
    q_len = len(query_tokens) if len(query_tokens) > 0 else 1

    # Bentuk vektor kueri
    q_vec: dict[str, float] = {}
    norm_sq = 0.0
    for term, count in q_counts.items():
        if term in index.idf:
            tf_val = count / q_len
            val = tf_val * index.idf[term]
            q_vec[term] = val
            norm_sq += val * val

    q_norm = math.sqrt(norm_sq)
    if q_norm <= 0.0:
        return scores

    normalized_q = {t: val / q_norm for t, val in q_vec.items()}

    # Hitung dot product (cosine similarity karena vektor dokumen sudah ternormalisasi L2)
    for term, q_weight in normalized_q.items():
        if term not in index.inverted_index:
            continue
        for doc_idx, _ in index.inverted_index[term]:
            doc_vec = index.doc_vectors[doc_idx]
            d_weight = doc_vec.get(term, 0.0)
            scores[doc_idx] += q_weight * d_weight

    return scores


def retrieve_passages(
    question_analysis: QuestionAnalysis,
    index: Any,
    top_k: int = 5,
) -> RetrievalResult:
    """Mengambil top-k passage relevan (TF-IDF/BM25) + kandidat triple terstruktur bila tersedia.

    Menggunakan `query_keywords`, `expanded_queries`, entitas, serta 6 fitur passage reranking.

    Args:
        question_analysis: Objek QuestionAnalysis dari modul question_processing.
        index: Objek RetrievalIndex yang dibangun oleh index_builder.
        top_k: Jumlah passage teratas yang dikembalikan (default: 5).

    Returns:
        RetrievalResult: Berisi kueri utama, daftar top-k passage terurut, dan structured_results (triples).
    """
    if not isinstance(index, RetrievalIndex):
        raise TypeError("Indeks harus merupakan instansi dari RetrievalIndex.")

    # 1. Ekstraksi token kueri utama
    keywords = question_analysis.get("query_keywords", [])
    primary_query_str = " ".join(str(k) for k in keywords) if keywords else ""
    if not primary_query_str:
        primary_query_str = question_analysis.get("normalized_question") or question_analysis.get("original_question", "")

    primary_tokens = _tokenize_text(primary_query_str)

    # 2. Ekstraksi token kueri ekspansi
    expanded_queries = question_analysis.get("expanded_queries", [])
    expanded_tokens: list[str] = []
    for eq in expanded_queries:
        expanded_tokens.extend(_tokenize_text(str(eq)))

    # 3. Hitung skor retrieval awal pada seluruh korpus
    if index.method == "bm25":
        base_scores = _score_bm25_query(primary_tokens, index)
        if expanded_tokens:
            exp_scores = _score_bm25_query(expanded_tokens, index)
            for doc_idx, s in exp_scores.items():
                base_scores[doc_idx] = base_scores.get(doc_idx, 0.0) + 0.25 * s
    else:
        base_scores = _score_tfidf_query(primary_tokens, index)
        if expanded_tokens:
            exp_scores = _score_tfidf_query(expanded_tokens, index)
            for doc_idx, s in exp_scores.items():
                base_scores[doc_idx] = base_scores.get(doc_idx, 0.0) + 0.25 * s

    # 4. Tambahkan boost prior jika entitas kunci (seperti kode MK atau kode CPL) cocok eksplisit
    entities = question_analysis.get("entities", [])
    for ent in entities:
        norm_val = str(ent.get("normalized_value") or ent.get("value", "")).lower()
        if not norm_val:
            continue
        ent_tokens = _tokenize_text(norm_val)
        for doc_idx, tokens in enumerate(index.doc_tokens):
            t_set = set(tokens)
            if all(et in t_set for et in ent_tokens):
                base_scores[doc_idx] = base_scores.get(doc_idx, 0.0) + 0.5

    # 5. Kumpulkan kandidat dokumen dengan skor tertinggi
    sorted_doc_indices = sorted(base_scores.keys(), key=lambda idx: base_scores[idx], reverse=True)

    # Ambil kandidat awal untuk diproses reranking (misal top 25 atau minimal top_k * 4)
    initial_pool_size = max(25, top_k * 4)
    candidate_indices = sorted_doc_indices[:initial_pool_size]

    candidates: list[RetrievedPassage] = []
    for rank_idx, doc_idx in enumerate(candidate_indices, start=1):
        raw_score = float(base_scores[doc_idx])
        p = index.passages[doc_idx]

        cand: RetrievedPassage = {
            "passage_id": p.get("passage_id", ""),
            "score": round(raw_score, 4),
            "doc_rank": rank_idx,
            "rerank_score": round(raw_score, 4),
            "rerank_features": {},
            "text": p.get("text", ""),
            "pdf_page": p.get("pdf_page", 0),
            "doc_page": p.get("doc_page", ""),
            "source_page": p.get("source_page", p.get("pdf_page", 0)),
            "section": p.get("section", ""),
            "content_type": p.get("content_type", "text"),
            "table_title": p.get("table_title"),
            "metadata": p.get("metadata", {}),
        }
        candidates.append(cand)

    # 6. Jalankan Passage Reranking berbasis Answer Type & 6 Fitur PBA14 Slide 52
    reranked_candidates = rank_passages(candidates, question_analysis)
    final_passages = reranked_candidates[:top_k]

    # 7. Ambil fakta terstruktur dari Knowledge Base (Structured Relation Retrieval)
    structured_results = retrieve_triples(question_analysis, index)

    return {
        "query": primary_query_str,
        "results": final_passages,
        "structured_results": structured_results,
    }


def retrieve_triples(
    question_analysis: QuestionAnalysis,
    index: Any,
) -> list[KnowledgeTriple]:
    """Mencari fakta terstruktur `(subject, predicate, object)` sesuai entitas & relasi pertanyaan.

    Mendukung penanganan multi-relasi, pencocokan kode MK <-> nama MK (aliasing),
    dan pencarian berbasis predikat domain kurikulum.
    """
    if not isinstance(index, RetrievalIndex) or not index.triples:
        return []

    matched_triples: list[KnowledgeTriple] = []
    seen_ids: set[str] = set()

    def _add_triple(t: KnowledgeTriple) -> None:
        tid = t.get("triple_id", "")
        if tid and tid not in seen_ids:
            seen_ids.add(tid)
            matched_triples.append(t)
        elif not tid:
            matched_triples.append(t)

    relations = question_analysis.get("relations", [])
    entities = question_analysis.get("entities", [])
    intent = question_analysis.get("intent", "")

    # 1. Pencocokan langsung dari relasi semantik yang diekstrak oleh Question Processing
    for rel in relations:
        pred = str(rel.get("predicate", "")).strip().lower()
        subj_raw = rel.get("subject")
        obj_raw = rel.get("object")

        subjs_to_try: list[str] = []
        if subj_raw:
            s_norm = _normalize_kb_key(subj_raw)
            subjs_to_try.append(s_norm)
            # Cek alias (misal kode MK <-> nama MK)
            if s_norm in index.kb_subject_aliases:
                subjs_to_try.append(index.kb_subject_aliases[s_norm])

        # A. Bila subjek dan predikat tersedia
        if subjs_to_try and pred:
            for s in subjs_to_try:
                for t in index.kb_pair_index.get((s, pred), []):
                    _add_triple(t)

            # Jika belum ketemu, cari dengan substring subjek
            if not matched_triples:
                for (kb_subj, kb_pred), triple_list in index.kb_pair_index.items():
                    if kb_pred == pred and any(s in kb_subj or kb_subj in s for s in subjs_to_try):
                        for t in triple_list:
                            _add_triple(t)

        # B. Bila subjek kosong tetapi objek dan predikat tersedia
        elif obj_raw and pred:
            o_norm = _normalize_kb_key(obj_raw)
            for t in index.kb_predicate_index.get(pred, []):
                t_obj_norm = _normalize_kb_key(t.get("object", ""))
                if o_norm == t_obj_norm or o_norm in t_obj_norm or t_obj_norm in o_norm:
                    _add_triple(t)

        # C. Bila hanya subjek yang tersedia
        elif subjs_to_try:
            for s in subjs_to_try:
                for t in index.kb_subject_index.get(s, []):
                    _add_triple(t)

    # 2. Cadangan: pencarian berbasis entitas dan intent bila relasi belum membuahkan hasil
    if not matched_triples and entities:
        for ent in entities:
            ent_val = str(ent.get("normalized_value") or ent.get("value", "")).strip()
            ent_norm = _normalize_kb_key(ent_val)
            if not ent_norm:
                continue

            candidates_for_ent: list[KnowledgeTriple] = []
            # Coba cari sebagai subjek
            if ent_norm in index.kb_subject_index:
                candidates_for_ent.extend(index.kb_subject_index[ent_norm])
            elif ent_norm in index.kb_subject_aliases and index.kb_subject_aliases[ent_norm] in index.kb_subject_index:
                candidates_for_ent.extend(index.kb_subject_index[index.kb_subject_aliases[ent_norm]])

            # Coba cari sebagai objek (misal nama learning path atau kelompok pilihan)
            if ent_norm in index.kb_object_index:
                candidates_for_ent.extend(index.kb_object_index[ent_norm])

            # Filter kandidat berdasarkan intent pertanyaan jika memungkinkan
            if intent:
                intent_predicates: dict[str, list[str]] = {
                    "course_prerequisite": ["prerequisite_of", "min_grade"],
                    "course_min_grade": ["min_grade", "prerequisite_of"],
                    "course_sks": ["sks"],
                    "course_semester": ["semester"],
                    "course_practicum": ["has_practicum"],
                    "course_code": ["course_code"],
                    "course_name": ["course_name"],
                    "course_equivalence": ["equivalent_to"],
                    "learning_path": ["learning_path_member", "learning_path_sks"],
                    "elective_group": ["elective_group_member"],
                    "cpl": ["cpl_description", "supports_cpl"],
                    "total_sks": ["total_sks"],
                }
                preferred_preds = intent_predicates.get(intent, [])
                if preferred_preds:
                    filtered = [t for t in candidates_for_ent if t.get("predicate", "").lower() in preferred_preds]
                    if filtered:
                        candidates_for_ent = filtered

            for t in candidates_for_ent:
                _add_triple(t)

    return matched_triples
