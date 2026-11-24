# Progress Log & Pembagian Anggota

Gunakan dokumen ini sebagai papan kontrol progres kelompok agar setiap anggota dapat memantau status modul, milestone, dan kontribusi masing-masing.

---

## 1. Pembagian Anggota Kelompok

| Peran | Nama / NIM | Modul Utama | Tugas Evaluasi (4 Soal) | Tugas Laporan |
|---|---|---|---|---|
| **Anggota 1** | **Putra Cakrawala Aulia Syafiq** (`235150200111040`) | `src/document_ingestion/` | Q01 – Q04 | Bab III & IV (Ingestion) |
| **Anggota 2** | **Raditya Ramadhan Eka Widhianto** (`245150207111054`) | `src/preprocessing/` | Q05 – Q08 | Bab III & IV (Preprocessing & Korpus) |
| **Anggota 3** | **Achmad Yusuf Hamdani Firmansyah** (`245150207111084`) | `src/question_processing/` | Q09 – Q12 | Bab II, III, IV (NLP & Question Processing) |
| **Anggota 4** | **Muhammad Azza Arsyada Roziqi** (`245150200111062`) | `src/retrieval/` | Q13 – Q16 | Bab II, III, IV (Retrieval & Ranking) |
| **Anggota 5** | **Zaidan Alvi Zulfan Pramudya** (`245150200111056`) | `src/answer_processing/` & `src/pipeline/` | Q17 – Q20 | Koordinator, Bab I, III, IV, V, VI |

---

## 2. Checklist Milestone (M1 – M9)

- [x] **M1 (Setup Awal)** — Struktur repository, kontrak interface (`src/contracts.py`), dan template evaluasi dibuat.
- [x] **M1 (Audit PBA14 & Korpus)** — PDF korpus tersedia di `data/raw/`, arsitektur diselaraskan dengan materi PBA14 (Hybrid IR + KB-QA, Li & Roth answer type, Focus/POS/Query Expansion, 6 fitur Passage Reranking, 8 fitur Candidate Ranking, & metrik MRR), dan `requirements.txt` diperbarui.
- [x] **M1 (Finalisasi Tim)** — Pembagian 5 anggota disepakati dan NIM kelima anggota lengkap (**Mas Syafiq**, **Radit**, **Yusuf**, **Azza Arsyada**, **Zulfan**).
- [x] **M2 — Corpus extraction** (`Anggota 1 — Mas Syafiq`): Teks, tabel, dan inventarisasi visual berhasil diekstrak ke `data/extracted/`.
- [x] **M3 — Processed corpus** (`Anggota 2 — Radit`): Korpus bersih, passage, dan metadata tersedia di `data/processed/` (392 `PassageRecord`, 1.177 `KnowledgeTriple`, validasi lulus).
- [x] **M4 — Question processing** (`Anggota 3 — Yusuf`): Klasifikasi pertanyaan, entitas, dan answer type berjalan.
- [x] **M5 — Retrieval** (`Anggota 4 — Azza Arsyada`): Indeks dan top-k passage retrieval berjalan (BM25, TF-IDF Cosine, 6 fitur PBA14 Slide 52, Relation Retrieval KB Triples).
- [x] **M6 — Answer extraction** (`Anggota 5 — Zulfan`): Ekstraksi kandidat 4 jalur, ranking 8 fitur PBA14, *confidence merging*, source tracking, dan fallback berjalan.
- [x] **M7 — End-to-end integration** (`Semua; koordinator Anggota 5 — Zulfan`): Pertanyaan dapat diproses sampai jawaban + sumber ditampilkan lewat `main.py` (`-q`, interaktif, `--evaluate`).
- [ ] **M8 — Evaluation** (`Semua`): 20 soal di `data/evaluation/eval_q*.json` selesai dan hasil `reports/evaluation_results.csv` tercapai (**18/20 benar, Accuracy 90,00%, MRR 0,9000**); tinggal melengkapi validasi silang (`validated_by`) seluruh 20 soal & menggabungkan ke `questions.json` bila diperlukan.
- [ ] **M9 — Report finalization** (`Semua`): Draf laporan utuh Bab I–VI tersedia di Google Docs; tinggal melengkapi kolom kelas, menambahkan screenshot aplikasi, dan mengemas ZIP pengumpulan final.

---

## 3. Log Progres Harian / Mingguan

> Tambahkan catatan setiap kali melakukan update atau merge ke `main`.

