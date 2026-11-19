"""Klasifikasi maksud, speech act, & kategori pertanyaan (Hybrid Rule-based + Supervised ML)."""

from typing import Any

from src.contracts import QuestionCategory, SpeechActType


def detect_speech_act(question: str) -> SpeechActType:
    """Mendeteksi tindak tutur pertanyaan (PBA14 Slide 17): wh, yes_no, command, indirect_request."""
    raise NotImplementedError("Anggota 3: implementasikan deteksi speech act pertanyaan di sini.")


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
