"""POS Tagging pertanyaan, Query Formulation, Query Expansion, & Reformulation (PBA14 Slide 46-47)."""

import re
import warnings
from functools import lru_cache
from pathlib import Path

import pycrfsuite

from config.settings import DATA_DIR
from src.contracts import ExtractedEntity
from src.question_processing.resources import load_course_lexicon, load_domain_lexicon
from src.question_processing.train_pos_tagger import sentence_to_features

_POS_MODEL_PATH = DATA_DIR / "question_processing" / "models" / "pos_crf.crfsuite"
_COURSE_CODE_RE = re.compile(r"^[a-z]{3}\d{5}(?:-\d)?$", re.IGNORECASE)
_CPL_CODE_RE = re.compile(r"^if_cpl_[a-z]{1,2}\d$", re.IGNORECASE)


@lru_cache(maxsize=1)
def _load_crf_tagger(model_path: str) -> pycrfsuite.Tagger | None:
    path = Path(model_path)
    if not path.exists():
        warnings.warn(
            f"Model POS CRF tidak ditemukan di {path}; memakai fallback lexicon tagger.",
            UserWarning,
            stacklevel=2,
        )
        return None
    tagger = pycrfsuite.Tagger()
    tagger.open(str(path))
    return tagger


@lru_cache(maxsize=1)
def _domain_proper_noun_phrases() -> tuple[tuple[str, ...], ...]:
    phrases: set[tuple[str, ...]] = set()
    course_lex = load_course_lexicon()
    for entry in course_lex["courses_2024"].values():
        toks = tuple(entry["name"].lower().split())
        if toks:
            phrases.add(toks)
        for alias in entry.get("aliases", []):
            a_toks = tuple(alias.lower().split())
            if len(a_toks) >= 2:
                phrases.add(a_toks)
    for entry in course_lex["courses_2020"].values():
        toks = tuple(entry["name"].lower().split())
        if toks:
            phrases.add(toks)
    domain_lex = load_domain_lexicon()
    for canon, aliases in domain_lex["learning_paths"].items():
        phrases.add(tuple(canon.lower().split()))
        for alias in aliases:
            a_toks = tuple(alias.lower().split())
            if len(a_toks) >= 2:
                phrases.add(a_toks)
    for canon, aliases in domain_lex["elective_groups"].items():
        phrases.add(tuple(canon.lower().split()))
        for alias in aliases:
            a_toks = tuple(alias.lower().split())
            if len(a_toks) >= 2:
                phrases.add(a_toks)
    for canon, aliases in domain_lex.get("knowledge_areas", {}).items():
        for alias in aliases:
            a_toks = tuple(alias.lower().split())
            if len(a_toks) >= 2:
                phrases.add(a_toks)
    for org_phrase in (
        ("teknik", "informatika"),
        ("merdeka", "belajar"),
        ("kampus", "merdeka"),
        ("universitas", "brawijaya"),
    ):
        phrases.add(org_phrase)
    return tuple(sorted(phrases, key=len, reverse=True))


