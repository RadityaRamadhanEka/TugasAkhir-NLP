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
from src.question_processing.answer_type_detector import detect_answer_type
from src.question_processing.entity_extractor import (
    detect_focus,
    extract_entities,
    extract_relations,
)
from src.question_processing.query_formulator import formulate_query, pos_tag_question
from src.question_processing.question_classifier import (
    classify_question,
    detect_speech_act,
)
from src.question_processing.text_utils import normalize_question, tokenize_question


def process_question(question: str) -> QuestionAnalysis:
    """Memproses pertanyaan pengguna menjadi representasi terstruktur QuestionAnalysis."""
    norm = normalize_question(question)
    tokens = tokenize_question(norm)
    pos_tags = pos_tag_question(tokens)
    speech_act = detect_speech_act(question)
    entities = extract_entities(question)
    focus = detect_focus(tokens, pos_tags=pos_tags)
    intent, question_category = classify_question(
        norm,
        pos_tags=pos_tags,
        focus=focus,
        speech_act=speech_act,
    )
    answer_type_coarse, answer_type = detect_answer_type(
        norm,
        intent,
        focus=focus,
        pos_tags=pos_tags,
    )
    relations = extract_relations(question, entities, pos_tags=pos_tags, intent=intent)
    query_keywords, expanded_queries = formulate_query(
        norm,
        tokens,
        entities,
        pos_tags=pos_tags,
        intent=intent,
    )
    return {
        "original_question": question,
        "normalized_question": norm,
        "tokens": tokens,
        "pos_tags": pos_tags,
        "speech_act": speech_act,
        "question_category": question_category,
        "intent": intent,
        "answer_type_coarse": answer_type_coarse,
        "answer_type": answer_type,
        "focus": focus,
        "query_keywords": query_keywords,
        "expanded_queries": expanded_queries,
        "entities": entities,
        "relations": relations,
    }
