"""Deteksi Answer Type mengikuti Taksonomi Li & Roth (2005) (PBA14 Slide 39-46)."""

import re

from src.contracts import AnswerTypeCoarse
from src.question_processing.text_utils import normalize_question

# 6 kelas umum Li & Roth (2005) dan pemetaan subkelas domain Kurikulum 2024 TIF UB:
# - NUMERIC      : NUMERIC:count (total/jumlah SKS), NUMERIC:order (semester),
#                  NUMERIC:grade (nilai minimum), NUMERIC:code (kode MK)
# - ENTITY       : ENTITY:course_name, ENTITY:course_list, ENTITY:prerequisite,
#                  ENTITY:learning_path, ENTITY:other
# - DESCRIPTION  : DESCRIPTION:definition (visi/misi/CPL/silabus), DESCRIPTION:manner (aturan peralihan),
#                  DESCRIPTION:yes_no, DESCRIPTION:other
# - ABBREVIATION : ABBREVIATION:expansion (kepanjangan CPL, MBKM, SKS, dsb.)
# - HUMAN        : HUMAN:title (profil lulusan), HUMAN:individual (pertanyaan siapa)
# - LOCATION     : LOCATION:other (lokasi/unit jika relevan)

_INTENT_ANSWER_TYPE: dict[str, tuple[AnswerTypeCoarse, str]] = {
    "course_prerequisite": ("ENTITY", "ENTITY:prerequisite"),
    "course_min_grade": ("NUMERIC", "NUMERIC:grade"),
    "course_sks": ("NUMERIC", "NUMERIC:count"),
    "course_semester": ("NUMERIC", "NUMERIC:order"),
    "course_code": ("NUMERIC", "NUMERIC:code"),
    "course_name": ("ENTITY", "ENTITY:course_name"),
    "course_practicum": ("DESCRIPTION", "DESCRIPTION:yes_no"),
    "course_list_semester": ("ENTITY", "ENTITY:course_list"),
    "elective_group": ("ENTITY", "ENTITY:course_list"),
    "learning_path": ("ENTITY", "ENTITY:course_list"),
    "learning_path_list": ("ENTITY", "ENTITY:learning_path"),
    "total_sks": ("NUMERIC", "NUMERIC:count"),
    "curriculum_transition": ("DESCRIPTION", "DESCRIPTION:manner"),
    "course_equivalence": ("ENTITY", "ENTITY:course_name"),
    "cpl": ("DESCRIPTION", "DESCRIPTION:definition"),
    "graduate_profile": ("HUMAN", "HUMAN:title"),
    "vision_mission": ("DESCRIPTION", "DESCRIPTION:definition"),
    "course_description": ("DESCRIPTION", "DESCRIPTION:definition"),
    "mbkm": ("ENTITY", "ENTITY:other"),
    "abbreviation": ("ABBREVIATION", "ABBREVIATION:expansion"),
}


def detect_answer_type(
    normalized_question: str,
    intent: str,
    focus: str | None = None,
    pos_tags: list[tuple[str, str]] | None = None,
) -> tuple[AnswerTypeCoarse, str]:
    """Menentukan `(answer_type_coarse, answer_type_fine)` sesuai Li & Roth (2005)."""
    del focus, pos_tags  # dipertahankan untuk kompatibilitas kontrak
    if intent in _INTENT_ANSWER_TYPE:
        return _INTENT_ANSWER_TYPE[intent]

    norm = normalize_question(normalized_question)
    if re.search(r"\b(?:kepanjangan|singkatan)\b", norm):
        return ("ABBREVIATION", "ABBREVIATION:expansion")
    if re.search(r"\bsiapa(?:kah)?\b", norm):
        return ("HUMAN", "HUMAN:individual")
    if re.search(r"\b(?:dimana|di\s+mana)\b", norm):
        return ("LOCATION", "LOCATION:other")
    if re.search(r"\bkapan(?:kah)?\b", norm):
        return ("NUMERIC", "NUMERIC:date")
    if re.search(r"\b(?:berapa|berapakah|brp)\b", norm):
        return ("NUMERIC", "NUMERIC:count")
    return ("DESCRIPTION", "DESCRIPTION:other")
