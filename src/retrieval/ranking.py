"""Re-ranking kandidat passage berbasis Answer Type & 6 Fitur PBA14 Slide 51-52."""

from src.contracts import QuestionAnalysis, RetrievedPassage

# 6 Fitur Passage Reranking (PBA14 Slide 52):
# 1. answer_type_ne_count  : Jumlah named entities yang cocok dengan expected answer_type
# 2. keyword_match_count   : Jumlah question keywords yang muncul pada passage
# 3. longest_keyword_seq   : Panjang rangkaian kata kunci terpanjang yang muncul berurutan
# 4. source_doc_rank       : Peringkat dokumen/bab asal passage dari tahap retrieval pertama
# 5. keyword_proximity     : Kedekatan (jarak token) antar kata kunci query pada passage
# 6. ngram_overlap         : Bigram/trigram overlap antara passage dan pertanyaan


def extract_passage_ranking_features(
    passage: RetrievedPassage,
    question_analysis: QuestionAnalysis,
) -> dict[str, float]:
    """Menghitung 6 fitur pemeringkatan passage (PBA14 Slide 52) untuk satu kandidat passage."""
    raise NotImplementedError("Anggota 4: implementasikan ekstraksi 6 fitur passage reranking di sini.")


def rank_passages(
    candidates: list[RetrievedPassage],
    question_analysis: QuestionAnalysis,
) -> list[RetrievedPassage]:
    """Mengurutkan ulang kandidat passage memakai answer_type & 6 fitur Slide 52."""
    raise NotImplementedError("Anggota 4: implementasikan passage reranking di sini.")
