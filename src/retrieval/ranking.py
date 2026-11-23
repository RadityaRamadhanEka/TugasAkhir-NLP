"""Re-ranking kandidat passage berbasis Answer Type & 6 Fitur PBA14 Slide 51-52.

Modul ini mengimplementasikan pemeringkatan ulang kandidat passage yang dihasilkan dari
tahap retrieval awal menggunakan Taksonomi Li & Roth serta 6 fitur pemeringkatan passage:
1. answer_type_ne_count  : Jumlah named entities yang cocok dengan expected answer_type
2. keyword_match_count   : Jumlah question keywords yang muncul pada passage
3. longest_keyword_seq   : Panjang rangkaian kata kunci terpanjang yang muncul berurutan
4. source_doc_rank       : Peringkat dokumen asal passage dari tahap retrieval pertama
5. keyword_proximity     : Kedekatan (jarak token) antar kata kunci query pada passage
6. ngram_overlap         : Bigram/trigram overlap antara passage dan pertanyaan
"""

from __future__ import annotations

import re
from typing import Any

from src.contracts import QuestionAnalysis, RetrievedPassage


def _tokenize_passage(text: str) -> list[str]:
    """Tokenisasi teks passage menjadi daftar token huruf kecil."""
    if not text:
        return []
    return [t.lower() for t in re.findall(r"\b[a-zA-Z0-9_]+(?:[.-][a-zA-Z0-9_]+)*\b", text)]


