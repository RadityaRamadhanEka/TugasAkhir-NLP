"""Klasifikasi maksud, speech act, & kategori pertanyaan (Hybrid Rule-based + Supervised ML)."""

from functools import lru_cache
import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC

from src.contracts import QuestionCategory, SpeechActType
from src.question_processing.resources import load_training_questions
from src.question_processing.text_utils import normalize_question, tokenize_question

_INDIRECT_REQUEST_RE = re.compile(
    r"\b(?:tolong|mohon)\b"
    r"|\bsaya\s+ingin\s+(?:tahu|mengetahui)\b"
    r"|\bboleh(?:kah)?\s+(?:saya\s+)?(?:tahu|minta|mengetahui)\b"
    r"|\bbisa(?:kah)?\s+(?:anda|kamu|tolong)?\s*(?:sebutkan|jelaskan|beri|berikan|tampilkan|carikan|tunjukkan)\b"
)
_COMMAND_RE = re.compile(
    r"^(?:sebutkan|jelaskan|tampilkan|tuliskan|berikan|uraikan|daftarkan|daftar|tunjukkan|carikan|cari)\b"
)
_YES_NO_RE = re.compile(
    r"^(?:apakah|apa\s+benar|benarkah|adakah|wajibkah|bolehkah|bisakah|perlukah|haruskah|termasukkah|memilikikah)\b"
)
_WH_RE = re.compile(
    r"\b(?:apa|siapa|siapakah|berapa|berapakah|kapan|kapankah|dimana|di\s+mana|mengapa|kenapa|bagaimana|bagaimanakah|mana|manakah|brp|gmn|gmna)\b"
)

_INTENT_TO_CATEGORY: dict[str, QuestionCategory] = {
    "course_prerequisite": "factoid",
    "course_min_grade": "factoid",
    "course_sks": "factoid",
    "course_semester": "factoid",
    "course_code": "factoid",
    "course_name": "factoid",
    "course_practicum": "yes_no",
    "course_list_semester": "list",
    "elective_group": "list",
    "learning_path": "list",
    "learning_path_list": "list",
    "total_sks": "factoid",
    "curriculum_transition": "narrative",
    "course_equivalence": "factoid",
    "cpl": "definition",
    "graduate_profile": "list",
    "vision_mission": "definition",
    "course_description": "definition",
    "mbkm": "list",
    "abbreviation": "definition",
    "other": "factoid",
}

_COURSE_CODE_PATTERN = re.compile(r"\b[a-z]{3}\d{5}(?:-\d)?\b")
_SPECIFIC_LP_RE = re.compile(
    r"\b(?:frontend|front\s+end|backend|back\s+end|game|cloud|security|network|ai/ml|ai\s+ml|computer\s+vision|data\s+scien\w+|nlp|ai\s+research)\b"
)

# Aturan berprioritas (regex/kondisi -> intent) untuk pola domain yang sangat khas
_RULE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("abbreviation", re.compile(r"\b(?:kepanjangan|singkatan)\b")),
    (
        "curriculum_transition",
        re.compile(
            r"\b(?:aturan\s+peralihan|ketentuan\s+peralihan|masa\s+peralihan|transisi\s+kurikulum|kekurangan\s+sks|nilai\s+d\s+pada)\b"
        ),
    ),
    (
        "course_equivalence",
        re.compile(r"\b(?:setara|ekuivalen|pengganti|penyetaraan|disetarakan|menggantikan)\b"),
    ),
    (
        "course_min_grade",
        re.compile(
            r"\b(?:nilai\s+(?:min|minimum|minimal)|minimal\s+(?:dapat\s+)?nilai)\b.*\b(?:prasyarat|syarat)\b|\b(?:prasyarat|syarat)\b.*\bnilai\s+(?:min|minimum|minimal)\b"
        ),
    ),
)


def detect_speech_act(question: str) -> SpeechActType:
    """Mendeteksi tindak tutur pertanyaan (PBA14 Slide 17): wh, yes_no, command, indirect_request."""
    norm = normalize_question(question)
    if _INDIRECT_REQUEST_RE.search(norm):
        return "indirect_request"
    if _COMMAND_RE.search(norm):
        return "command"
    if _YES_NO_RE.search(norm):
        return "yes_no"
    if _WH_RE.search(norm):
        return "wh"
    return "wh"


