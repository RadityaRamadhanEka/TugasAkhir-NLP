"""Ekstraksi entitas, relasi, dan Focus Detection / Question Headword (PBA14 Slide 35-37, 44)."""

import re
from functools import lru_cache

from src.contracts import ExtractedEntity, ExtractedRelation
from src.question_processing.query_formulator import pos_tag_question
from src.question_processing.resources import load_course_lexicon, load_domain_lexicon
from src.question_processing.text_utils import normalize_question

_COURSE_CODE_RE = re.compile(r"\b([a-z]{3}\d{5}(?:-\d)?)\b")
_CPL_CODE_RE = re.compile(r"\b(?:if_)?cpl[_\s-]?(s|p|ku|kk|kp)\s?(\d)\b")
_SEMESTER_RE = re.compile(
    r"\bsemester\s+(antara\s+[ab]|ganjil/genap|antara|ganjil|genap|[1-8]|viii|vii|vi|iv|iii|ii|i|v|satu|dua|tiga|empat|lima|enam|tujuh|delapan)\b"
)
_SKS_VALUE_RE = re.compile(r"\b(\d+)\s*sks\b")
_GRADE_RE = re.compile(r"\bnilai\s+(?:(?:minimal|minimum)\s+)?([a-e])\b")
_YEAR_RE = re.compile(r"\b(2020|2024)\b")

_SEMESTER_MAP = {
    "1": "1",
    "i": "1",
    "satu": "1",
    "2": "2",
    "ii": "2",
    "dua": "2",
    "3": "3",
    "iii": "3",
    "tiga": "3",
    "4": "4",
    "iv": "4",
    "empat": "4",
    "5": "5",
    "v": "5",
    "lima": "5",
    "6": "6",
    "vi": "6",
    "enam": "6",
    "7": "7",
    "vii": "7",
    "tujuh": "7",
    "8": "8",
    "viii": "8",
    "delapan": "8",
    "antara": "antara",
    "antara a": "Semester Antara (A)",
    "antara b": "Semester Antara (B)",
    "ganjil": "Ganjil",
    "genap": "Genap",
    "ganjil/genap": "Ganjil/Genap",
}

_INTENT_TO_PREDICATE: dict[str, str | None] = {
    "course_prerequisite": "prerequisite_of",
    "course_min_grade": "min_grade",
    "course_sks": "sks",
    "course_semester": "semester",
    "course_code": "course_code",
    "course_name": "course_name",
    "course_practicum": "has_practicum",
    "course_list_semester": "semester",
    "elective_group": "elective_group_member",
    "learning_path": "learning_path_member",
    "learning_path_list": None,
    "total_sks": "total_sks",
    "curriculum_transition": None,
    "course_equivalence": "equivalent_to",
    "cpl": "cpl_description",
    "graduate_profile": None,
    "vision_mission": None,
    "course_description": "course_description",
    "mbkm": None,
    "abbreviation": None,
    "other": None,
}

_FOCUS_STOPWORDS = {
    "saja",
    "yang",
    "itu",
    "ini",
    "dari",
    "untuk",
    "pada",
    "di",
    "ke",
    "tentang",
    "mengenai",
    "dalam",
    "dan",
    "atau",
    "adalah",
    "merupakan",
    "bagi",
}
_YES_NO_DOMAIN_FOCUS = ("praktikum", "prasyarat", "syarat", "sks", "wajib", "pilihan")


