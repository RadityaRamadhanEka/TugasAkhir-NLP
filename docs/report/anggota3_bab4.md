# Draf Bahan Bab IV — Implementasi Modul Question Processing (Bagian Anggota 3: Yusuf)

> **Catatan Penulis (Yusuf):** Bab IV memiliki bobot 20% dan pedoman TP mensyaratkan **penjelasan cara kerja kode program, bukan sekadar menempel kode**, serta menjelaskan bagian yang dibuat sendiri vs library eksternal. Sunting narasi ini dengan gaya penulisan Anda sendiri.

---

## 4.X Pembagian Implementasi: Dibuat Sendiri vs Library Eksternal

| Komponen | Bagian yang Dibuat Sendiri | Library / Data Eksternal |
|---|---|---|
| Normalisasi & Tokenisasi (`text_utils.py`) | Pola regex khusus yang menjaga kode MK (`CIF63110`, `MPK60001-5`), kode CPL (`IF_CPL_KK1`), dan `ai/ml` tetap utuh | `re` (Python stdlib) |
| Pembangunan Gazetteer (`build_lexicon.py`, `resources.py`) | Logika pemisahan tabel Kurikulum 2024 vs 2020, penanganan inkonsistensi kode antar-bab, kurasi alias mahasiswa, loader ber-cache | `pdfplumber`, `pymupdf` (baca PDF) |
| POS Tagging Hybrid (`train_pos_tagger.py`, `query_formulator.py`) | Parser pemecah token multi-kata IDN, ekstraksi 18 fitur morfologi/konteks, fungsi *domain lexicon override*, *fallback tagger* | `python-crfsuite` (algoritma CRF), IDN Tagged Corpus UI (data latih) |
| Speech Act, Entity, Focus, Relation (`entity_extractor.py`, `question_classifier.py`) | Seluruh aturan prioritas tindak tutur, *longest-match* gazetteer non-tumpang-tindih, 4 pola *focus* berbasis POS, pemetaan relasi biner | `re` |
| Hybrid Question Classifier & Answer Type (`question_classifier.py`, `answer_type_detector.py`) | Aturan regex berprioritas, rekayasa `FeatureUnion` (kata + POS + *headword*), dataset 252 latih & 63 uji, pemetaan Li & Roth | `scikit-learn` (`TfidfVectorizer`, `MultinomialNB`, `LinearSVC`, `LogisticRegression`, `StratifiedKFold`) |
| Query Formulation & Orkestrator (`query_formulator.py`, `question_processor.py`, `evaluate_qp.py`) | Seleksi keyword tanpa stemming, ekspansi sinonim/kode↔nama MK, reformulasi deklaratif ala Lin (2007), skrip evaluasi & ablasi | `re`, `scikit-learn` (`metrics`) |

---

## 4.X Penjelasan Implementasi Per Komponen

### 1. Normalisasi & Tokenisasi (`src/question_processing/text_utils.py`)
- **Tujuan:** Menyeragamkan huruf kapital dan tanda baca tanpa merusak kode domain atau melakukan *stemming* pada kata tanya.
- **Cuplikan kode inti:**
```python
TOKEN_RE = re.compile(
    r"[a-z]{3}\d{5}(?:-\d)?|if_cpl_[a-z0-9_]+|[a-z0-9]+/[a-z0-9]+|\d+(?:\.\d+)?|[a-z0-9]+"
)

def normalize_question(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Pertanyaan tidak boleh kosong.")
    text = question.strip().lower()
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"(?<=[a-z])-(?:nya|lah)\b", "", text)
    text = re.sub(r"\bif[\s_-]+cpl[\s_-]+([a-z]{1,2}\d)\b", r"if_cpl_\1", text)
    text = re.sub(r"[^\w\s/-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
```
- **Penjelasan:** Urutan alternatif pada `TOKEN_RE` menempatkan pola khusus (`mpk60001-5`, `if_cpl_kk1`, `ai/ml`) sebelum `[a-z0-9]+` sehingga tokenisasi tidak memecah kode MK maupun kode CPL. Akhiran `-nya` berhubung tanda hubung dihapus agar `"MK-nya"` menjadi `"mk"`.

