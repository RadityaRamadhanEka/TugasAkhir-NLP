# Draf Bahan Bab II — Tinjauan Pustaka (Bagian Anggota 3: Question Processing)

> **Catatan Penulis (Yusuf):** Dokumen ini berisi kerangka terstruktur, poin-poin teknis yang benar-benar diimplementasikan pada `src/question_processing/`, serta daftar referensi yang telah diverifikasi metadata-nya melalui Crossref/OpenAlex. Tulis ulang kalimat menjadi prosa akademik Anda sendiri saat menggabungkan Bab II bersama Anggota 4 (Azza).

---

## Kerangka Subbab (Hanya Teknik yang Diimplementasikan)

### 2.1 Arsitektur Question Answering (IR-Based & Hybrid KB-QA)
- Gambarkan posisi tahap *Question Processing* sebagai komponen hulu dalam arsitektur *Question Answering* klasik menurut Jurafsky & Martin (2009) serta materi perkuliahan PBA14 (Slide 33–35, 75).
- Jelaskan fungsi utamanya: menerima pertanyaan bahasa alami, mengekstrak representasi semantik (maksud/intent, *speech act*, *expected answer type*, *focus*, entitas, dan relasi), serta merumuskan kueri yang siap dikonsumsi *Passage Retrieval* dan *Knowledge Base Retrieval*.

### 2.2 Normalisasi dan Tokenisasi Teks Bahasa Indonesia
- Jelaskan mengapa normalisasi pertanyaan berbeda dari normalisasi dokumen korpus: pertanyaan berukuran pendek sehingga *stemming* tidak diterapkan pada *query keywords* maupun input classifier agar akhiran gramatikal dan konteks kata tanya tetap terjaga.
- Jelaskan kebutuhan tokenisasi berbasis *regular expression* untuk menjaga keutuhan pola domain seperti kode mata kuliah (`CIF63110`, `MPK60001-5`), kode CPL (`IF_CPL_KK1`), dan istilah bergaris miring (`ai/ml`).

### 2.3 Part-of-Speech (POS) Tagging & Conditional Random Fields (CRF)
- Jelaskan konsep *sequence labeling* dengan *Conditional Random Fields* (CRF) oleh Lafferty, McCallum & Pereira (2001) serta keunggulan CRF (model diskriminatif berbasis fitur lokal & morfologi tanpa asumsi independensi observasi yang ketat seperti HMM).
- Jelaskan implementasi efisien via `CRFsuite` (Okazaki, 2007) yang dibungkus `python-crfsuite`.
- Jelaskan tagset POS Bahasa Indonesia dan korpus beranotasi manual UI (`idn-tagged-corpus`, 10.030 kalimat) dari Dinakaramani dkk. (2014), termasuk alasan penggunaan label `WH` untuk kata tanya dan perlunya *domain lexicon override* karena frekuensi `WH` pada korpus berita sangat kecil (260 token dari >250.000 token).

### 2.4 Regular Expression dan Klasifikasi Berbasis Aturan (*Rule-Based*)
- Jelaskan peran ekspresi reguler (*regex*) dan aturan deterministik dalam mendeteksi *question speech act* (`wh`, `yes_no`, `command`, `indirect_request` — PBA14 Slide 17) serta pola domain spesifik yang presisi tinggi (misalnya singkatan, kode MK, aturan peralihan).

