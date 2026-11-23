"""Uji answer_extractor dengan data tiruan kecil (tidak perlu korpus asli)."""

from src.answer_processing.answer_extractor import extract_answer_candidates


def _analysis(question, intent, answer_type, coarse, relations=(), entities=(), focus=None, keywords=()):
    return {
        "original_question": question,
        "normalized_question": question.lower(),
        "intent": intent,
        "answer_type": answer_type,
        "answer_type_coarse": coarse,
        "relations": list(relations),
        "entities": list(entities),
        "focus": focus,
        "query_keywords": list(keywords),
    }


PASSAGE_SEMESTER_3 = {
    "passage_id": "p_1",
    "pdf_page": 20,
    "doc_page": "12",
    "content_type": "table",
    "rerank_score": 0.7,
    "text": "Distribusi Mata Kuliah Semester 3: Mata kuliah CIF63110 Kecerdasan Artifisial, Semester 3, "
            "2 SKS, Praktikum: Tidak, Prasyarat: CIF62305 Aljabar Linear (nilai minimal C).",
}

PASSAGE_KA_LANJUT = {
    "passage_id": "p_2",
    "pdf_page": 21,
    "doc_page": "13",
    "content_type": "table",
    "rerank_score": 0.8,
    "text": "Distribusi Mata Kuliah Semester 4: Mata kuliah CIF64311 Kecerdasan Artifisial Lanjut, Semester 4, "
            "5 SKS, Praktikum: Ya, Prasyarat: CIF63110 Kecerdasan Artifisial (nilai minimal C).",
}

SKS_QUESTION = _analysis(
    "Berapa SKS mata kuliah Kecerdasan Artifisial?", "course_sks", "NUMERIC:count", "NUMERIC",
    relations=[{"predicate": "sks", "subject": "Kecerdasan Artifisial", "object": None}],
    entities=[{"type": "course_name", "value": "kecerdasan artifisial", "normalized_value": "Kecerdasan Artifisial"}],
    focus="sks", keywords=["sks", "Kecerdasan Artifisial"],
)


def test_kb_hanya_memakai_predikat_yang_ditanya() -> None:
    triples = [
        {"triple_id": "t1", "subject": "Kecerdasan Artifisial", "predicate": "sks", "object": 2, "pdf_page": 19},
        {"triple_id": "t2", "subject": "Kecerdasan Artifisial", "predicate": "semester", "object": 3, "pdf_page": 20},
    ]
    candidates = extract_answer_candidates(SKS_QUESTION, {"results": [], "structured_results": triples})
    kb = [c for c in candidates if c["extraction_method"] == "knowledge_base"]
    assert [c["answer"] for c in kb] == ["2 SKS"]
    assert kb[0]["source"]["triple_id"] == "t1"
    assert kb[0]["source"]["pdf_page"] == 19


def test_angka_diambil_dari_mk_yang_ditanya_bukan_mk_mirip() -> None:
    result = {"results": [PASSAGE_KA_LANJUT, PASSAGE_SEMESTER_3], "structured_results": []}
    ner = [c for c in extract_answer_candidates(SKS_QUESTION, result) if c["extraction_method"] == "ner_tagger"]
    # KA Lanjut (5 SKS) dan penyebutan KA sebagai prasyarat tidak boleh menghasilkan kandidat
    assert [c["answer"] for c in ner] == ["2 SKS"]
    assert ner[0]["source"]["pdf_page"] == 20


def test_pola_prasyarat() -> None:
    question = _analysis(
        "Apa prasyarat mata kuliah Kecerdasan Artifisial?", "course_prerequisite", "ENTITY:prerequisite", "ENTITY",
        relations=[{"predicate": "prerequisite_of", "subject": "Kecerdasan Artifisial", "object": None}],
        focus="mata kuliah prasyarat", keywords=["prasyarat", "Kecerdasan Artifisial"],
    )
    result = {"results": [PASSAGE_SEMESTER_3], "structured_results": []}
    regex = [c for c in extract_answer_candidates(question, result) if c["extraction_method"] == "pattern_regex"]
    assert regex[0]["answer"] == "CIF62305 Aljabar Linear dengan nilai minimum C"


