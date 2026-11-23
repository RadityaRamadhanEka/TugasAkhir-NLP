"""Ekstraksi kandidat jawaban berbasis Answer-Type NER, Pattern Regex, & Knowledge Base (PBA14 Slide 55-59, 75)."""

import re
from typing import Any

from src.contracts import AnswerCandidate, QuestionAnalysis, RetrievalResult

# Passage yang dipakai untuk mencari kandidat di jalur teks
MAX_PASSAGES = 5
# Jumlah kalimat terbaik yang diambil di jalur passage fallback
MAX_FALLBACK_SENTENCES = 2

# Predikat yang jawabannya berupa daftar (beberapa fakta digabung jadi satu jawaban)
LIST_PREDICATES = {"learning_path_member"}

# Pola angka untuk jalur answer-type NER: predikat -> (pola, format jawaban)
ATTRIBUTE_PATTERNS = {
    "sks": (re.compile(r"(\d+)\s*SKS", re.IGNORECASE), "{} SKS"),
    "total_sks": (re.compile(r"(\d+)\s*SKS", re.IGNORECASE), "{} SKS"),
    "semester": (re.compile(r"Semester\s+(\d+)", re.IGNORECASE), "Semester {}"),
}

# "Mata kuliah CIF65318 Jaringan Saraf Tiruan, ..., Prasyarat: CIF64311 Kecerdasan Artifisial Lanjut (nilai minimal C)"
COURSE_ROW_PATTERN = re.compile(r"Mata kuliah (?P<code>[A-Z]{3}\d{5}) (?P<name>[^,]+),(?P<rest>.*)")
PREREQ_PATTERN = re.compile(r"(?P<course>[A-Z]{3}\d{5} [^(;]+?)\s*\(nilai minim\w*\s+(?P<grade>[A-E])\)")

# "Kurikulum Lama (2020) CIF61011 Kecerdasan Buatan (3 SKS) disetarakan dengan Kurikulum Baru (2024) CIF63110 Kecerdasan Artifisial (2 SKS)"
EQUIVALENCE_PATTERN = re.compile(
    r"Kurikulum Lama \(\d{4}\) (?P<old_code>\S+) (?P<old_name>.+?) \((?P<old_sks>\d+) SKS\) "
    r"disetarakan dengan Kurikulum Baru \(\d{4}\) (?P<new_code>\S+) (?P<new_name>.+?) \((?P<new_sks>\d+) SKS\)"
)

# Pola definisi <QP> adalah <AP> (PBA14 Slide 57-58)
QUOTED_DEFINITION = re.compile(
    r"(?:adalah|yaitu|ialah|merupakan|mengusung\s+[\w\s]{0,30}?)\s*[\"“](?P<answer>[^\"”]+)[\"”]",
    re.IGNORECASE,
)
PLAIN_DEFINITION = re.compile(r"\b(?:adalah|yaitu|ialah|merupakan)\s+(?P<answer>.{10,})$", re.IGNORECASE)

# Kata sambung yang boleh diselipkan di kepanjangan singkatan tanpa ikut jadi huruf depan
ABBREVIATION_SKIP_WORDS = {"dan", "atau", "di", "ke", "dari", "untuk", "&", "of", "and", "the"}

SENTENCE_SPLIT = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"”]))\s+(?=[A-Z0-9\"“])")
WORD = re.compile(r"[a-z0-9_]+")


# ---------------------------------------------------------------------------
# Fungsi bantu
# ---------------------------------------------------------------------------

def _words(text: Any) -> list[str]:
    return WORD.findall(str(text).lower())


