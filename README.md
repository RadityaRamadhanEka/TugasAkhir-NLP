# Sistem Question Answering Kurikulum 2024 Teknik Informatika UB

Proyek Akhir Mata Kuliah **Pemrosesan Bahasa Alami (NLP)** — membangun sistem *Question Answering* faktual berbasis **Classic NLP & Hybrid QA (IR-based + Structured Knowledge Base, tanpa LLM)** sesuai materi PBA14, dengan korpus utama *Buku Pedoman Pelaksanaan Kurikulum 2024 Teknik Informatika Universitas Brawijaya*.

Dokumen pembagian tugas lengkap dapat dibaca di [brief-task-delegation-qa-kurikulum-tif-revisi.md](brief-task-delegation-qa-kurikulum-tif-revisi.md).

---

## Pembagian Modul & Owner

Isi nama anggota kelompok pada tabel berikut (dan di `docs/progress_log.md`) setelah disepakati:

| Peran | Modul / Folder | Tanggung Jawab Utama | Nama Anggota |
|---|---|---|---|
| **Anggota 1** | `src/document_ingestion/` | Ekstraksi teks, tabel, dan visual/OCR dari PDF (`pdf_page` & `doc_page`) | *(Belum diisi)* |
| **Anggota 2** | `src/preprocessing/` | Pembersihan teks, tokenisasi, stopword selektif, stemming Sastrawi, *passage* & *Knowledge Triples* | *(Belum diisi)* |
| **Anggota 3** | `src/question_processing/` | POS tagging, Hybrid Question Classifier, *Answer Type* (Li & Roth), *Focus*, entitas/relasi, & *Query Expansion* | *(Belum diisi)* |
| **Anggota 4** | `src/retrieval/` | Indexing (TF-IDF / BM25 + KB Triples), *passage & relation retrieval*, serta *Passage Reranking* (6 fitur PBA14) | *(Belum diisi)* |
| **Anggota 5** | `src/answer_processing/` & `src/pipeline/` | Answer-type NER & Pattern Extraction, *Candidate Ranking* (8 fitur + *Confidence Merging*), integrasi & evaluasi (**Accuracy + MRR**) | *(Belum diisi)* |

---

## Struktur Repository

```text
.
├── main.py                         # Entry point CLI QA
├── requirements.txt                # Daftar library Python
├── config/
│   └── settings.py                 # Konfigurasi path relatif & parameter sistem
├── data/
│   ├── raw/                        # Letakkan PDF Kurikulum 2024 di sini
│   ├── extracted/                  # Hasil ekstraksi mentah (Anggota 1)
│   ├── processed/                  # Dataset passage final (Anggota 2)
│   └── evaluation/                 # 20 pertanyaan evaluasi & ground truth
├── src/
│   ├── contracts.py                # Kontrak format JSON antar-modul (single source of truth)
│   ├── document_ingestion/         # Modul Anggota 1
│   ├── preprocessing/              # Modul Anggota 2
│   ├── question_processing/        # Modul Anggota 3
│   ├── retrieval/                  # Modul Anggota 4
│   ├── answer_processing/          # Modul Anggota 5
│   └── pipeline/                   # Integrasi & evaluasi end-to-end (Anggota 5)
├── tests/                          # Unit test per modul
├── reports/
│   ├── evaluation_results.csv      # Rekap hasil uji 20 pertanyaan
│   └── screenshots/                # Screenshot bukti untuk laporan
└── docs/
    ├── progress_log.md             # Pelacakan progres & milestone M1–M9
    └── report/                     # Draft laporan Bab I–VI
```

---

## Setup Environment

1. Buat dan aktifkan *virtual environment*:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
2. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
3. Letakkan file PDF *Buku Pedoman Pelaksanaan Kurikulum 2024 Teknik Informatika* di folder `data/raw/`.
4. Jalankan tes awal untuk memastikan struktur modul terhubung:
   ```bash
   pytest
   ```

---

## Alur Kerja Kolaborasi (Git Workflow)

Agar tidak terjadi konflik saat 5 orang bekerja bersamaan:

1. **Selalu tarik perubahan terbaru** sebelum mulai coding:
   ```bash
   git pull origin main
   ```
2. **Buat branch per fitur/modul**, misalnya:
   * `feat/ingestion-pdf` (Anggota 1)
   * `feat/preprocessing-passage` (Anggota 2)
   * `feat/question-processing` (Anggota 3)
   * `feat/retrieval-bm25` (Anggota 4)
   * `feat/answer-extraction` (Anggota 5)
3. **Bekerja di folder modul masing-masing** dan patuhi kontrak data di `src/contracts.py`. Jangan mengubah format output di `src/contracts.py` tanpa kesepakatan seluruh tim.
4. **Update progres** di `docs/progress_log.md` setiap menyelesaikan *milestone* atau fitur penting, lalu buat *Pull Request* ke `main`.
5. **Gunakan path relatif** melalui `config/settings.py` (dilarang menuliskan path lokal seperti `C:\Users\Nama\...`).

---

## Cara Menjalankan Pipeline

Setelah modul terintegrasi, jalankan dari root proyek:

```bash
python main.py --question "Apa prasyarat Kecerdasan Artifisial Lanjut?"
```

Atau mode interaktif:

```bash
python main.py
```
