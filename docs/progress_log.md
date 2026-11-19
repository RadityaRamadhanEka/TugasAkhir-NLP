# Progress Log & Pembagian Anggota

Gunakan dokumen ini sebagai papan kontrol progres kelompok agar setiap anggota dapat memantau status modul, milestone, dan kontribusi masing-masing.

---

## 1. Pembagian Anggota Kelompok

| Peran | Nama / NIM | Modul Utama | Tugas Evaluasi (4 Soal) | Tugas Laporan |
|---|---|---|---|---|
| **Anggota 1** | *(Isi nama)* | `src/document_ingestion/` | Q01 – Q04 | Bab III & IV (Ingestion) |
| **Anggota 2** | *(Isi nama)* | `src/preprocessing/` | Q05 – Q08 | Bab III & IV (Preprocessing & Korpus) |
| **Anggota 3** | *(Isi nama)* | `src/question_processing/` | Q09 – Q12 | Bab II, III, IV (NLP & Question Processing) |
| **Anggota 4** | *(Isi nama)* | `src/retrieval/` | Q13 – Q16 | Bab II, III, IV (Retrieval & Ranking) |
| **Anggota 5** | *(Isi nama)* | `src/answer_processing/` & `src/pipeline/` | Q17 – Q20 | Koordinator, Bab I, III, IV, V, VI |

---

## 2. Checklist Milestone (M1 – M9)

- [x] **M1 (Setup Awal)** — Struktur repository, kontrak interface (`src/contracts.py`), dan template evaluasi dibuat.
- [x] **M1 (Audit PBA14 & Korpus)** — PDF korpus tersedia di `data/raw/`, arsitektur diselaraskan dengan materi PBA14 (Hybrid IR + KB-QA, Li & Roth answer type, Focus/POS/Query Expansion, 6 fitur Passage Reranking, 8 fitur Candidate Ranking, & metrik MRR), dan `requirements.txt` diperbarui.
- [ ] **M1 (Finalisasi Tim)** — Pembagian nama/NIM 5 anggota disepakati dan environment lokal terpasang di tiap anggota.
- [ ] **M2 — Corpus extraction** (`Anggota 1`): Teks, tabel, dan inventarisasi visual berhasil diekstrak ke `data/extracted/`.
- [ ] **M3 — Processed corpus** (`Anggota 2`): Korpus bersih, passage, dan metadata tersedia di `data/processed/`.
- [ ] **M4 — Question processing** (`Anggota 3`): Klasifikasi pertanyaan, entitas, dan answer type berjalan.
- [ ] **M5 — Retrieval** (`Anggota 4`): Indeks dan top-k passage retrieval berjalan.
- [ ] **M6 — Answer extraction** (`Anggota 5`): Kandidat jawaban, source tracking, dan fallback berjalan.
- [ ] **M7 — End-to-end integration** (`Semua; koordinator Anggota 5`): Pertanyaan dapat diproses sampai jawaban + sumber ditampilkan lewat `main.py`.
- [ ] **M8 — Evaluation** (`Semua`): 20 pertanyaan di `data/evaluation/questions.json`, cross-check ground truth, rekap `reports/evaluation_results.csv`, dan analisis error.
- [ ] **M9 — Report finalization** (`Semua`): Laporan Bab I–VI di `docs/report/`, kode, dan korpus siap dikumpulkan.

---

## 3. Log Progres Harian / Mingguan

> Tambahkan catatan setiap kali melakukan update atau merge ke `main`.

| Tanggal | Anggota | Modul / Area | Ringkasan Progres |
|---|---|---|---|
| 2026-11-18 | Initializer | Repository Setup | Membuat struktur folder, kontrak JSON (`src/contracts.py`), kerangka modul, unit test dasar, dan dokumentasi panduan. |
| 2026-11-18 | Initializer | Eksplorasi Korpus | Mendokumentasikan peta 100 halaman PDF, inventarisasi 16 visual, dan temuan *edge case* di `docs/corpus_exploration.md`. |
| 2026-11-19 | Initializer | Audit Materi PBA14 | Menyelaraskan `src/contracts.py`, arsitektur Hybrid IR+KB QA, modul `query_formulator.py`, pipeline reranking, `config/settings.py`, dan metrik evaluasi **Accuracy + MRR** sesuai slide PBA14. |