def _keyword_overlap(question_analysis: QuestionAnalysis, context: str) -> float:
    """Proporsi keyword pertanyaan yang muncul di konteks kandidat (fitur question_keywords)."""
    keywords = [k.lower() for k in question_analysis.get("query_keywords", []) if k]
    if not keywords:
        return 0.0
    context_lower = context.lower()
    found = sum(1 for k in keywords if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", context_lower))
    return found / len(keywords)


def _longest_question_sequence(question_analysis: QuestionAnalysis, context: str) -> float:
    """Panjang urutan kata pertanyaan terpanjang yang muncul berurutan di konteks, dinormalisasi."""
    q_words = _words(question_analysis.get("original_question", ""))
    c_words = _words(context)
    if not q_words or not c_words:
        return 0.0
    longest = 0
    for i in range(len(c_words)):
        for j in range(len(q_words)):
            length = 0
            while (i + length < len(c_words) and j + length < len(q_words)
                   and c_words[i + length] == q_words[j + length]):
                length += 1
            longest = max(longest, length)
    return min(longest / 4, 1.0)  # 4 kata berurutan sudah dianggap sangat kuat


def _novelty(question_analysis: QuestionAnalysis, answer: str) -> float:
    """Proporsi kata jawaban yang bukan pengulangan kata di pertanyaan (fitur novelty_factor)."""
    answer_words = _words(answer)
    if not answer_words:
        return 0.0
    question_words = set(_words(question_analysis.get("original_question", "")))
    return sum(1 for w in answer_words if w not in question_words) / len(answer_words)


def _followed_by_punctuation(context: str, end: int) -> float:
    rest = context[end:].lstrip(" ")
    return 1.0 if not rest or rest[0] in ",.;)\"”:" else 0.0


def _build_features(
    question_analysis: QuestionAnalysis,
    answer: str,
    context: str,
    *,
    answer_type_match: float,
    pattern_match: float,
    keyword_distance: float,
    apposition: float = 0.0,
    punctuation: float = 0.0,
    retrieval_score: float = 0.0,
) -> dict[str, float]:
    """Menyusun 8 fitur PBA14 Slide 62 + skor retrieval untuk satu kandidat."""
    return {
        "answer_type_match": answer_type_match,
        "pattern_match": pattern_match,
        "question_keywords": round(_keyword_overlap(question_analysis, context), 4),
        "keyword_distance": round(keyword_distance, 4),
        "novelty_factor": round(_novelty(question_analysis, answer), 4),
        "apposition_feature": apposition,
        "punctuation_location": punctuation,
        "question_term_seq": round(_longest_question_sequence(question_analysis, context), 4),
        "retrieval_score": round(min(max(retrieval_score, 0.0), 1.0), 4),
    }


def _source_from_passage(passage: dict[str, Any]) -> dict[str, Any]:
    return {
        "passage_id": passage.get("passage_id"),
        "triple_id": None,
        "pdf_page": passage.get("pdf_page"),
        "doc_page": passage.get("doc_page"),
        "page": passage.get("pdf_page"),
        "section": passage.get("section"),
        "table_title": passage.get("table_title"),
        "source_type": passage.get("content_type", "text"),
    }


def _source_from_triple(triple: dict[str, Any]) -> dict[str, Any]:
    return {
        "passage_id": None,
        "triple_id": triple.get("triple_id"),
        "pdf_page": triple.get("pdf_page"),
        "doc_page": triple.get("doc_page"),
        "page": triple.get("pdf_page"),
        "section": triple.get("section"),
        "table_title": triple.get("table_title"),
        "source_type": "knowledge_base",
    }


def _subject_names(question_analysis: QuestionAnalysis) -> list[str]:
    """Nama/kode subjek yang ditanyakan: dari relasi dan entitas hasil Modul 3.

    Nama asli di pertanyaan ('value') ikut disimpan, karena untuk soal peralihan
    kurikulum justru nama lama itulah yang dicari.
    """
    names: list[str] = []
    for relation in question_analysis.get("relations", []):
        if relation.get("subject"):
            names.append(str(relation["subject"]))
    for entity in question_analysis.get("entities", []):
        if entity.get("type") in {"course_name", "course_code"}:
            names += [str(entity.get("value", "")), str(entity.get("normalized_value", ""))]
    unique = {n.strip().lower(): n.strip() for n in names if n and n.strip()}
    return sorted(unique.values(), key=len, reverse=True)


def _wanted_predicates(question_analysis: QuestionAnalysis) -> set[str]:
    return {r["predicate"] for r in question_analysis.get("relations", []) if r.get("predicate")}


def _asks_prerequisite(question_analysis: QuestionAnalysis) -> bool:
    return "prasyarat" in question_analysis.get("normalized_question", question_analysis.get("original_question", "")).lower()


def _join_list(items: list[str]) -> str:
    if len(items) <= 2:
        return " dan ".join(items)
    return ", ".join(items[:-1]) + ", dan " + items[-1]


def _add_sks_from_passages(items: list[str], passages: list[dict[str, Any]]) -> list[str]:
    """Kalau pertanyaan minta SKS, cari 'Nama MK (N SKS)' di passage untuk tiap item daftar."""
    completed = []
    for item in items:
        sks = None
        for passage in passages:
            found = re.search(rf"{re.escape(item)}\s*\((\d+)\s*SKS\)", passage.get("text", ""), re.IGNORECASE)
            if found:
                sks = found.group(1)
                break
        completed.append(f"{item} ({sks} SKS)" if sks else item)
    return completed


def _expand_abbreviation(text: str, abbreviation: str) -> str | None:
    """Cari bentuk 'Kepanjangan (SINGKATAN)': kata-kata sebelum kurung yang huruf depannya = singkatan."""
    letters = abbreviation.upper()
    for match in re.finditer(rf"\(\s*{re.escape(abbreviation)}\s*\)", text, re.IGNORECASE):
        words = text[:match.start()].split()
        picked: list[str] = []
        initials = ""
        for word in reversed(words):
            clean = word.strip(",.;:\"“”")
            if not clean:
                break
            if clean.lower() in ABBREVIATION_SKIP_WORDS and picked:
                picked.insert(0, clean)
                continue
            initials = clean[0].upper() + initials
            picked.insert(0, clean)
            if not letters.endswith(initials):
                break
            if initials == letters:
                return " ".join(picked)
    return None


def _make_candidate(answer: str, granularity: str, method: str, features: dict, source: dict) -> AnswerCandidate:
    return {
        "answer": answer.strip(),
        "answer_granularity": granularity,
        "score": 0.0,  # diisi oleh answer_ranker
        "extraction_method": method,
        "features": features,
        "source": source,
    }


# ---------------------------------------------------------------------------
# Jalur 1: Knowledge Base (fakta tabel dari Anggota 2, diambil Anggota 4)
# ---------------------------------------------------------------------------

def _format_triple_answer(triple: dict[str, Any], subject_label: str) -> str:
    predicate, value = triple.get("predicate"), triple.get("object")
    if predicate in {"sks", "total_sks"}:
        return f"{value} SKS"
    if predicate == "semester":
        return f"Semester {value}"
    if predicate == "min_grade":
        return f"nilai minimum {value}"
    if predicate == "has_practicum":
        return f"Ya, {subject_label} memiliki praktikum" if value else f"Tidak, {subject_label} tidak memiliki praktikum"
    return str(value)


def extract_from_knowledge_base(
    question_analysis: QuestionAnalysis,
    triples: list[dict[str, Any]],
    passages: list[dict[str, Any]] | None = None,
) -> list[AnswerCandidate]:
    """Mengubah fakta tabel menjadi kandidat. Hanya fakta dengan predikat yang ditanyakan yang dipakai."""
    wanted = _wanted_predicates(question_analysis)
    relevant = [t for t in triples if t.get("predicate") in wanted]
    if not relevant:
        return []

    subject_label = next(iter(_subject_names(question_analysis)), "mata kuliah tersebut")
    asks_prereq = _asks_prerequisite(question_analysis)
    candidates: list[AnswerCandidate] = []

    # Fakta daftar (mis. anggota learning path) digabung per objek jadi satu jawaban
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    singles: list[dict[str, Any]] = []
    for triple in relevant:
        if triple["predicate"] in LIST_PREDICATES:
            groups.setdefault((triple["predicate"], str(triple["object"])), []).append(triple)
        else:
            singles.append(triple)

    for (_, group_name), members in groups.items():
        items = list(dict.fromkeys(str(t["subject"]) for t in members))
        if "learning_path_sks" in wanted or "sks" in _words(question_analysis.get("original_question", "")):
            items = _add_sks_from_passages(items, passages or [])
        answer = _join_list(items)
        context = f"{group_name}: {answer}"
        features = _build_features(
            question_analysis, answer, context,
            answer_type_match=1.0, pattern_match=1.0, keyword_distance=1.0,
            punctuation=1.0, retrieval_score=1.0,
        )
        candidates.append(_make_candidate(answer, "short", "knowledge_base", features, _source_from_triple(members[0])))

    # Prasyarat + nilai minimum dari subjek yang sama digabung jadi satu kalimat
    by_subject: dict[str, dict[str, dict[str, Any]]] = {}
    for triple in singles:
        by_subject.setdefault(str(triple["subject"]), {})[triple["predicate"]] = triple

    for subject, facts in by_subject.items():
        for predicate, triple in facts.items():
            if predicate == "min_grade" and "prerequisite_of" in facts:
                continue  # sudah ikut digabung di bawah
            if predicate == "prerequisite_of" and "min_grade" in facts:
                answer = f"{triple['object']} dengan nilai minimum {facts['min_grade']['object']}"
            else:
                answer = _format_triple_answer(triple, subject_label)

            # Soal prasyarat tapi faktanya cuma nilai, tanpa nama MK -> jawaban belum lengkap
            complete = not (asks_prereq and predicate == "min_grade")
            context = f"{subject} {predicate} {triple['object']} {triple.get('table_title') or ''}"
            features = _build_features(
                question_analysis, answer, context,
                answer_type_match=1.0 if complete else 0.5,
                pattern_match=1.0, keyword_distance=1.0,
                punctuation=1.0, retrieval_score=1.0,
            )
            candidates.append(_make_candidate(answer, "exact", "knowledge_base", features, _source_from_triple(triple)))

    return candidates


# ---------------------------------------------------------------------------
# Jalur 2: Answer-type NER — angka di dekat nama subjek di passage
# ---------------------------------------------------------------------------

def extract_attribute_values(
    question_analysis: QuestionAnalysis,
    passages: list[dict[str, Any]],
) -> list[AnswerCandidate]:
    """Mencari angka (SKS/semester) yang letaknya tepat setelah nama subjek di passage."""
    patterns = [ATTRIBUTE_PATTERNS[p] for p in _wanted_predicates(question_analysis) if p in ATTRIBUTE_PATTERNS]
    names = _subject_names(question_analysis)
    if not patterns or not names:
        return []

    candidates: list[AnswerCandidate] = []
    for passage in passages:
        text = passage.get("text", "")
        for name in names:
            # Nama harus berakhir di situ (diikuti koma/kurung/titik), supaya
            # "Kecerdasan Artifisial" tidak cocok dengan "Kecerdasan Artifisial Lanjut"
            for match in re.finditer(rf"(?<!\w){re.escape(name)}(?=\s*[,(.;:)]|$)", text, re.IGNORECASE):
                if "prasyarat" in text[max(0, match.start() - 40):match.start()].lower():
                    continue  # ini nama MK prasyarat, bukan MK yang ditanya
                window = re.split(r"Prasyarat", text[match.end():match.end() + 80])[0]
                for pattern, template in patterns:
                    found = pattern.search(window)
                    if not found:
                        continue
                    answer = template.format(found.group(1))
                    words_between = len(_words(window[:found.start()]))
                    features = _build_features(
                        question_analysis, answer, text,
                        answer_type_match=1.0, pattern_match=1.0,
                        keyword_distance=1.0 / (1 + words_between),
                        apposition=1.0 if window.lstrip().startswith("(") else 0.0,
                        punctuation=_followed_by_punctuation(window, found.end()),
                        retrieval_score=passage.get("rerank_score", passage.get("score", 0.0)),
                    )
                    candidates.append(_make_candidate(answer, "exact", "ner_tagger", features, _source_from_passage(passage)))
    return candidates


# ---------------------------------------------------------------------------
# Jalur 3: Pattern regex — prasyarat, peralihan kurikulum, definisi
# ---------------------------------------------------------------------------

def extract_by_patterns(
    question_analysis: QuestionAnalysis,
    passages: list[dict[str, Any]],
) -> list[AnswerCandidate]:
    names_lower = {n.lower() for n in _subject_names(question_analysis)}
    intent = question_analysis.get("intent", "")
    predicates = _wanted_predicates(question_analysis)
    candidates: list[AnswerCandidate] = []

    for passage in passages:
        text = passage.get("text", "")
        retrieval_score = passage.get("rerank_score", passage.get("score", 0.0))
        source = _source_from_passage(passage)

        # a. Prasyarat: "Mata kuliah X, ..., Prasyarat: Y (nilai minimal C)"
        if _asks_prerequisite(question_analysis) or {"prerequisite_of", "min_grade"} & predicates:
            row = COURSE_ROW_PATTERN.search(text)
            if row and (row["name"].strip().lower() in names_lower or row["code"].lower() in names_lower):
                prereq_part = row["rest"].split("Prasyarat:", 1)[-1] if "Prasyarat:" in row["rest"] else ""
                prereqs = [f"{m['course'].strip()} dengan nilai minimum {m['grade']}" for m in PREREQ_PATTERN.finditer(prereq_part)]
                if prereqs:
                    answer = " dan ".join(prereqs)
                    features = _build_features(
                        question_analysis, answer, text,
                        answer_type_match=1.0, pattern_match=1.0, keyword_distance=1.0,
                        punctuation=1.0, retrieval_score=retrieval_score,
                    )
                    candidates.append(_make_candidate(answer, "short", "pattern_regex", features, source))

        # b. Peralihan kurikulum: nama lama -> nama baru
        if intent == "course_equivalence" or "equivalent_to" in predicates:
            for m in EQUIVALENCE_PATTERN.finditer(text):
                if m["old_name"].strip().lower() in names_lower or m["old_code"].lower() in names_lower:
                    answer = f"{m['new_code']} {m['new_name'].strip()} ({m['new_sks']} SKS)"
                    features = _build_features(
                        question_analysis, answer, text,
                        answer_type_match=1.0, pattern_match=1.0, keyword_distance=1.0,
                        apposition=1.0, punctuation=1.0, retrieval_score=retrieval_score,
                    )
                    candidates.append(_make_candidate(answer, "exact", "pattern_regex", features, source))

        # c. Kepanjangan singkatan: "Merdeka Belajar Kampus Merdeka (MBKM)"
        if question_analysis.get("answer_type_coarse") == "ABBREVIATION":
            abbreviations = [e.get("normalized_value") or e.get("value") for e in question_analysis.get("entities", [])
                             if e.get("type") == "abbreviation"]
            for abbreviation in filter(None, abbreviations):
                expansion = _expand_abbreviation(text, abbreviation)
                if expansion:
                    features = _build_features(
                        question_analysis, expansion, text,
                        answer_type_match=1.0, pattern_match=1.0, keyword_distance=1.0,
                        apposition=1.0, punctuation=1.0, retrieval_score=retrieval_score,
                    )
                    candidates.append(_make_candidate(expansion, "exact", "pattern_regex", features, source))

        # d. Definisi: kalimat yang memuat fokus pertanyaan + "adalah/yaitu/..."
        if question_analysis.get("answer_type_coarse") not in {"NUMERIC", "ABBREVIATION"}:
            focus_words = set(_words(question_analysis.get("focus") or ""))
            for sentence in SENTENCE_SPLIT.split(text):
                sentence_words = set(_words(sentence))
                if not focus_words or len(focus_words & sentence_words) < max(1, len(focus_words) / 2):
                    continue
                m = QUOTED_DEFINITION.search(sentence) or PLAIN_DEFINITION.search(sentence)
                if not m:
                    continue
                answer = m["answer"].strip().rstrip(".")
                features = _build_features(
                    question_analysis, answer, sentence,
                    answer_type_match=1.0, pattern_match=1.0,
                    keyword_distance=len(focus_words & sentence_words) / len(focus_words),
                    punctuation=1.0, retrieval_score=retrieval_score,
                )
                candidates.append(_make_candidate(answer, "short", "pattern_regex", features, source))

    return candidates


# ---------------------------------------------------------------------------
# Jalur 4: Passage fallback — kalimat paling relevan
# ---------------------------------------------------------------------------

def extract_fallback_sentences(
    question_analysis: QuestionAnalysis,
    passages: list[dict[str, Any]],
) -> list[AnswerCandidate]:
    """Kalau tidak ada pola yang cocok, ambil kalimat dengan keyword pertanyaan terbanyak.

    Jawaban penjelasan sering terbagi dua kalimat berurutan ("... Sementara itu, ..."),
    jadi pasangan dua kalimat ikut dinilai. Pasangan diberi potongan kecil supaya
    tidak selalu menang hanya karena lebih panjang.
    """
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for passage in passages:
        sentences = [s.strip() for s in SENTENCE_SPLIT.split(passage.get("text", "")) if len(_words(s)) >= 5]
        for i, sentence in enumerate(sentences):
            overlap = _keyword_overlap(question_analysis, sentence)
            if overlap > 0:
                scored.append((overlap, sentence, passage))
            if i + 1 < len(sentences) and overlap > 0 and _keyword_overlap(question_analysis, sentences[i + 1]) > 0:
                pair = f"{sentence} {sentences[i + 1]}"
                scored.append((_keyword_overlap(question_analysis, pair) - 0.05, pair, passage))

    scored.sort(key=lambda item: item[0], reverse=True)
    is_description = question_analysis.get("answer_type_coarse") == "DESCRIPTION"
    candidates: list[AnswerCandidate] = []
    for overlap, sentence, passage in scored[:MAX_FALLBACK_SENTENCES]:
        features = _build_features(
            question_analysis, sentence, sentence,
            answer_type_match=1.0 if is_description else 0.0,
            pattern_match=0.0, keyword_distance=overlap,
            punctuation=1.0,
            retrieval_score=passage.get("rerank_score", passage.get("score", 0.0)),
        )
        candidates.append(_make_candidate(sentence, "long", "passage_fallback", features, _source_from_passage(passage)))
    return candidates


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------

def extract_answer_candidates(
    question_analysis: QuestionAnalysis,
    retrieval_result: RetrievalResult,
) -> list[AnswerCandidate]:
    """Mengekstrak kandidat jawaban dari passage dan knowledge triples terpilih.

    Menggabungkan tiga jalur ekstraksi sesuai materi PBA14:
    1. Answer-type Named Entity Tagger (Slide 55-56) untuk jawaban factoid (NUMERIC/ENTITY/HUMAN)
    2. Answer-type Pattern Extraction `<QP>/<AP>` (Slide 57-58) untuk definisi, prasyarat, & aturan
    3. Structured Knowledge Base Extraction (Slide 66-75) dari `retrieval_result["structured_results"]`
    Ditambah passage fallback (kalimat paling relevan) bila ketiga jalur tidak menemukan apa pun
    yang meyakinkan. Skor akhir tiap kandidat dihitung di answer_ranker.
    """
    passages = list(retrieval_result.get("results", []))[:MAX_PASSAGES]
    triples = list(retrieval_result.get("structured_results", []))

    candidates: list[AnswerCandidate] = []
    candidates += extract_from_knowledge_base(question_analysis, triples, passages)
    candidates += extract_attribute_values(question_analysis, passages)
    candidates += extract_by_patterns(question_analysis, passages)
    candidates += extract_fallback_sentences(question_analysis, passages)
    return candidates