### 2.5 Klasifikasi Teks Terawasi (*Supervised Machine Learning*) & Pembobotan TF-IDF
- Jelaskan representasi fitur gabungan (*feature engineering*): TF-IDF unigram & bigram kata (Salton/scikit-learn), n-gram urutan POS tag, dan *headword* (*focus*).
- Jelaskan tiga algoritma klasik yang dibandingkan melalui *Stratified k-fold Cross Validation* menggunakan `scikit-learn` (Pedregosa dkk., 2011):
  1. **Multinomial Naive Bayes** (probabilistik generatif dengan asumsi independensi fitur bersyarat).
  2. **Linear Support Vector Machine (`LinearSVC`)** (mencari *hyperplane* pemisah bermargin maksimum pada ruang fitur berdimensi tinggi yang jarang/*sparse*).
  3. **Logistic Regression** (regresi log-linear multikelas dengan keluaran probabilitas terkalibrasi).

### 2.6 Question Classification & Taksonomi Answer Type Li & Roth
- Jelaskan konsep *Question Classification* dalam menentukan *Expected Answer Type* menurut Li & Roth (2002; 2006), yaitu taksonomi hierarkis dua tingkat (*coarse-grained* dan *fine-grained*) dengan 6 kelas utama (`ABBREVIATION`, `ENTITY`, `DESCRIPTION`, `HUMAN`, `LOCATION`, `NUMERIC`).
- Jelaskan adaptasi subkelas *fine-grained* ke domain Kurikulum 2024 TIF UB (misalnya `NUMERIC:order` untuk semester, `NUMERIC:code` untuk kode MK, `NUMERIC:grade` untuk nilai minimum prasyarat, `ENTITY:prerequisite`, `ENTITY:course_list`, `DESCRIPTION:manner` untuk aturan peralihan).

### 2.7 Question Focus (*Headword*)
- Jelaskan definisi *question focus* atau *question headword* (kata atau frasa nominal yang merujuk pada entitas/atribut yang dicari dan menggantikan jawaban pada kalimat deklaratif — PBA14 Slide 36 & 44), serta aturan berbasis POS untuk mengekstraksinya.

### 2.8 Named Entity Recognition Berbasis Gazetteer & Relation Extraction Sederhana
- Jelaskan perbedaan NER statistik dan pendekatan berbasis aturan + kamus (*gazetteer*) dengan strategi *longest-match* pada domain tertutup (daftar mata kuliah, kode CPL, *learning path*, dan kelompok pilihan).
- Jelaskan ekstraksi relasi semantik biner `(predicate, subject, object)` dari pertanyaan untuk mendukung jalur *Knowledge-Based QA* (PBA14 Slide 35, 37, 69).

### 2.9 Query Formulation, Synonym Expansion, dan Declarative Reformulation
- Jelaskan pembentukan *query keywords* (penghapusan stopword selektif tanpa menghilangkan negasi `tidak` maupun angka), *query expansion* dengan sinonim/singkatan domain, serta *query reformulation* ke pola kalimat deklaratif mengikuti gagasan *redundancy-based QA* Lin (2007) (PBA14 Slide 47).

### 2.10 Metrik Evaluasi Modul Question Processing
- Jelaskan rumus dan fungsi *Accuracy*, *Precision*, *Recall*, *F1-score*, *Macro-F1* (penting pada klasifikasi multikelas agar kelas berjumlah kecil mendapat bobot setara), serta *Stratified 5-Fold Cross Validation*.

### 2.11 Studi Terkait QA & Question Classification Bahasa Indonesia
Ringkas dan kaitkan minimal 3 penelitian berikut (seluruhnya terverifikasi di Crossref):
1. **Suwarningsih, Purwarianti & Supriana (2015)** — menerapkan *pattern matching* untuk klasifikasi pertanyaan domain medis berbahasa Indonesia; relevan dengan lapisan *rule-based* pada klasifikasi pertanyaan kurikulum.
2. **Thalib, Widyawan & Soesanti (2023)** — meneliti *Indonesian question classification* dengan seleksi dan ekstraksi fitur pada taksonomi *coarse* dan *fine* (model Li & Roth); relevan langsung dengan pemetaan *answer type* dua tingkat dan fitur TF-IDF + POS.
3. **Abdiansah, Azhari & Sari (2018)** — mengulas arsitektur dan validasi jawaban pada *Indonesian Question Answering System* (IQAS), menyoroti peran analisis pertanyaan dan penentuan *expected answer type* terhadap kualitas jawaban akhir.

---

## Daftar Referensi (Harvard Anglia Ruskin — Terverifikasi)

- Abdiansah, A., Azhari, A. & Sari, A.K. (2018) 'Survey on Answer Validation for Indonesian Question Answering System (IQAS)', *International Journal of Intelligent Systems and Applications*, 10(4), pp. 68–78. doi: 10.5815/ijisa.2018.04.08.
- Dinakaramani, A., Rashel, F., Luthfi, A. & Manurung, R. (2014) 'Designing an Indonesian part of speech tagset and manually tagged Indonesian corpus', in *2014 International Conference on Asian Language Processing (IALP)*. IEEE, pp. 66–69. doi: 10.1109/ialp.2014.6973519.
- Jurafsky, D. & Martin, J.H. (2009) *Speech and Language Processing: An Introduction to Natural Language Processing, Computational Linguistics, and Speech Recognition*. 2nd edn. Upper Saddle River, NJ: Pearson Prentice Hall.
- Lafferty, J., McCallum, A. & Pereira, F. (2001) 'Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data', in *Proceedings of the Eighteenth International Conference on Machine Learning (ICML 2001)*. San Francisco, CA: Morgan Kaufmann, pp. 282–289.
- Li, X. & Roth, D. (2002) 'Learning question classifiers', in *COLING 2002: Proceedings of the 19th International Conference on Computational Linguistics*, Vol. 1, pp. 1–7. doi: 10.3115/1072228.1072378.
- Li, X. & Roth, D. (2006) 'Learning question classifiers: the role of semantic information', *Natural Language Engineering*, 12(3), pp. 229–249. doi: 10.1017/s1351324905003955.
- Lin, J. (2007) 'An exploration of the principles underlying redundancy-based factoid question answering', *ACM Transactions on Information Systems*, 25(2), Article 6. doi: 10.1145/1229179.1229180.
- Okazaki, N. (2007) *CRFsuite: a fast implementation of Conditional Random Fields (CRFs)* [Software]. Available at: http://www.chokkan.org/software/crfsuite/ *(rujukan perangkat lunak tanpa DOI resmi; cek tanggal akses bila dicantumkan)*.
- Pedregosa, F. et al. (2011) 'Scikit-learn: Machine Learning in Python', *Journal of Machine Learning Research*, 12, pp. 2825–2830. doi: 10.5555/1953048.2078195.
- Suwarningsih, W., Purwarianti, A. & Supriana, I. (2015) 'Indonesian medical question classification with pattern matching', in *2015 International Conference on Automation, Cognitive Science, Optics, Micro Electro-Mechanical System, and Information Technology (ICACOMIT)*. IEEE, pp. 106–109. doi: 10.1109/icacomit.2015.7440185.
- Thalib, I., Widyawan & Soesanti, I. (2023) 'Indonesian question classification using feature extraction and selection approach on coarse and fine taxonomy', *AIP Conference Proceedings*, 2675, 020007. doi: 10.1063/5.0114188.
