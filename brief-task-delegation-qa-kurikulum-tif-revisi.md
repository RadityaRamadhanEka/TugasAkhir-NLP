# Brief Task Delegation
## Proyek Akhir Pemrosesan Bahasa Alami (NLP)
### Sistem Question Answering Kurikulum 2024 Teknik Informatika Universitas Brawijaya

> Dokumen kerja untuk pembagian tanggung jawab coding dan dokumentasi kelompok beranggotakan lima orang.

---

## 1. Ringkasan Proyek

| Komponen | Keterangan |
|---|---|
| Mata kuliah | Pemrosesan Bahasa Alami (NLP) |
| Jenis proyek | Question Answering Sederhana (Tanpa LLM) |
| Topik | Sistem Question Answering Kurikulum Teknik Informatika UB |
| Korpus utama | *Buku Pedoman Pelaksanaan Kurikulum 2024 Teknik Informatika* |
| Format sumber | PDF, sekitar 100 halaman, berisi teks, tabel, gambar, diagram, dan grafik |
| Bahasa implementasi | Python |
| Jumlah anggota | 5 orang |
| Pendekatan | Classic NLP, information retrieval, dan ekstraksi jawaban berbasis aturan/statistik |

### Tujuan sistem

Membangun sistem yang dapat menerima pertanyaan pengguna mengenai Kurikulum 2024 Program Studi Teknik Informatika UB, menemukan bagian dokumen yang relevan, lalu memberikan jawaban faktual berdasarkan isi dokumen.

Contoh jenis pertanyaan:
- Apa saja mata kuliah wajib pada semester 3?
- Berapa total SKS mata kuliah muatan program studi?
- Apa prasyarat untuk mengambil Kecerdasan Artifisial Lanjut?
- Mata kuliah pilihan apa saja yang termasuk kelompok Perekayasa Komputasi Cerdas?
- Apa perbedaan aturan peralihan kurikulum untuk mahasiswa semester 3 dan semester 5?
- Learning path apa saja yang dijelaskan dalam pedoman?

Sistem harus menyertakan sumber jawaban, sekurang-kurangnya berupa nomor halaman dan/atau bagian dokumen, agar jawaban dapat diverifikasi.

## 2. Batasan dan Prinsip Teknis

1. **Tidak menggunakan LLM** untuk memahami pertanyaan, melakukan retrieval, atau menghasilkan jawaban.
2. Boleh menggunakan library NLP/Python seperti NLTK, spaCy, scikit-learn, PyMuPDF, pdfplumber, Camelot/Tabula, Tesseract, atau library lain yang relevan. Setiap library harus dijelaskan fungsi dan penggunaannya.
3. Implementasi harus memperlihatkan penerapan materi NLP perkuliahan, bukan hanya pencarian dokumen biasa. Materi yang dapat dipertimbangkan:
   - tokenization dan text normalization;
   - stopword removal dan stemming/lemmatization jika sesuai;
   - POS tagging;
   - regex dan rule-based question classification;
   - named entity recognition atau entity/rule extraction;
   - answer type detection;
   - passage retrieval dan ranking;
   - answer extraction dan answer ranking.
4. Pilih teknik yang benar-benar dapat dijelaskan dan dievaluasi. Tidak semua teknik di atas harus digunakan.
5. Dokumen PDF mengandung teks, tabel, serta gambar/diagram/grafik. Ekstraksi tabel harus diprioritaskan karena informasi kurikulum banyak disajikan dalam bentuk tabel.
6. Untuk gambar/diagram/grafik, lakukan inventarisasi. Gunakan OCR atau transkripsi/representasi tekstual terstruktur bila informasi di dalamnya diperlukan untuk menjawab pertanyaan. Jangan mengklaim sistem memahami seluruh informasi visual jika kontennya belum berhasil diekstrak.
7. Jawaban harus dibatasi pada informasi yang ditemukan dalam korpus. Jika bukti tidak cukup atau skor relevansi di bawah ambang batas, sistem harus menyatakan bahwa jawaban tidak ditemukan/tidak cukup informasi.
8. Setiap data hasil ekstraksi perlu mempertahankan metadata sumber, terutama nomor halaman, judul bagian, dan jenis konten (teks/tabel/visual).

## 3. Usulan Arsitektur Sistem