def _extract_ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    """Mengekstrak himpunan n-gram dari daftar token."""
    if len(tokens) < n:
        return set()
    return set(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def _count_answer_type_entities(text: str, answer_type: str, coarse_type: str) -> float:
    """Menghitung frekuensi entitas/indikator pada teks passage yang sesuai tipe jawaban yang diharapkan."""
    if not text:
        return 0.0

    lower_text = text.lower()
    count = 0.0

    # 1. NUMERIC
    if coarse_type == "NUMERIC" or "numeric" in answer_type.lower():
        if "grade" in answer_type:
            # Nilai huruf prasyarat (A, B, C, D, E)
            grades = re.findall(r"\b(?:nilai\s+(?:minimum|minimal\s+)?)?([a-e])\b", lower_text)
            count += float(len(grades))
        elif "code" in answer_type:
            # Kode mata kuliah (CIF63110, COM60014, dll)
            codes = re.findall(r"\b[a-z]{3}\d{5}(?:-\d)?\b", lower_text)
            count += float(len(codes))
        elif "order" in answer_type or "semester" in answer_type:
            # Angka semester
            semesters = re.findall(r"\b(?:semester\s+)?([1-8]|antara|ganjil|genap)\b", lower_text)
            count += float(len(semesters))
        else:
            # Angka SKS atau hitungan umum
            sks_matches = re.findall(r"\b\d+\s*sks\b", lower_text)
            numbers = re.findall(r"\b\d+\b", lower_text)
            count += float(len(sks_matches) * 2 + len(numbers))

    # 2. ENTITY
    elif coarse_type == "ENTITY" or "entity" in answer_type.lower():
        # Hitung kode MK atau pola nama MK / CPL
        codes = re.findall(r"\b[a-z]{3}\d{5}(?:-\d)?\b", lower_text)
        cpls = re.findall(r"\bif[_\s-]?cpl[_\s-]?[a-z0-9]+\b", lower_text)
        # Indikator kurikulum/mata kuliah
        mk_keywords = re.findall(r"\b(?:mata kuliah|prasyarat|learning path|kurikulum)\b", lower_text)
        count += float(len(codes) * 2 + len(cpls) * 2 + len(mk_keywords))

    # 3. DESCRIPTION
    elif coarse_type == "DESCRIPTION" or "description" in answer_type.lower():
        # Indikator penjelas narasi, definisi, atau cara (manner)
        descriptors = re.findall(
            r"\b(?:merupakan|adalah|yaitu|bertujuan|diwajibkan|aturan|ketentuan|melalui|solusi|syarat|rekomendasi)\b",
            lower_text,
        )
        count += float(len(descriptors))

    # 4. HUMAN
    elif coarse_type == "HUMAN" or "human" in answer_type.lower():
        # Gelar akademik atau jabatan profesi
        titles = re.findall(
            r"\b(?:dosen|ketua|anggota|tim|developer|engineer|scientist|s\.kom|m\.kom|ph\.d|dr\.|ir\.)\b",
            lower_text,
        )
        count += float(len(titles))

    # 5. ABBREVIATION
    elif coarse_type == "ABBREVIATION" or "abbreviation" in answer_type.lower():
        # Kata singkatan kapital (SKS, MBKM, CPL, dsb.)
        abbrs = re.findall(r"\b[A-Z]{2,6}\b", text)
        count += float(len(abbrs))

    else:
        # Default fallback
        count = 1.0 if len(text) > 20 else 0.0

    return count


def _compute_longest_keyword_sequence(passage_tokens: list[str], keyword_tokens: list[str]) -> int:
    """Menghitung panjang rangkaian kata kunci kueri terpanjang yang muncul berurutan pada passage."""
    if not passage_tokens or not keyword_tokens:
        return 0

    kw_set = set(t.lower() for t in keyword_tokens)
    max_len = 0
    current_len = 0

    for tok in passage_tokens:
        if tok in kw_set:
            current_len += 1
            if current_len > max_len:
                max_len = current_len
        else:
            current_len = 0

    return max_len


def _compute_keyword_proximity(passage_tokens: list[str], keyword_tokens: list[str]) -> float:
    """Menghitung kedekatan (proximity) kata kunci kueri di dalam passage.

    Menggunakan rasio jumlah kata kunci yang cocok terhadap rentang span token minimum.
    """
    if not passage_tokens or not keyword_tokens:
        return 0.0

    kw_set = set(t.lower() for t in keyword_tokens)
    positions: list[int] = []

    for idx, tok in enumerate(passage_tokens):
        if tok in kw_set:
            positions.append(idx)

    if not positions:
        return 0.0
    if len(positions) == 1:
        return 0.5  # Satu kata kunci cocok

    # Cari span terkecil yang memuat kemunculan kata kunci berbeda
    min_span = positions[-1] - positions[0] + 1
    # Sliding window untuk menemukan span minimum terdekat
    for i in range(len(positions) - 1):
        span = positions[i + 1] - positions[i] + 1
        if span < min_span:
            min_span = span

    matched_kw_count = len(set(passage_tokens[p] for p in positions))
    proximity = matched_kw_count / (min_span + 1.0)
    return min(proximity, 1.0)


def _compute_ngram_overlap(question_tokens: list[str], passage_tokens: list[str]) -> float:
    """Menghitung koefisien overlap n-gram (bigram dan trigram) antara pertanyaan dan passage."""
    if len(question_tokens) < 2 or len(passage_tokens) < 2:
        # Unigram overlap fallback jika pertanyaan sangat pendek
        q_uni = set(question_tokens)
        p_uni = set(passage_tokens)
        return len(q_uni & p_uni) / max(len(q_uni), 1)

    q_bi = _extract_ngrams(question_tokens, 2)
    p_bi = _extract_ngrams(passage_tokens, 2)
    bi_overlap = (2.0 * len(q_bi & p_bi)) / (len(q_bi) + len(p_bi)) if (len(q_bi) + len(p_bi)) > 0 else 0.0

    q_tri = _extract_ngrams(question_tokens, 3)
    p_tri = _extract_ngrams(passage_tokens, 3)
    tri_overlap = (2.0 * len(q_tri & p_tri)) / (len(q_tri) + len(p_tri)) if (len(q_tri) + len(p_tri)) > 0 else 0.0

    if q_tri and p_tri:
        return 0.5 * bi_overlap + 0.5 * tri_overlap
    return bi_overlap


def extract_passage_ranking_features(
    passage: RetrievedPassage,
    question_analysis: QuestionAnalysis,
) -> dict[str, float]:
    """Menghitung 6 fitur pemeringkatan passage (PBA14 Slide 52) untuk satu kandidat passage.

    Fitur yang dihitung:
    1. answer_type_ne_count: Jumlah named entities yang cocok dengan expected answer_type.
    2. keyword_match_count: Jumlah question keywords yang muncul pada passage.
    3. longest_keyword_seq: Panjang rangkaian kata kunci terpanjang yang muncul berurutan.
    4. source_doc_rank: Peringkat dokumen asal passage dari tahap retrieval pertama (1/rank).
    5. keyword_proximity: Kedekatan jarak token antar kata kunci query pada teks passage.
    6. ngram_overlap: Overlap bigram & trigram antara teks passage dan pertanyaan.
    """
    text = passage.get("text", "")
    p_tokens = _tokenize_passage(text)

    # Kata kunci pertanyaan
    keywords = question_analysis.get("query_keywords", [])
    if not keywords:
        keywords = question_analysis.get("tokens", [])

    # Tokenisasi pertanyaan utuh untuk n-gram
    q_norm = question_analysis.get("normalized_question") or question_analysis.get("original_question", "")
    q_tokens = _tokenize_passage(q_norm)

    # 1. Answer Type NE count
    ans_type = question_analysis.get("answer_type", "")
    coarse_type = question_analysis.get("answer_type_coarse", "")
    ne_count = _count_answer_type_entities(text, ans_type, coarse_type)

    # 2. Keyword match count
    # Pisahkan frasa keyword menjadi sub-token agar pencocokan presisi
    flat_kw_tokens: list[str] = []
    for kw in keywords:
        flat_kw_tokens.extend(_tokenize_passage(str(kw)))
    flat_kw_tokens = list(set(flat_kw_tokens))

    p_tokens_set = set(p_tokens)
    matched_keywords = [kw for kw in flat_kw_tokens if kw in p_tokens_set]
    kw_match_count = float(len(matched_keywords))

    # 3. Longest keyword sequence
    longest_seq = float(_compute_longest_keyword_sequence(p_tokens, flat_kw_tokens))

    # 4. Source document rank (inversi 1/rank dari tahap retrieval awal)
    doc_rank = passage.get("doc_rank", 1)
    source_doc_rank = 1.0 / float(max(doc_rank, 1))

    # 5. Keyword proximity
    proximity = _compute_keyword_proximity(p_tokens, flat_kw_tokens)

    # 6. N-gram overlap
    ngram_overlap = _compute_ngram_overlap(q_tokens, p_tokens)

    return {
        "answer_type_ne_count": round(ne_count, 4),
        "keyword_match_count": round(kw_match_count, 4),
        "longest_keyword_seq": round(longest_seq, 4),
        "source_doc_rank": round(source_doc_rank, 4),
        "keyword_proximity": round(proximity, 4),
        "ngram_overlap": round(ngram_overlap, 4),
    }


def rank_passages(
    candidates: list[RetrievedPassage],
    question_analysis: QuestionAnalysis,
) -> list[RetrievedPassage]:
    """Mengurutkan ulang kandidat passage memakai answer_type & 6 fitur Slide 52.

    Menghitung skor gabungan linier:
    rerank_score = w0 * base_score + sum(wi * feature_i)
    lalu memperbarui rerank_features, rerank_score, dan doc_rank pada tiap passage.
    """
    if not candidates:
        return []

    # Ekstraksi fitur untuk semua kandidat
    features_list: list[dict[str, float]] = []
    max_base_score = max((c.get("score", 0.0) for c in candidates), default=1.0)
    if max_base_score <= 0.0:
        max_base_score = 1.0

    for c in candidates:
        feat = extract_passage_ranking_features(c, question_analysis)
        features_list.append(feat)

    # Tentukan bobot linear terkalibrasi untuk 6 fitur PBA14
    # w_base = 0.35, w_doc_rank = 0.15, w_kw = 0.15, w_seq = 0.10, w_prox = 0.10, w_ngram = 0.10, w_ne = 0.05
    reranked: list[RetrievedPassage] = []
    for cand, feat in zip(candidates, features_list):
        norm_base_score = cand.get("score", 0.0) / max_base_score

        # Normalisasi fitur skalar
        ne_norm = min(feat["answer_type_ne_count"] / 10.0, 1.0)
        kw_norm = min(feat["keyword_match_count"] / 10.0, 1.0)
        seq_norm = min(feat["longest_keyword_seq"] / 5.0, 1.0)
        doc_rank_val = feat["source_doc_rank"]
        prox_val = feat["keyword_proximity"]
        ngram_val = feat["ngram_overlap"]

        composite_score = (
            0.35 * norm_base_score
            + 0.15 * doc_rank_val
            + 0.15 * kw_norm
            + 0.10 * seq_norm
            + 0.10 * prox_val
            + 0.10 * ngram_val
            + 0.05 * ne_norm
        )

        cand_copy: RetrievedPassage = dict(cand)  # type: ignore
        cand_copy["rerank_features"] = feat
        cand_copy["rerank_score"] = round(composite_score, 4)
        reranked.append(cand_copy)

    # Urutkan secara menurun berdasarkan rerank_score
    reranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

    # Perbarui urutan peringkat doc_rank (1-indexed)
    for idx, passage in enumerate(reranked, start=1):
        passage["doc_rank"] = idx

    return reranked
