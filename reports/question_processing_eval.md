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
| Rule-based Only | 0.9206 | 0.9286 |
| ML Only (Best CV) | 0.9841 | 0.9837 |
| **Hybrid (Rule + ML)** | **0.9841** | **0.9837** |

## 3. Ringkasan Akurasi Per Komponen

- **Speech Act Accuracy:** 1.0000
- **Hybrid Intent Accuracy:** 0.9841 (Macro-F1: 0.9837)
- **Answer Type Coarse Accuracy (6 kelas Li & Roth):** 1.0000
- **Answer Type Fine Accuracy:** 0.9841
- **Entity Extraction (12 Fixture Resmi):** Precision=1.0000, Recall=1.0000, F1=1.0000 (TP=14, FP=0, FN=0)

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
      course_semester     0.7500    1.0000    0.8571         3
           course_sks     1.0000    1.0000    1.0000         3
                  cpl     1.0000    1.0000    1.0000         3
curriculum_transition     1.0000    1.0000    1.0000         3
       elective_group     1.0000    1.0000    1.0000         3
     graduate_profile     1.0000    1.0000    1.0000         3
        learning_path     1.0000    1.0000    1.0000         3
   learning_path_list     1.0000    1.0000    1.0000         3
                 mbkm     1.0000    1.0000    1.0000         3
                other     1.0000    0.6667    0.8000         3
            total_sks     1.0000    1.0000    1.0000         3
       vision_mission     1.0000    1.0000    1.0000         3

             accuracy                         0.9841        63
            macro avg     0.9881    0.9841    0.9837        63
         weighted avg     0.9881    0.9841    0.9837        63
```

## 6. Contoh Prediksi Benar (Sampel)

| Pertanyaan | Intent | Answer Type | Speech Act | Entitas |
|---|---|---|---|---|
| Apa saja syarat mata kuliah untuk memprogram Pemrograman Aplikasi Perangkat Bergerak? | `course_prerequisite` | `ENTITY:prerequisite` | `wh` | `[('course_name', 'Pemrograman Aplikasi Perangkat Bergerak')]` |
| Adakah prasyarat sebelum mengambil Komputer Grafis? | `course_prerequisite` | `ENTITY:prerequisite` | `yes_no` | `[('course_name', 'Komputer Grafis')]` |
| Mata kuliah prasyarat Keamanan Informasi itu apa? | `course_prerequisite` | `ENTITY:prerequisite` | `wh` | `[('course_name', 'Keamanan Informasi')]` |
| Berapa nilai minimum yang disyaratkan pada prasyarat Metode Numerik? | `course_min_grade` | `NUMERIC:grade` | `wh` | `[('course_name', 'Metode Numerik')]` |
| Minimal dapat nilai berapa pada prasyarat Komputer Grafis? | `course_min_grade` | `NUMERIC:grade` | `wh` | `[('course_name', 'Komputer Grafis')]` |

## 7. Analisis Kesalahan pada Held-Out

- **Pertanyaan:** "Kapan libur semester genap berakhir di kalender akademik nasional?" — Target: `other`, Prediksi: `course_semester` (`answer_type=NUMERIC:order`)