### 2. POS Tagger Hybrid CRF + Domain Override (`train_pos_tagger.py`, `query_formulator.py`)
- **Tujuan:** Memberi label kelas kata Bahasa Indonesia untuk membantu *focus detection* dan fitur n-gram POS pada classifier.
- **Cuplikan kode inti (`pos_tag_question`):**
```python
def pos_tag_question(tokens: list[str]) -> list[tuple[str, str]]:
    if not tokens:
        return []
    tagger = _load_crf_tagger(str(_POS_MODEL_PATH))
    if tagger is None:
        raw_tagged = _fallback_pos_tag(tokens)
    else:
        preds = tagger.tag(sentence_to_features(tokens))
        raw_tagged = list(zip(tokens, preds))
    return apply_domain_pos_overrides(raw_tagged)
```
- **Penjelasan & Hasil:** Model CRF (`c1=0.1, c2=0.1, max_iterations=100`) mencapai akurasi token **97,15%** pada 1.003 kalimat uji IDN (26.367 token). Namun pada 20 pertanyaan domain kurikulum (`pos_domain_gold.tsv`), CRF mentah hanya mencapai **67,44%** karena korpus berita hanya memiliki 260 token `WH` dan tidak mengenal nama MK/kode MK. Setelah `apply_domain_pos_overrides` diterapkan, akurasi domain meningkat menjadi **94,57%** (+27,13%).

### 3. Entity Extraction, Focus Detection, & Relation Extraction (`entity_extractor.py`)
- **Tujuan:** Mengekstrak 10 tipe entitas kurikulum, menentukan *headword* pertanyaan, dan membentuk triple relasi `(predicate, subject, object)`.
- **Cuplikan kode inti (*longest-match* & anti-overlap):**
```python
def _record_match(hits, occupied, start, end, etype, value, normalized) -> None:
    if _overlaps(start, end, occupied):
        return
    occupied.append((start, end))
    hits.append((start, {"type": etype, "value": value, "normalized_value": normalized}))
```
- **Penjelasan:** Gazetteer diurutkan dari frasa terpanjang ke terpendek (`key=lambda x: -len(x[0])`). Saat memproses `"Kecerdasan Artifisial Lanjut"`, span tersebut dicatat pada `occupied` terlebih dahulu sehingga sub-frasa `"Kecerdasan Artifisial"` tidak diekstrak ganda. Pada 12 fixture resmi, ekstraksi entitas mencapai **Precision = 1,0000, Recall = 1,0000, F1 = 1,0000** (14/14 entitas tepat).

### 4. Hybrid Question Classifier & Li-Roth Answer Type (`question_classifier.py`, `answer_type_detector.py`)
- **Tujuan:** Mengklasifikasikan 21 kelas `intent`, 5 `question_category`, dan `(answer_type_coarse, answer_type)` sesuai Li & Roth (2005).
- **Penjelasan:** Lapisan *rule-based* (`classify_question_rule_only`) dijalankan terlebih dahulu untuk pola domain berpresisi tinggi; bila tidak cocok, sistem memanggil model ML terbaik hasil 5-Fold Stratified CV (`FeatureUnion`: TF-IDF kata (1,2)-gram + TF-IDF POS (1,2)-gram + fitur `HEAD_<focus>`).
- **Hasil Eksperimen Perbandingan Classifier (5-Fold CV pada 252 sampel latih):**

| Model | CV Accuracy | CV Macro-F1 |
|---|---:|---:|
| `MultinomialNB` | 0,7622 | 0,7454 |
| `LogisticRegression` | 0,8093 | 0,7983 |
| **`LinearSVC`** *(terpilih)* | **0,8728** | **0,8606** |