| Tanggal | Anggota | Modul / Area | Ringkasan Progres |
|---|---|---|---|
| 2026-11-18 | Initializer | Repository Setup | Membuat struktur folder, kontrak JSON (`src/contracts.py`), kerangka modul, unit test dasar, dan dokumentasi panduan. |
| 2026-11-18 | Initializer | Eksplorasi Korpus | Mendokumentasikan peta 100 halaman PDF, inventarisasi 16 visual, dan temuan *edge case* di `docs/corpus_exploration.md`. |
| 2026-11-19 | Initializer | Audit Materi PBA14 | Menyelaraskan `src/contracts.py`, arsitektur Hybrid IR+KB QA, modul `query_formulator.py`, pipeline reranking, `config/settings.py`, dan metrik evaluasi **Accuracy + MRR** sesuai slide PBA14. |
| 2026-11-20 | Tim | Pembagian Tugas | Menetapkan owner modul: Mas Syafiq (Anggota 1), Radit (Anggota 2), Yusuf (Anggota 3), Azza Arsyada (Anggota 4), dan Zulfan (Anggota 5). |
| 2026-11-21 | Mas Syafiq (Anggota 1) | Document Ingestion (M2) | Menyelesaikan `src/document_ingestion/`, `tests/test_ingestion.py`, `docs/system_architecture.md`, dan mengekstrak 100 hal. teks, 149 blok tabel, serta 16 visual ke `data/extracted/` (`failed_count: 0`). |
| 2026-11-21 | Yusuf (Anggota 3) | Question Processing (M4) | Menyelesaikan `src/question_processing/` (POS CRF + override, speech act, entity/focus/relation, hybrid classifier, Li & Roth answer type, query formulation), taksonomi, fixture tim, draf Q09–Q12, serta evaluasi modul (24/24 test lulus). |
| 2026-11-23 | Radit (Anggota 2) | Preprocessing & Structuring (M3) | Menyelesaikan `src/preprocessing/` (`preprocessing.py`, `passage_builder.py`, `corpus_validator.py`), menghasilkan `data/processed/passages.jsonl` (392 passage: 332 tabel, 46 teks, 14 visual) & `knowledge_triples.jsonl` (1.177 triple selaras GATE-A), `eval_q05_q08.json`, dan lulus unit test. |
| 2026-11-23 | Yusuf (Anggota 3) | Question Processing — Sinkronisasi A1/A2 (M4) | Merge `main` (A1+A2) ke `feat/question-processing`, menyelesaikan sinkronisasi 15/15 predikat GATE-A (+`supports_cpl`, +`learning_path_sks`, multi-relasi Q09/Q10, 31 Bahan Kajian, `Perekayasa Perangkat Lunak`, `Semester Antara (A)/(B)`, `Ganjil`/`Genap`, 14 subjek `total_sks`, alias MK A2), memperbaiki *no-op expansion* & ambang *out-of-domain* `LinearSVC` terkalibrasi CV, memindahkan soal ke `data/evaluation/eval_q09_q12.json`, memperbarui 15 fixture & laporan evaluasi, serta lulus 35/35 unit test gabungan A1+A2+A3 (8/8 Q05–Q12 cocok penuh). |
| 2026-11-23 | Azza Arsyada (Anggota 4) | Retrieval & Reranking (M5) | Menyelesaikan `src/retrieval/` (`index_builder.py`, `retriever.py`, `ranking.py`) mandiri (*from scratch*), mendukung BM25 & TF-IDF Cosine, integrasi Query Expansion & Entity Boost, 6 fitur Passage Reranking PBA14 Slide 52, Relation Retrieval O(1) dari 1.177 KB Triples dengan resolusi alias kode<->nama MK, menyusun `data/evaluation/eval_q13_q16.json`, draf Bab II, III, IV, dan laporan evaluasi (Recall@5=1.0000, MRR=0.7778), serta lulus 6/6 unit test `tests/test_retrieval.py` (4/4 Q13–Q16 lolos di rank 1). |
| 2026-11-23 | Mas Syafiq (Anggota 1) | Evaluasi Soal Q01–Q04 (M8) | Menambahkan `data/evaluation/eval_q01_q04.json` (Q01–Q04) lengkap dengan *ground truth*, variasi jawaban, dan halaman sumber. |
| 2026-11-24 | Zulfan (Anggota 5) | Answer Processing, Integrasi & Evaluasi (M6–M8) | Menyelesaikan `src/answer_processing/` (4 jalur ekstraksi + 8 fitur ranking PBA14 + *confidence merging* + threshold `0.5`), `src/pipeline/evaluation.py`, `main.py` (`-q`, interaktif, `--evaluate`), `eval_q17_q20.json`, 3 file unit test, serta evaluasi 20 soal di `reports/evaluation_results.csv` (**18/20 benar, Accuracy 90,00%, MRR 0,9000**). |
| 2026-11-24 | Radit (Anggota 2) | Validasi Silang Soal & Sinkronisasi Log (M1, M8) | Memvalidasi silang `Q09–Q12` (`eval_q09_q12.json` milik Yusuf) terhadap PDF Kurikulum 2024 dan menyinkronkan NIM lengkap ke-5 anggota serta status M1/M6/M7 ke `docs/progress_log.md`. |
