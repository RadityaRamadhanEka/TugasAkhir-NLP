"""Deteksi Answer Type mengikuti Taksonomi Li & Roth (2005) (PBA14 Slide 39-46)."""

from src.contracts import AnswerTypeCoarse

# 6 kelas umum Li & Roth (2005) dan contoh pemetaan subkelas domain Kurikulum 2024 TIF UB:
# - NUMERIC      : NUMERIC:count (total SKS), NUMERIC:period (semester), NUMERIC:grade (nilai minimum)
# - ENTITY       : ENTITY:course_code, ENTITY:course_name, ENTITY:course_list, ENTITY:prerequisite, ENTITY:cpl
# - DESCRIPTION  : DESCRIPTION:definition (visi/misi/profil), DESCRIPTION:reason (aturan peralihan/prosedur)
# - ABBREVIATION : ABBREVIATION:exp (kepanjangan CPL, MBKM, SKS, dsb.)
# - HUMAN        : HUMAN:group (tim penyusun, profil lulusan)
# - LOCATION     : LOCATION:other (unit/fakultas/prodi jika relevan)


def detect_answer_type(
    normalized_question: str,
    intent: str,
    focus: str | None = None,
    pos_tags: list[tuple[str, str]] | None = None,
) -> tuple[AnswerTypeCoarse, str]:
    """Menentukan `(answer_type_coarse, answer_type_fine)` sesuai Li & Roth (2005)."""
    raise NotImplementedError("Anggota 3: implementasikan deteksi answer type Li & Roth di sini.")