```text
PDF Kurikulum 2024
        |
        v
Document Ingestion
(Text / Table / Visual Extraction)
        |
        v
Preprocessing & Structuring
(Cleaning, Normalization, Metadata, Passage Creation)
        |
        v
Corpus / Passage Index
        |
        +--------------------------------------+
                                               |
User Question                                  |
        |                                      |
        v                                      |
Question Processing                           |
(Tokenization, Classification,                |
 Entity Extraction, Answer Type Detection)    |
        |                                      |
        v                                      |
Passage Retrieval <----------------------------+
(TF-IDF / BM25 / Keyword & Rule Matching)
        |
        v
Candidate Passage Ranking
        |
        v
Answer Extraction & Processing
(Rule-based / Pattern-based / Candidate Ranking)
        |
        v
Confidence / Evidence Check
        |
        v
Answer + Source Page / Section
```

**Catatan:** TF-IDF atau BM25 dapat digunakan sebagai metode retrieval, tetapi harus dilengkapi komponen NLP seperti question classification, POS tagging, entity extraction, answer type detection, atau teknik lain yang relevan. Pemilihan final metode dan library harus diputuskan bersama setelah eksplorasi dokumen.

## 4. Pembagian Tanggung Jawab Lima Anggota

Nama anggota dapat diisi setelah kelompok menyepakati pembagian. Setiap anggota menjadi *owner* untuk satu modul utama dan bertanggung jawab menulis dokumentasi modul tersebut.

### Anggota 1 — Document Ingestion & PDF Extraction

**Fokus:** Mengubah PDF menjadi data digital terstruktur yang dapat diproses modul selanjutnya.

#### Coding Task
- Memeriksa struktur dan karakteristik PDF: halaman, teks, tabel, gambar, diagram, grafik, header/footer, serta kualitas teks.
- Membuat pipeline ekstraksi teks per halaman.
- Mengekstrak tabel-tabel penting, termasuk tabel struktur mata kuliah, distribusi semester, SKS, prasyarat, learning path, perubahan kurikulum, dan kegiatan Merdeka Belajar.
- Menginventarisasi gambar/diagram/grafik dan menentukan mana yang relevan untuk QA.
- Melakukan OCR atau transkripsi terstruktur untuk visual yang diperlukan dan memungkinkan untuk diproses.
- Menyimpan hasil ekstraksi dalam format terstruktur (misalnya JSON/CSV/TXT) dengan metadata halaman dan bagian.
- Membuat laporan kualitas ekstraksi: halaman/tabel/visual yang berhasil dan gagal diekstrak.

**Output coding**
- `document_loader.py`
- `extract_text.py`
- `extract_tables.py`
- `extract_visuals.py` atau modul OCR bila digunakan
- `data/raw/` dan `data/extracted/`
- Contoh hasil ekstraksi beserta metadata sumber

#### Documentation Task
- **Bab III:** Sumber data, karakteristik korpus, prosedur pengumpulan, dan proses ekstraksi dokumen.
- **Bab IV:** Implementasi document ingestion, teknik/library yang digunakan, penanganan teks/tabel/visual, serta contoh hasil ekstraksi.
- Menyediakan screenshot atau contoh keluaran ekstraksi untuk laporan.

---

### Anggota 2 — Text Preprocessing, Structuring & Passage Dataset

**Fokus:** Membersihkan dan mengubah hasil ekstraksi menjadi korpus/passage yang siap diindeks.

#### Coding Task
- Membersihkan artefak PDF seperti nomor halaman yang tersisip, spasi berlebih, pemenggalan baris, dan karakter yang tidak diperlukan.
- Menormalisasi teks tanpa menghilangkan informasi penting seperti kode mata kuliah, angka SKS, semester, nilai prasyarat, dan singkatan.
- Menyusun konten menjadi unit yang bermakna: paragraf, subbagian, baris/record tabel, atau passage.
- Menentukan strategi pemisahan passage agar konteks tabel tidak terputus (misalnya menyimpan judul tabel dan nama kolom bersama record).
- Menambahkan metadata: halaman, bab/subbab, judul tabel, tipe konten, dan identifier passage.
- Menyusun dataset korpus final yang digunakan oleh retrieval.
- Membuat pemeriksaan kualitas data: passage kosong, duplikat, metadata hilang, dan informasi tabel yang terpotong.

