"""Antarmuka web sederhana untuk Sistem QA Kurikulum 2024 TIF UB.

Web ini tidak menambah logika baru. Langkahnya sama dengan qa_pipeline.answer_question,
hanya saja hasil tiap modul ikut dikirim ke halaman supaya cara sistem menemukan
jawaban bisa dilihat (berguna untuk demo).

Jalankan dari folder utama repo:  python main.py --web
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import (  # noqa: E402
    DEFAULT_ANSWER_TOP_M,
    DEFAULT_CORPUS_FILE,
    DEFAULT_EVALUATION_FILE,
    DEFAULT_TOP_K,
    MIN_CONFIDENCE_THRESHOLD,
)
from src.answer_processing.answer_extractor import extract_answer_candidates  # noqa: E402
from src.answer_processing.answer_ranker import rank_answer_candidates, select_best_answer  # noqa: E402
from src.question_processing.question_processor import process_question  # noqa: E402
from src.retrieval.ranking import rank_passages  # noqa: E402
from src.retrieval.retriever import retrieve_passages  # noqa: E402

MAX_QUESTION_LENGTH = 300
EXCERPT_RADIUS = 260  # jumlah karakter di kiri-kanan jawaban yang ikut ditampilkan

# Contoh pertanyaan di halaman awal, diambil dari soal evaluasi supaya pasti bisa dijawab
EXAMPLE_IDS = ["Q17", "Q09", "Q14", "Q03", "Q19", "Q07"]

METHOD_LABELS = {
    "knowledge_base": "Knowledge Base (Fakta Tabel)",
    "ner_tagger": "Answer-Type NER",
    "pattern_regex": "Pattern-Regex",
    "passage_fallback": "Passage Fallback",
}

FEATURE_SPEC = [
    ("answer_type_match", "Kecocokan jenis jawaban", 0.30),
    ("pattern_match", "Kecocokan pola", 0.20),
    ("question_keywords", "Kata kunci pertanyaan", 0.10),
    ("keyword_distance", "Jarak kata kunci", 0.10),
    ("novelty_factor", "Kebaruan (novelty)", 0.05),
    ("apposition_feature", "Aposisi", 0.05),
    ("punctuation_location", "Letak tanda baca", 0.05),
    ("question_term_seq", "Urutan term pertanyaan", 0.05),
    ("retrieval_score", "Skor retrieval (+)", 0.10),
]

PREDICATE_LABELS = {
    "sks": "SKS",
    "total_sks": "total SKS",
    "semester": "semester",
    "prerequisite_of": "prasyarat",
    "min_grade": "nilai minimum",
    "has_practicum": "praktikum",
    "equivalent_to": "setara dengan",
    "learning_path_member": "masuk learning path",
    "learning_path_sks": "SKS di learning path",
    "elective_group_member": "kelompok MK pilihan",
    "course_code": "kode MK",
    "course_name": "nama MK",
    "course_description": "deskripsi",
    "supports_cpl": "mendukung CPL",
    "cpl_description": "isi CPL",
}

INTENT_LABELS = {
    "course_sks": "SKS mata kuliah",
    "course_semester": "semester mata kuliah",
    "course_prerequisite": "prasyarat mata kuliah",
    "course_min_grade": "nilai minimum prasyarat",
    "course_practicum": "ada tidaknya praktikum",
    "course_code": "kode mata kuliah",
    "course_name": "nama mata kuliah",
    "course_description": "deskripsi mata kuliah",
    "course_equivalence": "peralihan nama/kode mata kuliah",
    "course_list_semester": "daftar MK per semester",
    "curriculum_transition": "aturan peralihan kurikulum",
    "learning_path": "isi learning path",
    "learning_path_list": "daftar learning path",
    "total_sks": "jumlah SKS",
    "vision_mission": "visi dan misi",
    "graduate_profile": "profil lulusan",
    "cpl": "capaian pembelajaran lulusan",
    "cpl_code": "kode CPL",
    "abbreviation": "kepanjangan singkatan",
    "mbkm": "Merdeka Belajar (MBKM)",
    "other": "lainnya",
}

ANSWER_TYPE_LABELS = {
    "NUMERIC": "angka",
    "ENTITY": "nama atau daftar",
    "DESCRIPTION": "penjelasan",
    "HUMAN": "orang atau peran",
    "LOCATION": "tempat",
    "ABBREVIATION": "kepanjangan singkatan",
}

CONTENT_LABELS = {"table": "tabel", "text": "teks", "visual": "diagram"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _examples() -> list[str]:
    from src.pipeline.evaluation import load_questions

    try:
        by_id = {q["id"]: q["question"] for q in load_questions(DEFAULT_EVALUATION_FILE)}
    except FileNotFoundError:
        return []
    return [by_id[i] for i in EXAMPLE_IDS if i in by_id]


def _num(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Potongan halaman + stabilo
# ---------------------------------------------------------------------------

def _mark_targets(answer: str) -> list[str]:
    """Teks yang dicari di passage untuk ditandai. Jawaban daftar dipecah per item."""
    plain = re.sub(r"\s*\(\d+ SKS\)", "", answer).strip().rstrip(".")
    parts = [p.strip() for p in re.split(r",\s*(?:dan\s+)?|\s+dan\s+(?=[A-Z])", plain) if p.strip()]
    targets = [answer.strip().rstrip("."), plain] + (parts if len(parts) > 1 else [])
    return [t for t in dict.fromkeys(targets) if len(t) >= 1]


def _segments(text: str, answer: str) -> list[dict[str, Any]]:
    """Potong teks passage jadi bagian biasa & bagian yang distabilo, dipusatkan di sekitar jawaban."""
    spans: list[tuple[int, int]] = []

    def mark(target: str) -> None:
        for m in re.finditer(re.escape(target), text, re.IGNORECASE):
            if not any(s < m.end() and m.start() < e for s, e in spans):
                spans.append((m.start(), m.end()))

    # coba jawaban utuh dulu (dengan/tanpa "(x SKS)"); kalau tidak ada, tandai tiap item daftar
    whole = answer.strip().rstrip(".")
    plain = re.sub(r"\s*\(\d+ SKS\)", "", whole).strip()
    for target in dict.fromkeys([whole, plain]):
        if not spans:
            mark(target)
    if not spans:
        for item in _mark_targets(answer):
            if item not in (whole, plain):
                mark(item)
    if not spans:
        # jawaban hasil pola bisa sedikit beda redaksi dengan buku ("minimum" vs "minimal"),
        # jadi tandai bagian depan jawaban terpanjang yang memang ada di teks
        words = _mark_targets(answer)[-1].split()
        for n in range(len(words) - 1, 1, -1):
            m = re.search(re.escape(" ".join(words[:n])), text, re.IGNORECASE)
            if m:
                spans.append((m.start(), m.end()))
                break
    spans.sort()

    start, end = 0, len(text)
    if spans and len(text) > EXCERPT_RADIUS * 2 + 80:
        start = max(0, spans[0][0] - EXCERPT_RADIUS)
        end = min(len(text), spans[-1][1] + EXCERPT_RADIUS)
    elif len(text) > EXCERPT_RADIUS * 2 + 80:
        end = EXCERPT_RADIUS * 2

    out: list[dict[str, Any]] = []
    if start > 0:
        out.append({"text": "… ", "mark": False})
    cursor = start
    for s, e in spans:
        if s < start or e > end:
            continue
        if s > cursor:
            out.append({"text": text[cursor:s], "mark": False})
        out.append({"text": text[s:e], "mark": True})
        cursor = e
    if cursor < end:
        out.append({"text": text[cursor:end], "mark": False})
    if end < len(text):
        out.append({"text": " …", "mark": False})
    return out


def _excerpt(output: dict[str, Any], passages_by_id: dict[str, dict], passages_by_page: dict[int, list]) -> dict | None:
    """Ambil passage sumber jawaban. Untuk fakta tabel, cari passage di halaman yang sama."""
    source = output.get("source") or {}
    answer = output.get("answer", "")
    passage = passages_by_id.get(source.get("passage_id") or "")

    if passage is None and source.get("pdf_page") is not None:
        candidates = passages_by_page.get(source["pdf_page"], [])
        targets = [t.lower() for t in _mark_targets(answer)]
        title = (source.get("table_title") or "").lower()

        # pilih passage yang memuat item jawaban paling banyak; kalau seri, yang judulnya sama dengan sumber
        def coverage(p: dict) -> tuple[int, bool]:
            text = p["text"].lower()
            return sum(t in text for t in targets), bool(title) and title in text

        best = max(candidates, key=coverage, default=None)
        passage = best if best is not None and coverage(best)[0] > 0 else None

    if passage is None:
        return None
    return {
        "pdf_page": passage.get("pdf_page"),
        "doc_page": passage.get("doc_page"),
        "title": passage.get("table_title") or passage.get("section"),
        "content_type": CONTENT_LABELS.get(passage.get("content_type"), passage.get("content_type")),
        "segments": _segments(passage.get("text", ""), answer),
    }


# ---------------------------------------------------------------------------
# Menjawab + mencatat jejak tiap modul
# ---------------------------------------------------------------------------

def answer_with_trace(question: str, index: Any, passages_by_id: dict, passages_by_page: dict) -> dict[str, Any]:
    t0 = time.perf_counter()
    analysis = process_question(question)
    retrieval = retrieve_passages(analysis, index=index, top_k=DEFAULT_TOP_K)
    passages = rank_passages(retrieval.get("results", []), analysis)
    retrieval["results"] = passages
    candidates = extract_answer_candidates(analysis, retrieval)
    ranked = rank_answer_candidates(analysis, candidates)
    output = select_best_answer(analysis, ranked, min_confidence=MIN_CONFIDENCE_THRESHOLD, top_m=DEFAULT_ANSWER_TOP_M)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    coarse = analysis.get("answer_type_coarse", "")
    source = output.get("source") or {}
    facts: list[dict[str, str]] = []
    if source.get("triple_id"):
        triples = retrieval.get("structured_results", [])
        main = next((t for t in triples if t.get("triple_id") == source["triple_id"]), None)
        if main:
            # jawaban daftar adalah gabungan beberapa triple dengan predikat & objek yang sama
            answer_lower = output["answer"].lower()
            related = [
                t for t in triples
                if t.get("predicate") == main.get("predicate")
                and t.get("object") == main.get("object")
                and str(t.get("subject", "")).lower() in answer_lower
            ] or [main]
            seen = set()
            for t in related:
                key = (str(t.get("subject")), t.get("predicate"), str(t.get("object")))
                if key in seen:
                    continue
                seen.add(key)
                facts.append({
                    "subject": str(t.get("subject")),
                    "relation": PREDICATE_LABELS.get(t.get("predicate"), t.get("predicate")),
                    "value": str(t.get("object")),
                })

    return {
        "question": question,
        "status": output["status"],
        "answer": output["answer"],
        "confidence": output["confidence"],
        "confidence_text": _num(output["confidence"]),
        "threshold": MIN_CONFIDENCE_THRESHOLD,
        "threshold_text": _num(MIN_CONFIDENCE_THRESHOLD),
        "elapsed_ms": elapsed_ms,
        "long_answer": len(output["answer"]) > 90,
        "source": {
            "pdf_page": source.get("pdf_page"),
            "doc_page": source.get("doc_page"),
            "title": source.get("table_title") or source.get("section"),
        } if output["status"] == "answered" else None,
        "facts": facts if output["status"] == "answered" else [],
        "excerpt": _excerpt(output, passages_by_id, passages_by_page) if output["status"] == "answered" else None,
        "trace": {
            "intent": INTENT_LABELS.get(analysis.get("intent"), analysis.get("intent")),
            "answer_type": f"{ANSWER_TYPE_LABELS.get(coarse, coarse.lower())} ({analysis.get('answer_type')})",
            "focus": analysis.get("focus"),
            "entities": [e.get("value") for e in analysis.get("entities", []) if e.get("value")],
            "keywords": analysis.get("query_keywords", [])[:8],
            "facts_found": len(retrieval.get("structured_results", [])),
            "passages": [
                {
                    "pdf_page": p.get("pdf_page"),
                    "doc_page": p.get("doc_page"),
                    "content_type": CONTENT_LABELS.get(p.get("content_type"), p.get("content_type")),
                    "title": p.get("table_title") or p.get("section"),
                    "score": _num(float(p.get("rerank_score", p.get("score", 0.0)))),
                }
                for p in passages[:DEFAULT_TOP_K]
            ],
            "candidates": [
                {
                    "answer": c.get("answer", ""),
                    "method": METHOD_LABELS.get(c.get("extraction_method"), c.get("extraction_method")),
                    "method_key": c.get("extraction_method", ""),
                    "score": _num(c.get("score", 0.0)),
                    "sources": int(c.get("features", {}).get("supporting_sources", 1)),
                    "features": [
                        {
                            "label": label,
                            "weight": _num(weight),
                            "value": _num(float(c.get("features", {}).get(key, 0.0))),
                            "weighted": _num(weight * float(c.get("features", {}).get(key, 0.0))),
                        }
                        for key, label, weight in FEATURE_SPEC
                    ],
                }
                for c in output.get("top_candidates", [])
            ],
            "total_candidates": len(candidates),
        },
    }


def create_app() -> Flask:
    from main import load_index

    if not DEFAULT_CORPUS_FILE.exists():
        raise FileNotFoundError(f"Korpus belum ada di {DEFAULT_CORPUS_FILE}. Jalankan modul preprocessing dulu.")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.json.ensure_ascii = False

    index = load_index()
    passages = _read_jsonl(DEFAULT_CORPUS_FILE)
    passages_by_id = {p["passage_id"]: p for p in passages}
    passages_by_page: dict[int, list] = {}
    for p in passages:
        passages_by_page.setdefault(p.get("pdf_page"), []).append(p)
    examples = _examples()

    @app.get("/")
    def home():
        return render_template("index.html", examples=examples)

    @app.post("/api/tanya")
    def tanya():
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", "")).strip()
        if not question:
            return jsonify({"error": "Tulis pertanyaan dulu, misalnya “Berapa SKS mata kuliah Basis Data?”"}), 400
        if len(question) > MAX_QUESTION_LENGTH:
            return jsonify({"error": f"Pertanyaan terlalu panjang. Batasnya {MAX_QUESTION_LENGTH} karakter."}), 400
        return jsonify(answer_with_trace(question, index, passages_by_id, passages_by_page))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