def classify_question_rule_only(
    normalized_question: str,
    speech_act: SpeechActType | None = None,
) -> str | None:
    """Mengembalikan intent bila cocok aturan regex berprioritas tinggi, atau None."""
    norm = normalize_question(normalized_question)
    for intent, pat in _RULE_PATTERNS:
        if pat.search(norm):
            return intent

    if re.search(r"\b(?:praktikum|praktik)\b", norm) and (
        speech_act == "yes_no" or _YES_NO_RE.search(norm)
    ):
        return "course_practicum"

    if re.search(r"\b(?:prasyarat|syarat\s+(?:ambil|mengambil|lulus|memprogram)|butuh\s+.*\bmata\s+kuliah)\b", norm) and not re.search(
        r"\b(?:mbkm|merdeka\s+belajar|pertukaran|magang)\b", norm
    ):
        return "course_prerequisite"

    if re.search(r"\bkode\s+(?:resmi\s+)?(?:dari\s+)?(?:mk|mata\s+kuliah)\b", norm) and not _COURSE_CODE_PATTERN.search(norm):
        return "course_code"

    if _COURSE_CODE_PATTERN.search(norm) and re.search(
        r"\b(?:nama\s+(?:mk|mata\s+kuliah)|berkode|dengan\s+kode|merujuk|adalah\s+kode|merupakan\s+mata\s+kuliah)\b",
        norm,
    ):
        return "course_name"

    if re.search(r"\blearning\s+path\b", norm):
        return "learning_path" if _SPECIFIC_LP_RE.search(norm) else "learning_path_list"

    if re.search(
        r"\b(?:kelompok\s+(?:mk|mata\s+kuliah|perekayasa|komputasi|infrastruktur)|tabel\s+7\.[1-3]|perekayasa\s+(?:perangkat\s+lunak|infrastruktur|komputasi)|kategori\s+mk\s+pilihan)\b",
        norm,
    ) and not re.search(r"\bprofil\s+lulusan\b", norm):
        return "elective_group"

    if re.search(r"\b(?:total|keseluruhan)\s+(?:beban\s+)?sks\b", norm):
        return "total_sks"

    if re.search(r"\b(?:sks|satuan\s+kredit\s+semester)\b", norm) and not re.search(
        r"\bsks\s+atau\s+mk\b", norm
    ):
        return "course_sks"

    if re.search(r"\bsemester\s+(?:berapa|apa|mana|ganjil|genap)\b", norm) or (
        re.search(r"\bsemester\b", norm)
        and re.search(r"\b(?:diambil|ditempuh|dijadwalkan|ditawarkan|diprogram|masuk|berada)\b", norm)
        and not re.search(r"\b(?:apa\s+saja|daftar|semua|seluruh)\b", norm)
    ):
        return "course_semester"

    if re.search(
        r"\bsemester\s+(?:[1-8]|satu|dua|tiga|empat|lima|enam|tujuh|delapan|antara)\b", norm
    ) and re.search(r"\b(?:mk|mata\s+kuliah|wajib|daftar|apa\s+saja|sebutkan|tampilkan|tuliskan)\b", norm):
        return "course_list_semester"

    if re.search(r"\bif_cpl_[a-z0-9]+\b|\bcpl\b", norm):
        return "cpl"

    if re.search(r"\bprofil\s+lulusan\b", norm):
        return "graduate_profile"

    if re.search(
        r"\b(?:visi|misi|tujuan\s+(?:dari\s+)?program\s+studi|tujuan\s+pendidikan|tujuan\s+lulusan|dorongan\s+utama)\b",
        norm,
    ):
        return "vision_mission"

    if re.search(
        r"\b(?:mbkm|merdeka\s+belajar|kampus\s+merdeka|pertukaran\s+mahasiswa|magang|proyek\s+independen|proyek\s+kemanusiaan|asisten\s+riset|asistensi\s+mengajar|studi\s+independen|kknt|membangun\s+desa)\b",
        norm,
    ):
        return "mbkm"

    if re.search(r"\b(?:dipelajari|bahan\s+kajian|silabus|deskripsi|materi|topik|pembahasan)\b", norm) and re.search(
        r"\b(?:mk|mata\s+kuliah|kuliah)\b", norm
    ):
        return "course_description"

    return None


def _select_norm_field(records: list[dict[str, str]]) -> list[str]:
    return [r["norm"] for r in records]


def _select_pos_field(records: list[dict[str, str]]) -> list[str]:
    return [r["pos"] for r in records]


def _select_head_field(records: list[dict[str, str]]) -> list[str]:
    return [r["head"] for r in records]


