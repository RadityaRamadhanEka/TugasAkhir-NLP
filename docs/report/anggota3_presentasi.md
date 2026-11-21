# Bahan Presentasi & Serah Terima (Anggota 3 — Yusuf)

---

## 1. Struktur 4 Slide Presentasi Bagian Anggota 3

### Slide 1 — Peran Question Processing dalam Arsitektur Hybrid QA
- **Posisi:** Pintu masuk (hulu) sistem Hybrid QA tanpa LLM.
- **Tugas:** Mengubah pertanyaan bebas pengguna menjadi objek terstruktur `QuestionAnalysis` (14 field sesuai `src/contracts.py`) untuk dipakai oleh **Retrieval (Azza)** dan **Answer Extraction (Zulfan)**.
- **Nilai tambah:** Menggabungkan teknik Classic NLP 1 semester (Regex, POS Tagging CRF, Gazetteer NER, Focus Detection, Hybrid Rule+ML Classification, Li & Roth Answer Type, dan Query Expansion).

### Slide 2 — Alur 6 Tahap + Contoh End-to-End
- **Input:** `"Apa prasyarat Kecerdasan Artifisial Lanjut?"`
- **Langkah:**
  1. Normalisasi & Tokenisasi → `["apa", "prasyarat", "kecerdasan", "artifisial", "lanjut"]`
  2. POS Tagging Hybrid (CRF + Override) → `WH, NN, NNP, NNP, NNP`
  3. Speech Act (`wh`) + Focus (`prasyarat`) + Entity (`Kecerdasan Artifisial Lanjut`)
  4. Hybrid Classifier (`course_prerequisite` / `factoid`) + Li & Roth (`ENTITY:prerequisite`)
  5. Relation (`prerequisite_of`, subject=`Kecerdasan Artifisial Lanjut`, object=`None`)
  6. Query Keywords (`prasyarat`, `Kecerdasan Artifisial Lanjut`, `CIF64311`) + Expanded Queries (`syarat ...`, `prasyarat ... adalah`).

### Slide 3 — Hasil Eksperimen Kuantitatif Modul
- **POS Tagger CRF (IDN Tagged Corpus 10.030 kalimat):**
  - Held-out IDN: **97,15%**
  - Domain Gold (20 pertanyaan kurikulum): **67,44% (CRF mentah) → 94,57% (+27,13% dengan Domain Override)**.
- **Perbandingan 3 Classifier ML (5-Fold CV, 252 sampel, 21 intent):**
  - `MultinomialNB`: 76,22% (Macro-F1 0,7454)
  - `LogisticRegression`: 80,93% (Macro-F1 0,7983)
  - **`LinearSVC`**: **87,28% (Macro-F1 0,8606)**
- **Ablasi pada 63 Pertanyaan Uji Held-Out:**
  - Rule-only: 92,06% | ML-only: 98,41% | **Hybrid: 98,41% (Macro-F1 0,9837)**.
- **Speech Act:** 100% | **Answer Type Coarse:** 100% | **Entity F1 (12 fixture):** 100%.

### Slide 4 — Keterbatasan & Contoh Kesalahan
- **1 kasus salah pada 63 uji held-out:** `"Kapan libur semester genap berakhir di kalender akademik nasional?"` terdeteksi `course_semester` (target: `other`) karena aturan `semester genap` belum mensyaratkan kehadiran entitas mata kuliah.
- **Penanganan inkonsistensi dokumen asli:** Gazetteer memetakan kode kembar (`CIF60048`/`CIF60050`, `CIF63106`/`CIF63107`, `CIF63108`/`CIF63109`, `CIF63110`/`CIF63310`) dan memisahkan kode Kurikulum 2020 vs 2024.

---

## 2. Skrip Demo Live (Terminal)

```bash
cd "/home/helloohowareyu/Documents/Natural Language Processing/TugasAkhir-NLP"
source .venv/bin/activate
python -c "from src.question_processing.question_processor import process_question as p; import json; print(json.dumps(p('Sebutkan mata kuliah pada semester 4!'), ensure_ascii=False, indent=2))"
```

---

## 3. Ringkasan 3 Kalimat untuk Abstrak (Serahkan ke Zulfan)

> Modul *Question Processing* dibangun menggunakan pendekatan *Classic NLP* tanpa LLM yang mencakup POS *tagging* hibrida (CRF terlatih pada *IDN Tagged Corpus* dengan *domain lexicon override*), ekstraksi entitas berbasis *gazetteer longest-match*, deteksi *speech act* dan *focus*, klasifikasi maksud hibrida (*rule-based* + `LinearSVC`), pemetaan *expected answer type* berbasis taksonomi Li & Roth, serta formulasi dan ekspansi kueri. Evaluasi mandiri pada 63 pertanyaan uji *held-out* menunjukkan akurasi *speech act* sebesar 100%, akurasi klasifikasi *intent* sebesar 98,41% (*macro-F1* 0,9837), akurasi *answer type coarse* sebesar 100%, serta peningkatan akurasi POS *tagging* domain dari 67,44% menjadi 94,57% berkat *domain override*.

---

## 4. Baris Tanggung Jawab untuk `tanggungjawab.docx`

| Nama | Peran | Tanggung Jawab Teknis yang Dikerjakan |
|---|---|---|
| **Yusuf** | Anggota 3 — Question Processing & NLP Analysis | Merancang taksonomi 21 intent & kontrak fixture tim (`docs/question_taxonomy.md`); membangun gazetteer mata kuliah & leksikon domain dari PDF (`build_lexicon.py`, `resources.py`); mengimplementasikan normalisasi/tokenisasi (`text_utils.py`), POS tagger CRF + domain override (`train_pos_tagger.py`, `query_formulator.py`), deteksi *speech act* & hybrid classifier (`question_classifier.py`), ekstraksi entitas/focus/relasi (`entity_extractor.py`), deteksi *answer type* Li & Roth (`answer_type_detector.py`), orkestrator `process_question` (`question_processor.py`), evaluasi & unit test (`evaluate_qp.py`, `tests/test_question_processing.py`), menyusun 4 soal evaluasi Q09–Q12, serta menulis bagian Bab II, III, dan IV modul Question Processing. |