**Output coding**
- `preprocessing.py`
- `passage_builder.py`
- `corpus_validator.py`
- `data/processed/`
- Dataset passage final (JSON/JSONL/CSV sesuai kesepakatan)

#### Documentation Task
- **Bab III:** Tahapan preprocessing, normalisasi, pembentukan passage, metadata, dan struktur dataset.
- **Bab IV:** Implementasi preprocessing dan passage construction, alasan pemilihan aturan, serta contoh sebelum-sesudah.
- Menyediakan statistik korpus (jumlah halaman yang diproses, passage, tabel/record, dan distribusi tipe konten).

---

### Anggota 3 — Question Processing & NLP Analysis

**Fokus:** Memproses pertanyaan pengguna agar sistem mengetahui maksud pertanyaan dan tipe jawaban yang diharapkan.

#### Coding Task
- Menyusun kategori pertanyaan yang sesuai dengan isi dokumen, misalnya:
  - definisi/deskripsi;
  - daftar mata kuliah;
  - jumlah SKS;
  - semester;
  - prasyarat;
  - learning path;
  - aturan peralihan;
  - CPL/profil lulusan.
- Membuat question classification/intent classification berbasis aturan, pola kata, atau metode statistik sederhana.
- Melakukan tokenization dan normalisasi pertanyaan.
- Menggunakan POS tagging bila relevan untuk mengidentifikasi struktur pertanyaan.
- Membuat entity/keyword extraction untuk entitas seperti nama mata kuliah, kode MK, semester, SKS, CPL, dan learning path.
- Membuat answer type detection, misalnya tipe jawaban berupa angka/SKS, nama mata kuliah, daftar, semester, atau deskripsi.
- Menghasilkan representasi pertanyaan yang dapat digunakan oleh retrieval dan answer extraction.

**Output coding**
- `question_processor.py`
- `question_classifier.py`
- `entity_extractor.py`
- `answer_type_detector.py`
- Kumpulan contoh pertanyaan dan hasil analisisnya

#### Documentation Task
- **Bab II:** Landasan teori yang berkaitan dengan teknik NLP yang benar-benar digunakan, seperti tokenization, POS tagging, rule-based classification, NER/entity extraction, dan answer type detection.
- **Bab III:** Rancangan dan alur question processing.
- **Bab IV:** Implementasi setiap komponen, aturan/pola yang dibuat, contoh input-output, dan keterbatasannya.

---

### Anggota 4 — Passage Retrieval & Ranking

**Fokus:** Menemukan passage yang paling relevan terhadap pertanyaan pengguna.

#### Coding Task
- Menentukan dan mengimplementasikan metode retrieval klasik, misalnya TF-IDF dengan cosine similarity atau BM25.
- Menyusun indeks dari dataset passage hasil preprocessing.
- Mengintegrasikan token/entitas/intent hasil question processing sebagai sinyal tambahan jika diperlukan.
- Mengimplementasikan retrieval top-k dan ranking passage.
- Menangani istilah penting yang sensitif terhadap format, seperti kode mata kuliah, angka SKS, semester, dan nama learning path.
- Mengembalikan passage beserta skor relevansi dan metadata sumber.
- Menentukan cara menangani hasil retrieval yang tidak relevan atau memiliki skor rendah.
- Menyiapkan pengujian retrieval menggunakan contoh query dan relevansi passage.

**Output coding**
- `retriever.py`
- `index_builder.py`
- `ranking.py`
- Indeks/artefak retrieval yang diperlukan
- Hasil pengujian retrieval awal

#### Documentation Task
- **Bab II:** Landasan teori metode retrieval yang dipilih, misalnya TF-IDF, cosine similarity, atau BM25.
- **Bab III:** Rancangan passage retrieval, pembentukan indeks, ranking, dan penentuan top-k.
- **Bab IV:** Implementasi retrieval, parameter yang digunakan, contoh hasil ranking, serta analisis keterbatasan.

---

### Anggota 5 — Answer Extraction, System Integration & Evaluation

**Fokus:** Mengambil jawaban dari passage terpilih, mengintegrasikan modul, dan menguji sistem secara menyeluruh.