@lru_cache(maxsize=1)
def _compiled_gazetteer() -> tuple[tuple[re.Pattern[str], str, str], ...]:
    """Menyusun pasangan `(pattern, entity_type, canonical_value)` terurut dari terpanjang."""
    entries: list[tuple[str, str, str]] = []
    domain_lex = load_domain_lexicon()
    course_lex = load_course_lexicon()

    for canon, aliases in domain_lex["learning_paths"].items():
        entries.append((canon.lower(), "learning_path", canon))
        for alias in aliases:
            entries.append((alias.lower(), "learning_path", canon))

    for canon, aliases in domain_lex["elective_groups"].items():
        entries.append((canon.lower(), "elective_group", canon))
        for alias in aliases:
            entries.append((alias.lower(), "elective_group", canon))

    seen_course_surface: set[str] = set()
    for info in course_lex["courses_2024"].values():
        canon = info["name"]
        low = canon.lower()
        seen_course_surface.add(low)
        entries.append((low, "course_name", canon))
        for alias in info.get("aliases", []):
            al = alias.lower()
            seen_course_surface.add(al)
            entries.append((al, "course_name", canon))

    for info in course_lex["courses_2020"].values():
        low = info["name"].lower()
        if low not in seen_course_surface:
            entries.append((low, "course_name", info["name"]))

    for canon, aliases in domain_lex.get("knowledge_areas", {}).items():
        entries.append((canon.lower(), "knowledge_area", canon))
        for alias in aliases:
            entries.append((alias.lower(), "knowledge_area", canon))

    for abbr in domain_lex["abbreviations"]:
        entries.append((abbr.lower(), "abbreviation", abbr.upper()))

    # Panjang terpanjang diutamakan; jika sama panjang, learning_path/elective_group/course_name > knowledge_area > abbreviation
    priority = {
        "learning_path": 0,
        "elective_group": 1,
        "course_name": 2,
        "knowledge_area": 3,
        "abbreviation": 4,
    }
    dedup: dict[str, tuple[str, str]] = {}
    for surface, etype, canon in sorted(entries, key=lambda x: (-len(x[0]), priority[x[1]])):
        if surface not in dedup:
            dedup[surface] = (etype, canon)

    compiled: list[tuple[re.Pattern[str], str, str]] = []
    for surface, (etype, canon) in sorted(dedup.items(), key=lambda x: -len(x[0])):
        pat = re.compile(rf"(?<!\w){re.escape(surface)}(?!\w)")
        compiled.append((pat, etype, canon))
    return tuple(compiled)


def _overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    return any(not (end <= s or start >= e) for s, e in occupied)


def _record_match(
    hits: list[tuple[int, ExtractedEntity]],
    occupied: list[tuple[int, int]],
    start: int,
    end: int,
    etype: str,
    value: str,
    normalized: str,
) -> None:
    if _overlaps(start, end, occupied):
        return
    occupied.append((start, end))
    hits.append((start, {"type": etype, "value": value, "normalized_value": normalized}))


def extract_entities(question: str) -> list[ExtractedEntity]:
    """Mengekstrak entitas domain kurikulum (kode MK, nama MK, semester, SKS, learning path, CPL)."""
    norm = normalize_question(question)
    hits: list[tuple[int, ExtractedEntity]] = []
    occupied: list[tuple[int, int]] = []

    for m in _COURSE_CODE_RE.finditer(norm):
        _record_match(hits, occupied, m.start(), m.end(), "course_code", m.group(1), m.group(1).upper())

    for m in _CPL_CODE_RE.finditer(norm):
        canon = f"IF_CPL_{m.group(1).upper()}{m.group(2)}"
        _record_match(hits, occupied, m.start(), m.end(), "cpl_code", m.group(0), canon)

    for m in _SEMESTER_RE.finditer(norm):
        _record_match(
            hits,
            occupied,
            m.start(),
            m.end(),
            "semester",
            m.group(0),
            _SEMESTER_MAP[m.group(1)],
        )

    for m in _SKS_VALUE_RE.finditer(norm):
        _record_match(hits, occupied, m.start(), m.end(), "sks_value", m.group(0), m.group(1))

    for m in _GRADE_RE.finditer(norm):
        _record_match(hits, occupied, m.start(), m.end(), "grade", m.group(0), m.group(1).upper())

    for m in _YEAR_RE.finditer(norm):
        _record_match(hits, occupied, m.start(), m.end(), "curriculum_year", m.group(1), m.group(1))

    for pat, etype, canon in _compiled_gazetteer():
        for m in pat.finditer(norm):
            _record_match(hits, occupied, m.start(), m.end(), etype, m.group(0), canon)

    hits.sort(key=lambda item: item[0])
    return [ent for _, ent in hits]