- **Hasil Studi Ablasi pada 63 Pertanyaan Uji Held-Out (`questions_test.json`):**

| Varian | Test Accuracy | Test Macro-F1 |
|---|---:|---:|
| Rule-based Only | 0,9206 | 0,9286 |
| ML Only (`LinearSVC`) | 0,9841 | 0,9837 |
| **Hybrid (Rule + ML)** | **0,9841** | **0,9837** |

### 5. Query Formulation & Orkestrator (`query_formulator.py`, `question_processor.py`)
- **Contoh Input–Output Aktual (`process_question`):**
  - **Input:** `"Apa prasyarat Kecerdasan Artifisial Lanjut?"`
  - **Output ringkas:**
    - `speech_act`: `"wh"`, `question_category`: `"factoid"`, `intent`: `"course_prerequisite"`
    - `answer_type_coarse`: `"ENTITY"`, `answer_type`: `"ENTITY:prerequisite"`, `focus`: `"prasyarat"`
    - `entities`: `[{"type": "course_name", "value": "kecerdasan artifisial lanjut", "normalized_value": "Kecerdasan Artifisial Lanjut"}]`
    - `relations`: `[{"predicate": "prerequisite_of", "subject": "Kecerdasan Artifisial Lanjut", "object": null}]`
    - `query_keywords`: `["prasyarat", "Kecerdasan Artifisial Lanjut", "CIF64311"]`
    - `expanded_queries`: `["syarat Kecerdasan Artifisial Lanjut CIF64311", "syarat Kecerdasan Artifisial Lanjut", "prasyarat Kecerdasan Artifisial Lanjut adalah", "CIF64311 Kecerdasan Artifisial Lanjut prasyarat"]`

---

## 4.X Analisis Kesalahan & Keterbatasan Modul

1. **Kasus kesalahan pada `questions_test.json` (1 dari 63 soal):**
   - Pertanyaan: `"Kapan libur semester genap berakhir di kalender akademik nasional?"`
   - Target: `other` → Prediksi: `course_semester` (`answer_type=NUMERIC:order`).
   - **Penyebab:** Aturan regex `semester (berapa|apa|mana|ganjil|genap)` memicu `course_semester` meskipun pertanyaan tidak menyebut entitas mata kuliah dan menanyakan kalender libur (di luar domain kurikulum).
   - **Rencana perbaikan:** Mempersyaratkan kehadiran entitas mata kuliah (atau kata `mk`/`mata kuliah`) untuk aturan `semester ganjil|genap`.
2. **Keterbatasan umum:**
   - Gazetteer hanya mengenal mata kuliah dan alias yang terdaftar pada PDF Kurikulum 2024; typo berat di luar alias belum ditangani (*fuzzy matching* belum ditambahkan agar presisi tetap tinggi).
   - `LinearSVC` tidak mengeluarkan probabilitas terkalibrasi secara langsung sehingga *confidence thresholding* hanya aktif bila model ber-`predict_proba` terpilih.

---

## Panduan Pengambilan Screenshot Bukti (`reports/screenshots/`)

Jalankan 4 perintah berikut di terminal Anda lalu simpan tangkapan layarnya ke `reports/screenshots/`:
1. `anggota3_pytest.png`: `.venv/bin/python -m pytest tests/test_question_processing.py -v`
2. `anggota3_process_question.png`: `.venv/bin/python -c "from src.question_processing.question_processor import process_question as p; import json; print(json.dumps(p('Apa prasyarat Kecerdasan Artifisial Lanjut?'), ensure_ascii=False, indent=2))"`
3. `anggota3_eval_qp.png`: `.venv/bin/python -m src.question_processing.evaluate_qp`
4. `anggota3_pos_eval.png`: `head -n 35 reports/pos_tagger_eval.txt`