#### Coding Task
- Merancang strategi answer extraction berbasis aturan/pola sesuai answer type.
- Mengambil kandidat jawaban dari passage hasil retrieval, bukan menghasilkan jawaban bebas tanpa bukti.
- Menggunakan informasi question classification dan answer type detection untuk memilih pola ekstraksi yang sesuai.
- Melakukan candidate answer ranking atau pemilihan kandidat berdasarkan kecocokan pola, kata kunci, dan konteks.
- Menambahkan evidence/source tracking: nomor halaman, bagian, atau tabel asal jawaban.
- Membuat mekanisme fallback jika jawaban tidak ditemukan atau bukti tidak cukup.
- Mengintegrasikan seluruh modul menjadi alur QA yang dapat dijalankan.
- Membuat antarmuka sederhana (CLI atau web sederhana) bila waktu memungkinkan.
- Menyiapkan script pengujian dan rekap hasil evaluasi.

**Output coding**
- `answer_extractor.py`
- `answer_ranker.py`
- `qa_pipeline.py` atau `main.py`
- `evaluation.py`
- Antarmuka sederhana bila disepakati
- Hasil evaluasi dan log pengujian

#### Documentation Task
- **Bab III:** Rancangan answer extraction, integrasi sistem, dan metodologi evaluasi.
- **Bab IV:** Implementasi answer processing dan integrasi seluruh modul.
- **Bab V:** Prosedur pengujian, hasil, analisis jawaban benar/salah, contoh kegagalan, dan keterbatasan sistem.
- Menyusun rekap evaluasi bersama seluruh anggota.

---

## 5. Tanggung Jawab Bersama

Pembagian owner modul tidak berarti anggota lain bebas dari keseluruhan proyek. Pekerjaan berikut dilakukan bersama.

| Aktivitas | Pembagian tanggung jawab |
|---|---|
| Menentukan batasan masalah dan jenis pertanyaan | Semua anggota |
| Meninjau isi PDF dan menyepakati cakupan korpus | Semua anggota |
| Menyepakati format data dan interface antar-modul | Semua anggota; Anggota 1–4 menyiapkan spesifikasi modul, Anggota 5 mengoordinasikan integrasi |
| Menyusun rumusan masalah, tujuan, dan manfaat | Semua anggota; satu anggota menjadi editor |
| Studi literatur | Setiap anggota mencari referensi untuk metode yang menjadi tanggung jawabnya |
| Membuat 20 pertanyaan evaluasi | Setiap anggota membuat 4 pertanyaan beserta jawaban acuan dan halaman sumber |
| Memvalidasi ground truth | Semua anggota melakukan pemeriksaan silang |
| Menjalankan pengujian akhir | Semua anggota |
| Menyusun abstrak dan Bab VI | Semua anggota; editor laporan menggabungkan hasil |
| Review laporan dan kode | Semua anggota |
| Menyiapkan presentasi/demo jika diminta | Semua anggota |

**Ketentuan 20 pertanyaan:** Panduan tugas meminta 20 daftar pertanyaan dan menyatakan setiap anggota membuat pertanyaan. Dengan lima anggota, target pembagian adalah 4 pertanyaan per anggota. Setiap pertanyaan harus memiliki:
- pertanyaan;
- jawaban acuan (*ground truth*);
- halaman dan/atau bagian sumber;
- tipe pertanyaan;
- kriteria jawaban benar (termasuk variasi jawaban yang dapat diterima jika relevan).

Pertanyaan harus bervariasi, tidak hanya menanyakan fakta sederhana. Usahakan mencakup teks naratif, tabel, dan konten visual yang memang berhasil diekstrak.

## 6. Pembagian Penulisan Laporan

Struktur berikut mengikuti panduan tugas akhir NLP.