def _collect_headword_np(
    tagged: list[tuple[str, str]],
    start_idx: int,
    step: int,
) -> list[str]:
    """Mengumpulkan frasa nominal `(NN|JJ)+` dari `start_idx` ke arah `step` (+1 atau -1)."""
    allowed_tags = {"NN", "JJ"} if step == 1 else {"NN", "JJ", "FW"}
    collected: list[str] = []
    i = start_idx
    while 0 <= i < len(tagged):
        tok, tag = tagged[i]
        low = tok.lower()
        if low in _FOCUS_STOPWORDS:
            if not collected and step == 1:
                i += step
                continue
            break
        if tag in allowed_tags:
            # Jika sudah ada headword seperti "sks" lalu bertemu "mata kuliah <MK>", hentikan
            if (
                step == 1
                and collected
                and low == "mata"
                and i + 1 < len(tagged)
                and tagged[i + 1][0].lower() == "kuliah"
            ):
                break
            collected.append(low)
            i += step
        else:
            break
    return list(reversed(collected)) if step == -1 else collected


def detect_focus(
    tokens: list[str],
    pos_tags: list[tuple[str, str]] | None = None,
) -> str | None:
    """Mendeteksi question focus / headword (frasa NP setelah/sebelum wh-word yang digantikan jawaban)."""
    if not tokens:
        return None
    tagged = pos_tags if pos_tags is not None else pos_tag_question(tokens)
    domain_lex = load_domain_lexicon()
    command_words = set(domain_lex["command_words"])

    # Pola 1 & 2: Pertanyaan mengandung kata tanya WH
    wh_indices = [
        i for i, (tok, tag) in enumerate(tagged) if tag == "WH" and tok.lower() not in _FOCUS_STOPWORDS
    ]
    if wh_indices:
        wh_idx = wh_indices[0]
        head_tok = tagged[wh_idx][0].lower()
        # Pola 4: Pertanyaan ya/tidak ("apakah...", "adakah...")
        if wh_idx == 0 and head_tok in {"apakah", "adakah", "benarkah", "wajibkah", "bisakah"}:
            for tok, _ in tagged[1:]:
                if tok.lower() in _YES_NO_DOMAIN_FOCUS:
                    return tok.lower()
            return None

        # Pola 2: NP + WH (mis. "Mata kuliah apa saja...", "... semester berapa")
        if wh_idx > 0:
            before = _collect_headword_np(tagged, wh_idx - 1, -1)
            if before:
                return " ".join(before)

        # Pola 1: WH + NP (mis. "Apa prasyarat...", "Berapa SKS...")
        after = _collect_headword_np(tagged, wh_idx + 1, 1)
        if after:
            return " ".join(after)
        return None

    # Pola 3: Kalimat perintah atau permintaan tidak langsung ("Sebutkan...", "Tolong jelaskan...")
    cmd_indices = [i for i, (tok, _) in enumerate(tagged[:3]) if tok.lower() in command_words]
    if cmd_indices:
        after_cmd = _collect_headword_np(tagged, cmd_indices[-1] + 1, 1)
        if after_cmd:
            return " ".join(after_cmd)

    return None


def _infer_predicate_from_text(norm: str, entities: list[ExtractedEntity]) -> str | None:
    etypes = {e["type"] for e in entities}
    if re.search(r"\bnilai\s+(?:min|minimum|minimal)\b", norm):
        return "min_grade"
    if re.search(r"\b(?:prasyarat|syarat\s+(?:ambil|mengambil|lulus))\b", norm):
        return "prerequisite_of"
    if re.search(r"\b(?:setara|ekuivalen|pengganti|penyetaraan)\b", norm):
        return "equivalent_to"
    if re.search(r"\b(?:praktikum|praktik)\b", norm):
        return "has_practicum"
    if re.search(r"\bkode\s+(?:mk|mata\s+kuliah)\b", norm):
        return "course_code"
    if "learning_path" in etypes and not re.search(r"\bapa\s+saja\s+learning\s+path\b", norm):
        return "learning_path_member"
    if "elective_group" in etypes:
        return "elective_group_member"
    if re.search(r"\btotal\s+sks\b", norm):
        return "total_sks"
    if re.search(r"\b(?:sks|kredit)\b", norm):
        return "sks"
    if "semester" in etypes or re.search(r"\bsemester\b", norm):
        return "semester"
    if "knowledge_area" in etypes:
        return "supports_cpl"
    if "cpl_code" in etypes:
        if re.search(r"\b(?:bahan\s+kajian|mendukung|didukung|matriks|pemetaan)\b", norm):
            return "supports_cpl"
        return "cpl_description"
    if re.search(r"\b(?:dipelajari|silabus|deskripsi|materi|membahas)\b", norm) and (
        "course_name" in etypes or "course_code" in etypes
    ):
        return "course_description"
    return None


