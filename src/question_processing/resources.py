"""Loader sumber daya leksikon dan data latih untuk modul Question Processing."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from config.settings import DATA_DIR


def get_qp_data_dir() -> Path:
    """Mengembalikan path direktori data khusus modul Question Processing."""
    return DATA_DIR / "question_processing"


@lru_cache(maxsize=1)
def load_course_lexicon() -> dict[str, Any]:
    """Memuat kamus kode, nama kanonik, dan alias mata kuliah dari JSON."""
    path = get_qp_data_dir() / "lexicon" / "course_lexicon.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_domain_lexicon() -> dict[str, Any]:
    """Memuat kamus entitas domain, singkatan, sinonim, dan kata tanya."""
    path = get_qp_data_dir() / "lexicon" / "domain_lexicon.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_training_questions() -> list[dict[str, str]]:
    """Memuat dataset pertanyaan berlabel untuk pelatihan classifier."""
    path = get_qp_data_dir() / "training" / "questions_labeled.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_test_questions() -> list[dict[str, str]]:
    """Memuat dataset pertanyaan uji held-out untuk evaluasi modul."""
    path = get_qp_data_dir() / "training" / "questions_test.json"
    return json.loads(path.read_text(encoding="utf-8"))