| Bagian laporan | Penanggung jawab utama | Kontributor |
|---|---|---|
| Sampul dan identitas kelompok | Anggota 5 | Semua anggota |
| Lembar tanggung jawab anggota | Anggota 5 | Semua anggota memeriksa |
| Abstrak | Anggota 5 sebagai editor | Semua anggota menyediakan ringkasan hasil |
| Bab I — Pendahuluan | Anggota 5 sebagai koordinator | Semua anggota memberi masukan |
| Bab II — Tinjauan Pustaka | Anggota 3 dan 4 | Anggota 1, 2, dan 5 untuk teori modul masing-masing |
| Bab III — Metodologi Penelitian | Anggota 5 sebagai koordinator | Anggota 1–4 menulis metode modul masing-masing |
| Bab IV — Implementasi | Setiap anggota menulis implementasi modulnya | Anggota 5 menyatukan format dan alur |
| Bab V — Hasil dan Pembahasan | Anggota 5 | Semua anggota menyediakan hasil pengujian modul dan analisis |
| Bab VI — Penutup | Anggota 5 sebagai editor | Semua anggota memeriksa kesesuaian kesimpulan |
| Daftar Referensi | Setiap anggota memasukkan referensinya | Anggota 5 memeriksa konsistensi format |

**Penting:** Penanggung jawab utama adalah koordinator/editor, bukan satu-satunya penulis. Isi teknis setiap modul harus ditulis dan dapat dipertanggungjawabkan oleh anggota yang mengimplementasikannya.

## 7. Kontrak Interface Antar-Modul

Agar pengerjaan dapat berlangsung paralel, format input-output perlu disepakati sejak awal. Contoh kontrak awal:

### 7.1 Format passage korpus

```json
{
  "passage_id": "p_0001",
  "text": "CIF63110 Kecerdasan Artifisial ...",
  "source_page": 20,
  "section": "6. Struktur Kurikulum",
  "content_type": "table",
  "table_title": "Distribusi Mata Kuliah Semester 3",
  "metadata": {
    "semester": 3,
    "course_code": "CIF63110"
  }
}
```

### 7.2 Output question processing

```json
{
  "original_question": "Apa prasyarat Kecerdasan Artifisial Lanjut?",
  "normalized_question": "prasyarat kecerdasan artifisial lanjut",
  "intent": "course_prerequisite",
  "entities": [
    {
      "type": "course_name",
      "value": "Kecerdasan Artifisial Lanjut"
    }
  ],
  "answer_type": "prerequisite"
}
```

### 7.3 Output retrieval

```json
{
  "query": "prasyarat kecerdasan artifisial lanjut",
  "results": [
    {
      "passage_id": "p_0002",
      "score": 0.87,
      "text": "..."
    }
  ]
}
```

### 7.4 Output answer processing

```json
{
  "question": "Apa prasyarat Kecerdasan Artifisial Lanjut?",
  "answer": "Kecerdasan Artifisial dengan nilai minimum C.",
  "source": {
    "passage_id": "p_0002",
    "page": 20,
    "section": "Struktur Kurikulum"
  },
  "confidence": 0.87,
  "status": "answered"
}
```

Format tersebut hanya contoh awal. Kelompok boleh mengubah skema selama disepakati semua pemilik modul. Hindari perubahan format sepihak setelah integrasi dimulai.

## 8. Rencana Integrasi dan Milestone

| Milestone | Target keluaran | Owner utama |
|---|---|---|
| M1 — Project setup | Struktur repository, environment, pembagian modul, format data disepakati | Semua anggota |
| M2 — Corpus extraction | Teks, tabel, dan inventarisasi visual berhasil diekstrak | Anggota 1 |
| M3 — Processed corpus | Korpus bersih, passage, dan metadata tersedia | Anggota 2 |
| M4 — Question processing | Klasifikasi pertanyaan, entity, dan answer type berjalan | Anggota 3 |
| M5 — Retrieval | Indeks dan top-k passage retrieval berjalan | Anggota 4 |
| M6 — Answer extraction | Kandidat jawaban dan source tracking berjalan | Anggota 5 |
| M7 — End-to-end integration | Pertanyaan dapat diproses sampai jawaban dan sumber ditampilkan | Semua anggota; Anggota 5 mengoordinasikan |
| M8 — Evaluation | 20 pertanyaan, ground truth, hasil benar/salah, dan analisis tersedia | Semua anggota |
| M9 — Report finalization | Laporan, source code, korpus, dan berkas pendukung siap dikumpulkan | Semua anggota |

Urutan milestone adalah dependensi teknis, bukan berarti anggota berikutnya harus menunggu seluruh pekerjaan sebelumnya selesai. Pengembangan dapat dilakukan dengan data contoh dan interface sementara selama formatnya disepakati.

## 9. Rekomendasi Struktur Repository