def _build_feature_union() -> FeatureUnion:
    return FeatureUnion(
        transformer_list=[
            (
                "word_ngrams",
                Pipeline(
                    [
                        ("sel", FunctionTransformer(_select_norm_field, validate=False)),
                        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                    ]
                ),
            ),
            (
                "pos_ngrams",
                Pipeline(
                    [
                        ("sel", FunctionTransformer(_select_pos_field, validate=False)),
                        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
                    ]
                ),
            ),
            (
                "headword",
                Pipeline(
                    [
                        ("sel", FunctionTransformer(_select_head_field, validate=False)),
                        ("tfidf", TfidfVectorizer()),
                    ]
                ),
            ),
        ]
    )


def _featurize_sample(
    question: str,
    pos_tags: list[tuple[str, str]] | None = None,
    focus: str | None = None,
) -> dict[str, str]:
    from src.question_processing.entity_extractor import detect_focus
    from src.question_processing.query_formulator import pos_tag_question

    norm = normalize_question(question)
    toks = tokenize_question(norm)
    tags = pos_tags if pos_tags is not None else pos_tag_question(toks)
    head = focus if focus is not None else detect_focus(toks, tags)
    pos_str = " ".join(tag for _, tag in tags)
    head_str = f"HEAD_{(head or 'NONE').replace(' ', '_')}"
    return {"norm": norm, "pos": pos_str, "head": head_str}


def _make_classifier_pipeline(estimator: Any) -> Pipeline:
    return Pipeline([("features", _build_feature_union()), ("clf", estimator)])


def evaluate_ml_classifiers(
    labeled_samples: list[dict[str, str]],
    records: list[dict[str, str]] | None = None,
) -> dict[str, dict[str, float]]:
    """Membandingkan MultinomialNB, LinearSVC, dan LogisticRegression memakai 5-fold Stratified CV."""
    feat_records = records if records is not None else [_featurize_sample(item["question"]) for item in labeled_samples]
    labels = [item["intent"] for item in labeled_samples]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    candidates = {
        "MultinomialNB": MultinomialNB(alpha=0.5),
        "LinearSVC": LinearSVC(C=1.5, random_state=42),
        "LogisticRegression": LogisticRegression(C=3.0, max_iter=1000, random_state=42),
    }
    summary: dict[str, dict[str, float]] = {}
    for name, est in candidates.items():
        pipe = _make_classifier_pipeline(est)
        scores = cross_validate(
            pipe,
            feat_records,
            labels,
            cv=cv,
            scoring=("accuracy", "f1_macro"),
        )
        summary[name] = {
            "accuracy": float(scores["test_accuracy"].mean()),
            "macro_f1": float(scores["test_f1_macro"].mean()),
        }
    return summary


def train_question_classifier(labeled_samples: list[dict[str, str]]) -> Any:
    """Melatih supervised classifier klasik (scikit-learn) terbaik dari data beranotasi (Slide 45)."""
    records = [_featurize_sample(item["question"]) for item in labeled_samples]
    labels = [item["intent"] for item in labeled_samples]
    cv_summary = evaluate_ml_classifiers(labeled_samples, records=records)

    # Pilih model terbaik menurut macro_f1 (tie-breaker ke LogisticRegression)
    best_name = max(
        cv_summary,
        key=lambda k: (round(cv_summary[k]["macro_f1"], 6), k == "LogisticRegression"),
    )
    est_map = {
        "MultinomialNB": MultinomialNB(alpha=0.5),
        "LinearSVC": LinearSVC(C=1.5, random_state=42),
        "LogisticRegression": LogisticRegression(C=3.0, max_iter=1000, random_state=42),
    }
    best_pipe = _make_classifier_pipeline(est_map[best_name])
    best_pipe.fit(records, labels)
    return best_pipe


@lru_cache(maxsize=1)
def _get_default_classifier() -> Any:
    return train_question_classifier(load_training_questions())


def classify_question(
    normalized_question: str,
    pos_tags: list[tuple[str, str]] | None = None,
    classifier_model: Any | None = None,
    focus: str | None = None,
    speech_act: SpeechActType | None = None,
) -> tuple[str, QuestionCategory]:
    """Mengklasifikasikan pertanyaan ke `(intent, question_category)` secara hybrid."""
    sa = speech_act if speech_act is not None else detect_speech_act(normalized_question)
    rule_intent = classify_question_rule_only(normalized_question, speech_act=sa)

    if rule_intent is not None:
        intent = rule_intent
    else:
        model = classifier_model if classifier_model is not None else _get_default_classifier()
        feat = _featurize_sample(normalized_question, pos_tags=pos_tags, focus=focus)
        intent = str(model.predict([feat])[0])
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba([feat])[0]
            if float(max(probs)) < 0.12:
                intent = "other"

    category: QuestionCategory = "yes_no" if sa == "yes_no" else _INTENT_TO_CATEGORY.get(intent, "factoid")
    return intent, category
