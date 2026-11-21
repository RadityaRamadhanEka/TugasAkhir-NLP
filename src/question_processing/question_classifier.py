"""Klasifikasi maksud, speech act, & kategori pertanyaan (Hybrid Rule-based + Supervised ML)."""

import re
from typing import Any

from src.contracts import QuestionCategory, SpeechActType
from src.question_processing.text_utils import normalize_question

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


def classify_question(
    normalized_question: str,
    pos_tags: list[tuple[str, str]] | None = None,
    classifier_model: Any | None = None,
) -> tuple[str, QuestionCategory]:
    """Mengklasifikasikan pertanyaan ke `(intent, question_category)` secara hybrid.

    Menggabungkan aturan regex/pola kata tanya (rule-based) dan classifier klasik
    (mis. MultinomialNB / LinearSVC / LogisticRegression dengan fitur kata, POS tag, headword).
    """
    raise NotImplementedError("Anggota 3: implementasikan klasifikasi intent & kategori pertanyaan di sini.")


def train_question_classifier(labeled_samples: list[dict[str, str]]) -> Any:
    """Melatih supervised classifier klasik (scikit-learn) dari data pertanyaan beranotasi (Slide 45)."""
    raise NotImplementedError("Anggota 3: implementasikan pelatihan classifier pertanyaan di sini.")
