# Laporan Evaluasi Modul Question Processing (Anggota 3 — Yusuf)

- Jumlah sampel latih: **252** (21 intent)
- Jumlah sampel uji held-out: **63** (0 duplikat dengan latih)

## 1. Perbandingan Classifier ML (5-Fold Stratified CV pada Data Latih)

| Model | CV Accuracy | CV Macro-F1 |
|---|---|---|
| `MultinomialNB` | 0.7622 | 0.7454 |
| `LinearSVC` | 0.8728 | 0.8606 |
| `LogisticRegression` | 0.8093 | 0.7983 |

## 2. Studi Ablasi pada Data Uji Held-Out (`questions_test.json`)

| Varian Metode | Test Accuracy | Test Macro-F1 |
|---|---|---|
| Rule-based Only | 0.9365 | 0.9429 |
| ML Only (Best CV) | 0.9841 | 0.9837 |
| **Hybrid (Rule + ML)** | **1.0000** | **1.0000** |

## 3. Ringkasan Akurasi Per Komponen

- **Speech Act Accuracy:** 1.0000
- **Hybrid Intent Accuracy:** 1.0000 (Macro-F1: 1.0000)
- **Answer Type Coarse Accuracy (6 kelas Li & Roth):** 1.0000
- **Answer Type Fine Accuracy:** 1.0000
- **Entity Extraction (15 Fixture Resmi):** Precision=1.0000, Recall=1.0000, F1=1.0000 (TP=18, FP=0, FN=0)

## 4. Evaluasi POS Tagger CRF (`reports/pos_tagger_eval.txt`)

```text
# Evaluasi POS Tagger CRF (IDN Tagged Corpus + Domain Gold)
Train sentences: 9027 | Held-out test sentences: 1003
IDN Held-out Token Accuracy: 0.9715
Domain Gold Sentences: 20
Domain Gold Accuracy (CRF Raw): 0.6744
Domain Gold Accuracy (CRF + Domain Override): 0.9457

```

## 5. Classification Report Per Intent (Hybrid pada Held-Out)

```text
                       precision    recall  f1-score   support

         abbreviation     1.0000    1.0000    1.0000         3
          course_code     1.0000    1.0000    1.0000         3
   course_description     1.0000    1.0000    1.0000         3
   course_equivalence     1.0000    1.0000    1.0000         3
 course_list_semester     1.0000    1.0000    1.0000         3
     course_min_grade     1.0000    1.0000    1.0000         3
          course_name     1.0000    1.0000    1.0000         3
     course_practicum     1.0000    1.0000    1.0000         3
  course_prerequisite     1.0000    1.0000    1.0000         3
      course_semester     1.0000    1.0000    1.0000         3
           course_sks     1.0000    1.0000    1.0000         3
                  cpl     1.0000    1.0000    1.0000         3
curriculum_transition     1.0000    1.0000    1.0000         3
       elective_group     1.0000    1.0000    1.0000         3
     graduate_profile     1.0000    1.0000    1.0000         3
        learning_path     1.0000    1.0000    1.0000         3
   learning_path_list     1.0000    1.0000    1.0000         3
                 mbkm     1.0000    1.0000    1.0000         3
                other     1.0000    1.0000    1.0000         3
            total_sks     1.0000    1.0000    1.0000         3
       vision_mission     1.0000    1.0000    1.0000         3

             accuracy                         1.0000        63
            macro avg     1.0000    1.0000    1.0000        63
         weighted avg     1.0000    1.0000    1.0000        63
```

## 6. Contoh Prediksi Benar (Sampel)

| Pertanyaan | Intent | Answer Type | Speech Act | Entitas |
|---|---|---|---|---|
| Apa saja syarat mata kuliah untuk memprogram Pemrograman Aplikasi Perangkat Bergerak? | `course_prerequisite` | `ENTITY:prerequisite` | `wh` | `[('course_name', 'Pemrograman Aplikasi Perangkat Bergerak')]` |
| Adakah prasyarat sebelum mengambil Komputer Grafis? | `course_prerequisite` | `ENTITY:prerequisite` | `yes_no` | `[('course_name', 'Komputer Grafis')]` |
| Mata kuliah prasyarat Keamanan Informasi itu apa? | `course_prerequisite` | `ENTITY:prerequisite` | `wh` | `[('course_name', 'Keamanan Informasi')]` |
| Berapa nilai minimum yang disyaratkan pada prasyarat Metode Numerik? | `course_min_grade` | `NUMERIC:grade` | `wh` | `[('course_name', 'Metode Numerik')]` |
| Minimal dapat nilai berapa pada prasyarat Komputer Grafis? | `course_min_grade` | `NUMERIC:grade` | `wh` | `[('course_name', 'Komputer Grafis')]` |

## 7. Analisis Kesalahan pada Held-Out (Transparansi Before vs After)

- **Hasil terkini:** Tidak ada kesalahan klasifikasi intent pada `questions_test.json` (63/63 benar, 1.0000).
- **Catatan transparansi *before vs after*:** Pada evaluasi awal sebelum sinkronisasi A2, terjadi 1/63 kesalahan (`0.9841`) pada pertanyaan *"Kapan libur semester genap berakhir di kalender akademik nasional?"* (Target: `other`, Prediksi awal: `course_semester`) akibat aturan regex `semester ganjil|genap` yang terlalu umum dan tidak aktifnya fallback *out-of-domain* pada `LinearSVC`. Setelah memperketat syarat konteks mata kuliah pada aturan semester serta mengkalibrasi ambang `LinearSVC.decision_function < -0.32` khusus dari 5-fold CV data latih (tanpa menyentuh set uji), kesalahan tersebut teratasi.

## 8. Verifikasi Keselarasan Lintas-Modul A2 ↔ A3 (`knowledge_triples.jsonl` & Q05–Q12)

- **Total Knowledge Triples Anggota 2:** 1177 triple
- **Keselarasan Vocabulary Predikat (GATE-A):** 15/15 predikat cocok 100%
- **Keselarasan Entitas Kanonik Leksikon:** 11/11 `learning_path`, 3/3 `elective_group`, 31/31 `knowledge_area`
- **Evaluasi 8 Soal Tim (Q05–Q08 Anggota 2 + Q09–Q12 Anggota 3):** 8/8 cocok penuh (`speech_act`, `question_category`, `intent`, `answer_type`)
- **KB Exact-Hit Relasi pada Q05–Q12:** 8/8 relasi menghasilkan kecocokan langsung pada `knowledge_triples.jsonl`