def test_pola_peralihan_kurikulum_memakai_nama_lama() -> None:
    passage = {
        "passage_id": "p_3", "pdf_page": 41, "doc_page": "33", "content_type": "table", "rerank_score": 0.8,
        "text": "Tabel 9.2: Kurikulum Lama (2020) CIF61011 Kecerdasan Buatan (3 SKS) disetarakan dengan "
                "Kurikulum Baru (2024) CIF63110 Kecerdasan Artifisial (2 SKS).",
    }
    question = _analysis(
        "Kecerdasan Buatan diganti menjadi mata kuliah apa?", "course_equivalence", "ENTITY:course_name", "ENTITY",
        relations=[{"predicate": "equivalent_to", "subject": "Kecerdasan Artifisial", "object": None}],
        entities=[{"type": "course_name", "value": "kecerdasan buatan", "normalized_value": "Kecerdasan Artifisial"}],
        focus="mata kuliah", keywords=["kurikulum", "diganti"],
    )
    candidates = extract_answer_candidates(question, {"results": [passage], "structured_results": []})
    assert candidates[0]["answer"] == "CIF63110 Kecerdasan Artifisial (2 SKS)"


def test_pola_definisi_dalam_tanda_kutip() -> None:
    passage = {
        "passage_id": "p_4", "pdf_page": 10, "doc_page": "3", "content_type": "text", "rerank_score": 0.6,
        "text": 'Profil lulusan program studi Teknik Informatika adalah "Perekayasa perangkat lunak yang '
                'berintegritas tinggi." Lulusan diharapkan mampu bersaing.',
    }
    question = _analysis(
        "Apa profil lulusan program studi?", "graduate_profile", "DESCRIPTION:definition", "DESCRIPTION",
        focus="profil lulusan program studi", keywords=["profil", "lulusan"],
    )
    candidates = extract_answer_candidates(question, {"results": [passage], "structured_results": []})
    assert candidates[0]["extraction_method"] == "pattern_regex"
    assert candidates[0]["answer"] == "Perekayasa perangkat lunak yang berintegritas tinggi"


def test_daftar_learning_path_digabung() -> None:
    triples = [
        {"triple_id": f"t{i}", "subject": name, "predicate": "learning_path_member", "object": "NLP Engineer", "pdf_page": 34}
        for i, name in enumerate(["Pemrosesan Bahasa Alami", "Pemerolehan Informasi dan Penambangan Teks"])
    ]
    question = _analysis(
        "MK apa saja pada learning path NLP Engineer?", "learning_path", "ENTITY:course_list", "ENTITY",
        relations=[{"predicate": "learning_path_member", "subject": None, "object": None}],
        keywords=["learning", "path", "NLP Engineer"],
    )
    candidates = extract_answer_candidates(question, {"results": [], "structured_results": triples})
    assert candidates[0]["answer"] == "Pemrosesan Bahasa Alami dan Pemerolehan Informasi dan Penambangan Teks"


def test_kepanjangan_singkatan() -> None:
    passage = {
        "passage_id": "p_5", "pdf_page": 38, "doc_page": "30", "content_type": "text", "rerank_score": 0.5,
        "text": "Mahasiswa dapat belajar di luar kampus dalam Program Merdeka Belajar Kampus Merdeka (MBKM) "
                "yang dilaksanakan satu semester.",
    }
    question = _analysis(
        "Apa kepanjangan dari MBKM?", "abbreviation", "ABBREVIATION:expansion", "ABBREVIATION",
        entities=[{"type": "abbreviation", "value": "mbkm", "normalized_value": "MBKM"}],
        focus="kepanjangan", keywords=["kepanjangan", "mbkm"],
    )
    candidates = extract_answer_candidates(question, {"results": [passage], "structured_results": []})
    assert candidates[0]["answer"] == "Merdeka Belajar Kampus Merdeka"  # "Program" tidak ikut


def test_tanpa_bahan_tidak_ada_kandidat() -> None:
    assert extract_answer_candidates(SKS_QUESTION, {"results": [], "structured_results": []}) == []
