"""Pembuatan indeks retrieval klasik (TF-IDF / BM25) & indeks Knowledge Triples.

Modul ini mengimplementasikan pembuatan struktur data inverted index untuk pencarian
dokumen korpus (passages.jsonl) dan indeks relasi Knowledge Base (knowledge_triples.jsonl)
sesuai arsitektur Hybrid QA (IR-based + Structured KB-QA) pada materi perkuliahan PBA14.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

from src.contracts import KnowledgeTriple, PassageRecord


def _tokenize_text(text: str) -> list[str]:
    """Tokenisasi teks sederhana berbasis regex untuk menjaga alfanumerik, kode MK, dan CPL."""
    if not text:
        return []
    # Pola: pertahankan kode alfanumerik (seperti cif63110, if_cpl_kk1), angka desimal, dan kata
    tokens = re.findall(r"\b[a-zA-Z0-9_]+(?:[.-][a-zA-Z0-9_]+)*\b", text.lower())
    return [t for t in tokens if len(t) > 1 or t.isdigit()]


@dataclass
class RetrievalIndex:
    """Struktur data indeks hybrid untuk retrieval passage dan relasi terstruktur."""

    method: Literal["bm25", "tfidf"]
    passages: list[PassageRecord]
    doc_ids: list[str]
    doc_tokens: list[list[str]]
    doc_lens: list[int]
    avg_dl: float
    total_docs: int
    vocab: dict[str, int]  # term -> term_id
    id_to_term: list[str]
    doc_freqs: dict[str, int]  # term -> document frequency df
    idf: dict[str, float]  # term -> idf weight
    inverted_index: dict[str, list[tuple[int, int]]]  # term -> [(doc_idx, tf)]
    doc_vectors: list[dict[str, float]] | None = None  # untuk tfidf: vektor bobot ternormalisasi
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    # Indeks Relasi Knowledge Base Triples
    triples: list[KnowledgeTriple] | None = None
    kb_subject_index: dict[str, list[KnowledgeTriple]] = field(default_factory=lambda: defaultdict(list))
    kb_predicate_index: dict[str, list[KnowledgeTriple]] = field(default_factory=lambda: defaultdict(list))
    kb_pair_index: dict[tuple[str, str], list[KnowledgeTriple]] = field(default_factory=lambda: defaultdict(list))
    kb_object_index: dict[str, list[KnowledgeTriple]] = field(default_factory=lambda: defaultdict(list))
    kb_subject_aliases: dict[str, str] = field(default_factory=dict)


def _normalize_kb_key(text: Any) -> str:
    """Normalisasi kunci entitas atau subjek KB (lowercase, stripped, hapus spasi berlebih)."""
    if text is None:
        return ""
    s = str(text).strip().lower()
    return re.sub(r"\s+", " ", s)


def _build_kb_indices(
    triples: list[KnowledgeTriple],
) -> tuple[
    dict[str, list[KnowledgeTriple]],
    dict[str, list[KnowledgeTriple]],
    dict[tuple[str, str], list[KnowledgeTriple]],
    dict[str, list[KnowledgeTriple]],
    dict[str, str],
]:
    """Membangun tabel lookup O(1) untuk subjek, predikat, pasangan (subjek, predikat), dan objek."""
    subject_index: dict[str, list[KnowledgeTriple]] = defaultdict(list)
    predicate_index: dict[str, list[KnowledgeTriple]] = defaultdict(list)
    pair_index: dict[tuple[str, str], list[KnowledgeTriple]] = defaultdict(list)
    object_index: dict[str, list[KnowledgeTriple]] = defaultdict(list)
    aliases: dict[str, str] = {}

    for t in triples:
        subj = _normalize_kb_key(t.get("subject", ""))
        pred = str(t.get("predicate", "")).strip().lower()
        obj = _normalize_kb_key(t.get("object", ""))

        if subj:
            subject_index[subj].append(t)
        if pred:
            predicate_index[pred].append(t)
        if subj and pred:
            pair_index[(subj, pred)].append(t)
        if obj:
            object_index[obj].append(t)

        # Petakan relasi kode MK <-> nama MK untuk alias
        if pred == "course_code" and subj and obj:
            aliases[obj] = subj
            aliases[subj] = obj
        elif pred == "course_name" and subj and obj:
            aliases[obj] = subj
            aliases[subj] = obj

    return subject_index, predicate_index, pair_index, object_index, aliases


def build_index(
    passages: list[PassageRecord],
    method: Literal["bm25", "tfidf"] = "bm25",
    triples: list[KnowledgeTriple] | None = None,
    bm25_k1: float = 1.5,
    bm25_b: float = 0.75,
) -> RetrievalIndex:
    """Membangun struktur indeks dari daftar passage korpus (+ opsional indeks knowledge triples).

    Mendukung perbandingan metode retrieval klasik `bm25` (Okapi BM25) dan `tfidf` (cosine similarity)
    serta menyimpan lookup terstruktur untuk cabang Hybrid Knowledge-Based QA (PBA14 Slide 66-75).

    Args:
        passages: Daftar rekaman passage hasil ekstraksi dan preprocessing (passages.jsonl).
        method: Metode pembobotan/perangkingan teks ('bm25' atau 'tfidf').
        triples: Daftar fakta terstruktur (subject, predicate, object) dari knowledge_triples.jsonl.
        bm25_k1: Parameter saturasi term frequency k1 pada BM25 (default: 1.5).
        bm25_b: Parameter normalisasi panjang dokumen b pada BM25 (default: 0.75).

    Returns:
        RetrievalIndex: Objek indeks terpadu siap pakai untuk pencarian passage dan relation retrieval.
    """
    total_docs = len(passages)
    doc_ids: list[str] = []
    doc_tokens: list[list[str]] = []
    doc_lens: list[int] = []

    # Tokenisasi dan pengumpulan token per passage
    for p in passages:
        doc_ids.append(p.get("passage_id", ""))
        # Gunakan kombinasi token asli dan stemmed_text bila ada untuk memperkaya representasi
        toks = p.get("tokens")
        if not toks:
            raw_text = (p.get("stemmed_text") or "") + " " + (p.get("text") or "")
            toks = _tokenize_text(raw_text)
        else:
            # Pastikan lowercase dan sertakan token dari stemmed text
            stemmed = p.get("stemmed_text", "")
            stemmed_toks = _tokenize_text(stemmed) if stemmed else []
            combined = set(str(t).lower() for t in toks) | set(stemmed_toks)
            toks = list(combined)

        doc_tokens.append(toks)
        doc_lens.append(len(toks))

    avg_dl = sum(doc_lens) / total_docs if total_docs > 0 else 0.0

    # Pembangunan Inverted Index dan perhitungan Document Frequency (DF)
    doc_freqs: dict[str, int] = defaultdict(int)
    inverted_index: dict[str, list[tuple[int, int]]] = defaultdict(list)
    vocab_set: set[str] = set()

    for doc_idx, tokens in enumerate(doc_tokens):
        counts = Counter(tokens)
        for term, tf in counts.items():
            doc_freqs[term] += 1
            inverted_index[term].append((doc_idx, tf))
            vocab_set.add(term)

    id_to_term = sorted(list(vocab_set))
    vocab = {term: idx for idx, term in enumerate(id_to_term)}

    # Perhitungan IDF (Inverse Document Frequency)
    idf: dict[str, float] = {}
    if method == "bm25":
        # Robertson-Spärck Jones Okapi BM25 IDF formula dengan smoothing non-negatif
        for term, df in doc_freqs.items():
            idf_val = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
            idf[term] = max(idf_val, 0.01)
    else:
        # Standard smoothed TF-IDF formula: ln((N + 1) / (df + 1)) + 1.0
        for term, df in doc_freqs.items():
            idf[term] = math.log((total_docs + 1.0) / (df + 1.0)) + 1.0

    # Jika metode TF-IDF, pre-compute normalized document vectors untuk cosine similarity efisien
    doc_vectors: list[dict[str, float]] | None = None
    if method == "tfidf":
        doc_vectors = []
        for doc_idx, tokens in enumerate(doc_tokens):
            counts = Counter(tokens)
            doc_len = doc_lens[doc_idx] if doc_lens[doc_idx] > 0 else 1
            vec: dict[str, float] = {}
            norm_sq = 0.0
            for term, count in counts.items():
                tf_val = count / doc_len
                tfidf_val = tf_val * idf.get(term, 0.0)
                vec[term] = tfidf_val
                norm_sq += tfidf_val * tfidf_val

            norm = math.sqrt(norm_sq)
            if norm > 0.0:
                normalized_vec = {t: val / norm for t, val in vec.items()}
            else:
                normalized_vec = vec
            doc_vectors.append(normalized_vec)

    # Indeks KB triples
    kb_subj, kb_pred, kb_pair, kb_obj, kb_aliases = ({}, {}, {}, {}, {})
    if triples:
        kb_subj, kb_pred, kb_pair, kb_obj, kb_aliases = _build_kb_indices(triples)

    return RetrievalIndex(
        method=method,
        passages=passages,
        doc_ids=doc_ids,
        doc_tokens=doc_tokens,
        doc_lens=doc_lens,
        avg_dl=avg_dl,
        total_docs=total_docs,
        vocab=vocab,
        id_to_term=id_to_term,
        doc_freqs=doc_freqs,
        idf=idf,
        inverted_index=inverted_index,
        doc_vectors=doc_vectors,
        bm25_k1=bm25_k1,
        bm25_b=bm25_b,
        triples=triples,
        kb_subject_index=kb_subj,
        kb_predicate_index=kb_pred,
        kb_pair_index=kb_pair,
        kb_object_index=kb_obj,
        kb_subject_aliases=kb_aliases,
    )