```text
qa-kurikulum-tif/
├── README.md
├── requirements.txt
├── main.py
├── config/
│   └── settings.py
├── data/
│   ├── raw/
│   ├── extracted/
│   ├── processed/
│   └── evaluation/
├── src/
│   ├── document_ingestion/
│   │   ├── document_loader.py
│   │   ├── extract_text.py
│   │   ├── extract_tables.py
│   │   └── extract_visuals.py
│   ├── preprocessing/
│   │   ├── preprocessing.py
│   │   ├── passage_builder.py
│   │   └── corpus_validator.py
│   ├── question_processing/
│   │   ├── question_processor.py
│   │   ├── question_classifier.py
│   │   ├── entity_extractor.py
│   │   └── answer_type_detector.py
│   ├── retrieval/
│   │   ├── index_builder.py
│   │   ├── retriever.py
│   │   └── ranking.py
│   ├── answer_processing/
│   │   ├── answer_extractor.py
│   │   └── answer_ranker.py
│   └── pipeline/
│       └── qa_pipeline.py
├── tests/
│   ├── test_ingestion.py
│   ├── test_preprocessing.py
│   ├── test_question_processing.py
│   ├── test_retrieval.py
│   └── test_answer_processing.py
├── reports/
│   ├── evaluation_results.csv
│   └── screenshots/
└── docs/
    ├── task_delegation.md
    └── report/
```

Struktur ini bersifat usulan. Sesuaikan dengan kebutuhan implementasi, tetapi pertahankan pemisahan modul agar kontribusi setiap anggota mudah ditelusuri.

## 10. Standar Definition of Done

Sebuah task dianggap selesai jika memenuhi seluruh kriteria yang relevan:

### Coding
- [ ] Modul dapat dijalankan dan memiliki fungsi yang jelas.
- [ ] Input dan output sesuai kontrak interface.
- [ ] Memiliki contoh penggunaan atau pengujian sederhana.
- [ ] Error/edge case utama ditangani.
- [ ] Tidak ada path file lokal yang hanya bekerja di komputer satu anggota.
- [ ] Kode memiliki komentar/docstring secukupnya.
- [ ] Library eksternal dan fungsinya dicatat.
- [ ] Hasil penting dapat direproduksi oleh anggota lain.

### Documentation
- [ ] Menjelaskan tujuan modul dan perannya dalam arsitektur.
- [ ] Menjelaskan metode/algoritma yang digunakan dan alasannya.
- [ ] Menjelaskan library yang digunakan dan bagian yang dibuat sendiri.
- [ ] Menyertakan contoh input-output atau screenshot.
- [ ] Menjelaskan hasil, kendala, dan keterbatasan.
- [ ] Klaim teknis didukung referensi yang dicantumkan.
- [ ] Konsisten dengan implementasi aktual, bukan rencana yang belum dibuat.

## 11. Ketentuan Evaluasi

Panduan tugas meminta minimal 20 pertanyaan yang disusun berdasarkan korpus dan evaluasi jawaban benar/salah disertai alasan. Karena itu:

1. Buat 20 pertanyaan dengan pembagian 4 pertanyaan per anggota.
2. Siapkan jawaban acuan dan halaman sumber sebelum menjalankan sistem.
3. Lakukan pemeriksaan silang agar ground truth tidak hanya divalidasi oleh pembuat pertanyaan.
4. Jalankan seluruh pertanyaan melalui sistem yang sudah terintegrasi.
5. Catat jawaban sistem, jawaban acuan, status benar/salah, sumber yang ditemukan, dan alasan kesalahan.
6. Laporkan jumlah serta persentase jawaban benar dan salah.
7. Kelompok boleh menambahkan metrik lain yang relevan, tetapi definisi dan cara perhitungannya harus dijelaskan.
8. Analisis kesalahan, misalnya kegagalan ekstraksi tabel, salah klasifikasi intent, retrieval passage yang keliru, ekstraksi jawaban yang tidak lengkap, atau metadata halaman yang salah.

Contoh format hasil:

| ID | Pertanyaan | Jawaban acuan | Jawaban sistem | Sumber | Status | Analisis |
|---|---|---|---|---|---|---|
| Q01 | ... | ... | ... | Hal. ... | Benar/Salah | ... |
