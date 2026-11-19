"""Orkestrator modul Question Processing (PBA14 Slide 34-47).

Menggabungkan:
1. Tokenisasi, normalisasi, dan POS tagging
2. Deteksi Question Speech Act & Question Category (Slide 17)
3. Hybrid Question Classification (Rule-based + Supervised ML, Slide 43-45)
4. Answer Type Detection dengan taksonomi Li & Roth (2005) (Slide 39-42)
5. Focus Detection (question headword) & Entity/Relation Extraction (Slide 35-37, 44)
6. Query Formulation, Synonym Expansion & Declarative Reformulation (Slide 47)
"""

from src.contracts import QuestionAnalysis


def process_question(question: str) -> QuestionAnalysis:
    """Memproses pertanyaan pengguna menjadi representasi terstruktur QuestionAnalysis."""
    raise NotImplementedError(
        "Anggota 3: hubungkan POS tagging, classifier, answer type, focus, entity/relation, dan query formulator."
    )