def apply_domain_pos_overrides(tagged: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Menerapkan override leksikon domain kurikulum di atas hasil POS tagger umum."""
    domain_lex = load_domain_lexicon()
    wh_words = set(domain_lex["wh_words"])
    command_words = set(domain_lex["command_words"])
    abbrevs = {k.lower() for k in domain_lex["abbreviations"]}
    tokens_lower = [tok.lower() for tok, _ in tagged]
    result = list(tagged)

    # Tandai span frasa nama MK / learning path / kelompok pilihan sebagai NNP
    idx = 0
    phrases = _domain_proper_noun_phrases()
    while idx < len(tokens_lower):
        matched_len = 0
        for phrase in phrases:
            plen = len(phrase)
            if idx + plen <= len(tokens_lower) and tuple(tokens_lower[idx : idx + plen]) == phrase:
                matched_len = plen
                break
        if matched_len > 0:
            for offset in range(matched_len):
                result[idx + offset] = (result[idx + offset][0], "NNP")
            idx += matched_len
        else:
            idx += 1

    for i, (tok, tag) in enumerate(result):
        low = tok.lower()
        if low in wh_words:
            result[i] = (tok, "WH")
        elif _COURSE_CODE_RE.match(tok) or _CPL_CODE_RE.match(tok):
            result[i] = (tok, "NNP")
        elif tok.isdigit() or re.fullmatch(r"\d+(?:\.\d+)?", tok):
            result[i] = (tok, "CD")
        elif i == 0 and low in command_words:
            result[i] = (tok, "VB")
        elif low in {"sks", "mk"}:
            result[i] = (tok, "NN")
        elif low in abbrevs and tag not in {"NN", "NNP"}:
            result[i] = (tok, "NNP")

    return result


def _fallback_pos_tag(tokens: list[str]) -> list[tuple[str, str]]:
    domain_lex = load_domain_lexicon()
    wh_words = set(domain_lex["wh_words"])
    command_words = set(domain_lex["command_words"])
    preps = {"di", "ke", "dari", "pada", "dalam", "untuk", "bagi", "dengan", "tentang"}
    conjs = {"dan", "atau", "yang", "serta", "jika", "bila"}
    tagged: list[tuple[str, str]] = []
    for i, tok in enumerate(tokens):
        low = tok.lower()
        if low in wh_words:
            tagged.append((tok, "WH"))
        elif i == 0 and low in command_words:
            tagged.append((tok, "VB"))
        elif tok.isdigit():
            tagged.append((tok, "CD"))
        elif low in preps:
            tagged.append((tok, "IN"))
        elif low in conjs:
            tagged.append((tok, "SC"))
        else:
            tagged.append((tok, "NN"))
    return tagged


def pos_tag_question(tokens: list[str]) -> list[tuple[str, str]]:
    """Memberi label Part-of-Speech (POS tag) pada token pertanyaan (CRF + override domain)."""
    if not tokens:
        return []
    tagger = _load_crf_tagger(str(_POS_MODEL_PATH))
    if tagger is None:
        raw_tagged = _fallback_pos_tag(tokens)
    else:
        preds = tagger.tag(sentence_to_features(tokens))
        raw_tagged = list(zip(tokens, preds))
    return apply_domain_pos_overrides(raw_tagged)


@lru_cache(maxsize=1)
def _course_name_to_code() -> dict[str, str]:
    course_lex = load_course_lexicon()
    mapping: dict[str, str] = {}
    for code, info in course_lex["courses_2024"].items():
        mapping[info["name"].lower()] = code
    return mapping


def _append_unique(target: list[str], seen: set[str], value: str) -> None:
    clean = re.sub(r"\s+", " ", value).strip()
    if clean and clean.lower() not in seen:
        seen.add(clean.lower())
        target.append(clean)


def formulate_query(
    normalized_question: str,
    tokens: list[str],
    entities: list[ExtractedEntity],
    pos_tags: list[tuple[str, str]] | None = None,
    intent: str | None = None,
) -> tuple[list[str], list[str]]:
    """Menghasilkan `(query_keywords, expanded_queries)` untuk modul Passage Retrieval.

    Mencakup:
    - Seleksi query keywords (tanpa stemming; buang kata tanya & stopword tidak informatif)
    - Query expansion dengan sinonim/singkatan domain dan kode<->nama MK
    - Query reformulation ke pola deklaratif (ala Lin 2007, Slide 47)
    """
    del pos_tags  # dipertahankan untuk kompatibilitas kontrak
    domain_lex = load_domain_lexicon()
    course_lex = load_course_lexicon()
    stopwords = set(domain_lex["question_stopwords"])
    synonyms: dict[str, list[str]] = domain_lex["synonyms"]
    abbrevs: dict[str, str] = domain_lex["abbreviations"]
    name_to_code = _course_name_to_code()

    # Kumpulkan token yang sudah diwakili frasa entitas multi-kata agar tidak duplikat pecah
    multi_ent_tokens: set[str] = set()
    for ent in entities:
        val_toks = ent.get("value", "").lower().split()
        if len(val_toks) >= 2:
            multi_ent_tokens.update(val_toks)

    keywords: list[str] = []
    seen_kw: set[str] = set()
    for tok in tokens:
        low = tok.lower()
        if low in stopwords or low in multi_ent_tokens:
            continue
        _append_unique(keywords, seen_kw, tok)

    course_name: str | None = None
    course_code: str | None = None
    semester_val: str | None = None
    lp_val: str | None = None
    eg_val: str | None = None
    cpl_val: str | None = None
    abbr_val: str | None = None

    for ent in entities:
        etype = ent["type"]
        norm_val = ent["normalized_value"]
        _append_unique(keywords, seen_kw, norm_val)
        if etype == "course_name":
            course_name = norm_val
            resolved = name_to_code.get(norm_val.lower())
            if resolved and intent != "course_code":
                course_code = resolved
                _append_unique(keywords, seen_kw, resolved)
        elif etype == "course_code":
            canon_code = course_lex["code_aliases"].get(norm_val, norm_val)
            course_code = norm_val
            if canon_code != norm_val:
                _append_unique(keywords, seen_kw, canon_code)
            if canon_code in course_lex["courses_2024"] and intent != "course_name":
                course_name = course_lex["courses_2024"][canon_code]["name"]
                _append_unique(keywords, seen_kw, course_name)
        elif etype == "semester":
            semester_val = norm_val
        elif etype == "learning_path":
            lp_val = norm_val
        elif etype == "elective_group":
            eg_val = norm_val
        elif etype == "cpl_code":
            cpl_val = norm_val
        elif etype == "abbreviation":
            abbr_val = norm_val

    expanded: list[str] = []
    seen_exp: set[str] = set()
    seen_exp.add(normalized_question.lower())

    # 1. Ekspansi sinonim/singkatan pada query dasar
    base_phrase = " ".join(keywords)
    if base_phrase:
        seen_exp.add(base_phrase.lower())
    source_phrase = base_phrase or normalized_question
    for term, repls in synonyms.items():
        if re.search(rf"\b{re.escape(term)}\b", normalized_question):
            for rep in repls[:1]:
                if re.search(rf"\b{re.escape(term)}\b", source_phrase):
                    candidate = re.sub(rf"\b{re.escape(term)}\b", rep, source_phrase)
                    if candidate.lower() != source_phrase.lower():
                        _append_unique(expanded, seen_exp, candidate)
                if course_name and term in {"prasyarat", "syarat"}:
                    _append_unique(expanded, seen_exp, f"{rep} {course_name}")

    if abbr_val and abbr_val in abbrevs:
        _append_unique(expanded, seen_exp, f"{abbrevs[abbr_val]} {abbr_val}")

    # 2. Reformulasi deklaratif ala Lin (2007) per intent
    if intent == "course_prerequisite" and course_name:
        _append_unique(expanded, seen_exp, f"prasyarat {course_name} adalah")
        if course_code:
            _append_unique(expanded, seen_exp, f"{course_code} {course_name} prasyarat")
    elif intent == "course_min_grade" and course_name:
        _append_unique(expanded, seen_exp, f"{course_name} prasyarat nilai minimum")
    elif intent == "course_sks" and course_name:
        if course_code:
            _append_unique(expanded, seen_exp, f"{course_code} {course_name} sks")
        _append_unique(expanded, seen_exp, f"satuan kredit semester {course_name}")
    elif intent == "course_semester" and course_name:
        _append_unique(expanded, seen_exp, f"{course_name} diambil pada semester")
    elif intent == "course_code" and course_name:
        _append_unique(expanded, seen_exp, f"kode mata kuliah {course_name}")
    elif intent == "course_practicum" and course_name:
        _append_unique(expanded, seen_exp, f"{course_name} praktikum ya tidak")
    elif intent == "course_list_semester" and semester_val:
        _append_unique(expanded, seen_exp, f"semester {semester_val} kode mk nama mk sks")
    elif intent == "learning_path" and lp_val:
        _append_unique(expanded, seen_exp, f"learning path {lp_val} mata kuliah pilihan")
    elif intent == "elective_group" and eg_val:
        _append_unique(expanded, seen_exp, f"mk pilihan {eg_val}")
    elif intent == "cpl" and cpl_val:
        _append_unique(expanded, seen_exp, f"{cpl_val} capaian pembelajaran lulusan")
    elif intent == "curriculum_transition":
        sem_part = f" semester {semester_val}" if semester_val else ""
        _append_unique(expanded, seen_exp, f"aturan peralihan kurikulum 2024{sem_part}")
    elif intent == "abbreviation" and abbr_val:
        _append_unique(expanded, seen_exp, f"singkatan {abbr_val} adalah")

    return keywords, expanded[:5]
