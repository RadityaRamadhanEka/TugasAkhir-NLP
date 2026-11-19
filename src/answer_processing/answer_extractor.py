"""Ekstraksi kandidat jawaban berbasis Answer-Type NER, Pattern Regex, & Knowledge Base (PBA14 Slide 55-59, 75)."""

from src.contracts import AnswerCandidate, QuestionAnalysis, RetrievalResult


def extract_answer_candidates(
    question_analysis: QuestionAnalysis,
    retrieval_result: RetrievalResult,
) -> list[AnswerCandidate]:
    """Mengekstrak kandidat jawaban dari passage dan knowledge triples terpilih.

    Menggabungkan tiga jalur ekstraksi sesuai materi PBA14:
    1. Answer-type Named Entity Tagger (Slide 55-56) untuk jawaban factoid (NUMERIC/ENTITY/HUMAN)
    2. Answer-type Pattern Extraction `<QP>/<AP>` (Slide 57-58) untuk definisi, prasyarat, & aturan
    3. Structured Knowledge Base Extraction (Slide 66-75) dari `retrieval_result["structured_results"]`
    """
    raise NotImplementedError("Anggota 5: implementasikan ekstraksi kandidat jawaban di sini.")