def extract_relations(
    question: str,
    entities: list[ExtractedEntity],
    pos_tags: list[tuple[str, str]] | None = None,
    intent: str | None = None,
) -> list[ExtractedRelation]:
    """Mengekstrak relasi semantik dari pertanyaan (mis. `prasyarat(MK, ?x)`, `sks(MK, ?x)`)."""
    del pos_tags  # dipertahankan untuk kompatibilitas tanda tangan kontrak
    norm = normalize_question(question)

    if intent is not None:
        predicate = _INTENT_TO_PREDICATE.get(intent)
    else:
        predicate = _infer_predicate_from_text(norm, entities)

    if not predicate:
        return []

    course_target = next(
        (e["normalized_value"] for e in entities if e["type"] in {"course_name", "course_code"}),
        None,
    )
    code_target = next(
        (e["normalized_value"] for e in entities if e["type"] == "course_code"),
        None,
    )
    semester_target = next(
        (e["normalized_value"] for e in entities if e["type"] == "semester"),
        None,
    )
    lp_target = next(
        (e["normalized_value"] for e in entities if e["type"] == "learning_path"),
        None,
    )
    eg_target = next(
        (e["normalized_value"] for e in entities if e["type"] == "elective_group"),
        None,
    )
    cpl_target = next(
        (e["normalized_value"] for e in entities if e["type"] == "cpl_code"),
        None,
    )
    ka_target = next(
        (e["normalized_value"] for e in entities if e["type"] == "knowledge_area"),
        None,
    )

    if predicate == "learning_path_member" and lp_target:
        rels: list[ExtractedRelation] = [
            {"predicate": "learning_path_member", "subject": None, "object": lp_target}
        ]
        if re.search(r"\b(?:sks|satuan\s+kredit\s+semester)\b", norm):
            rels.append({"predicate": "learning_path_sks", "subject": course_target, "object": None})
        return rels
    if predicate == "elective_group_member" and eg_target:
        return [{"predicate": predicate, "subject": None, "object": eg_target}]
    if predicate == "semester":
        if course_target:
            return [{"predicate": "semester", "subject": course_target, "object": None}]
        if semester_target:
            return [{"predicate": "semester", "subject": None, "object": semester_target}]
        return []
    if predicate in {"cpl_description", "supports_cpl"}:
        if ka_target:
            return [{"predicate": "supports_cpl", "subject": ka_target, "object": None}]
        if cpl_target and re.search(r"\b(?:bahan\s+kajian|mendukung|didukung|matriks|pemetaan)\b", norm):
            return [{"predicate": "supports_cpl", "subject": None, "object": cpl_target}]
        if cpl_target:
            return [{"predicate": "cpl_description", "subject": cpl_target, "object": None}]
        return []
    if predicate == "course_name" and code_target:
        return [{"predicate": predicate, "subject": code_target, "object": None}]
    if predicate == "total_sks":
        subj: str | None = None
        if re.search(r"\bmuatan\s+(?:program\s+studi|prodi)\b", norm):
            subj = "muatan program studi"
        elif "muatan nasional" in norm:
            subj = "muatan nasional"
        elif "muatan universitas" in norm:
            subj = "muatan universitas"
        elif "muatan fakultas" in norm:
            subj = "muatan fakultas"
        elif semester_target and (
            semester_target.isdigit() or semester_target.startswith("Semester Antara")
        ):
            subj = f"semester {semester_target}"
        return [{"predicate": predicate, "subject": subj, "object": None}]
    if predicate == "prerequisite_of" and course_target:
        rels = [{"predicate": "prerequisite_of", "subject": course_target, "object": None}]
        if re.search(r"\bnilai\s+(?:min|minimum|minimal)(?:nya)?\b", norm):
            rels.append({"predicate": "min_grade", "subject": course_target, "object": None})
        return rels
    if course_target:
        return [{"predicate": predicate, "subject": course_target, "object": None}]
    return []
