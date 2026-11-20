# Eksplorasi Korpus PDF Kurikulum 2024 Teknik Informatika UB

Dokumen ini merangkum struktur, peta konten, daftar visual, dan temuan *edge case* dari **100 halaman** PDF *Panduan Kurikulum Program Studi Teknik Informatika 2024* (Versi 1.0, 9 Agustus 2024) sebagai acuan bersama seluruh tim (Anggota 1–5).

---

## 1. Ringkasan Penomoran Halaman

Terdapat perbedaan antara **nomor halaman file PDF (`pdf_page`)** dan **nomor halaman tercetak pada footer (`doc_page`)**:

| Rentang `pdf_page` | Rentang `doc_page` | Isi |
|---|---|---|
| 1 | *(cover)* | Halaman sampul (*Panduan Kurikulum Program Studi Teknik Informatika 2024*) |
| 2 – 7 | `i` – `vi` | Kata Pengantar, Versi Dokumen (v1.0), Daftar Isi, Daftar Tabel, Daftar Gambar, Tim Penyusun |
| 8 – 100 | `1` – `92` | Konten utama Bab 1 sampai Bab 11 |

> **Catatan penting:** Angka footer `6` muncul dua kali, yaitu pada `pdf_page` 13 (lanjutan Tabel 3.1) dan `pdf_page` 14 (awal Bab 4). Karena itu, modul ingestion & preprocessing disarankan menyimpan **keduanya** (`pdf_page` dan `doc_page`) dalam metadata `PassageRecord`.

---

## 2. Peta Bab, Teks, dan Tabel

| Bab / Bagian | `pdf_page` | `doc_page` | Jenis Konten Utama | Catatan Ekstraksi |
|---|---|---|---|---|
| 1. Deskripsi Program Studi (Visi, Misi, Tujuan) | 8 – 9 | 1 – 2 | Teks naratif & daftar bernomor | Teks bersih, mudah diekstrak per subbagian |
| 2. Profil Lulusan | 10 | 3 | Teks naratif | 2 paragraf utama |
| 3. CPL Program Studi | 11 – 13 | 4 – 6 | Teks, Gambar 3.1, Tabel 3.1 | Tabel 3.1 terpotong lintas halaman (hal. PDF 12–13) |
| 4. Penetapan Bahan Kajian | 14 – 16 | 6 – 8 | Teks & Tabel 4.1 | Tabel 4.1 berupa matriks tanda centang (`✓`) terhadap kolom kode CPL (`IF_CPL_S1` s.d. `IF_CPL_KK3`) |
| 5. Pembentukan Mata Kuliah | 17 | 9 | Teks & Gambar 5.1 | Teks + diagram skema pemetaan BK -> CPMK -> MK |
| 6. Struktur Kurikulum | 18 – 22 | 10 – 14 | Teks & Tabel 6.1–6.4 + Tabel Semester 1–8 & SA | Header prasyarat bertingkat (`Kode`, `Mata Kuliah (MK)`, `Nilai`), ada tanda `✓` di kolom Praktikum, serta syarat SKS (`≥ 60 SKS`, `≥ 120 SKS`) |
| 7. Mata Kuliah Pilihan & Learning Path | 22 – 36 | 14 – 28 | Teks, Tabel 7.1–7.4, Gambar 7.1–7.11 | Daftar MK per *learning path* berada di Gambar 7.1–7.11 |
| 8. Diagram Alir Mata Kuliah | 37 – 39 | 29 – 31 | Teks & Gambar 8.1–8.3 | Skema Reguler, MBKM 1 Semester (sem. 6), MBKM 2 Semester (sem. 7–8) |
| 9. Perubahan Kurikulum & Aturan Peralihan | 40 – 45 | 32 – 37 | Tabel 9.1–9.11 & 7 poin teks aturan peralihan | Tabel 9.1–9.8 memakai header bertingkat *Kurikulum Lama (2020)* vs *Kurikulum Baru (2024)* |
| 10. Kegiatan Merdeka Belajar | 45 – 49 | 37 – 41 | Teks & Tabel 10.1 | Tabel 10.1 memiliki sel teks panjang dan terpotong lintas halaman (hal. PDF 46–49) |
| 11. Silabus Mata Kuliah | 50 – 100 | 42 – 92 | Kartu/tabel silabus tiap MK | 51 halaman penuh; banyak kartu silabus terbelah lintas halaman dengan header `Kode MK / Nama MK / SKS` berulang |

---

## 3. Inventarisasi Visual & Rekomendasi Penanganan (Anggota 1)

Total terdapat **16 gambar/diagram** sesuai Daftar Gambar (`pdf_page` 6):

| Gambar | `pdf_page` | `doc_page` | Deskripsi | Prioritas QA |
|---|---|---|---|---|
| Gambar 3.1 | 11 | 4 | Alur pembentukan CPL Program Studi | Rendah–Sedang (sebagian besar sudah dijelaskan di teks Bab 3) |
| Gambar 5.1 | 17 | 9 | Skema Pemetaan Bahan Kajian kepada Mata Kuliah | Rendah–Sedang (sudah dijelaskan di poin teks Bab 5) |
| **Gambar 7.1 – 7.11** | **25 – 35** | **17 – 27** | **11 Diagram MK Pilihan Learning Path** (Frontend, Backend, Game, Cloud, Security, Network, AI/ML, Computer Vision, Data Scientist, NLP, AI Research Scientist) | **Tinggi** — nama MK & SKS pada tiap *learning path* **hanya ada di diagram** (tidak diulang di tabel teks). Wajib ditranskrip/OCR ke teks terstruktur. |
| Gambar 8.1 – 8.3 | 37 – 39 | 29 – 31 | Diagram alir MK (Reguler, MBKM 1 Semester, MBKM 2 Semester) | Sedang — menunjukkan distribusi MK per semester dan garis prasyarat secara visual |

---

## 4. Temuan *Edge Case* & Ketidakkonsistenan pada Dokumen Asli

Hal-hal berikut ditemukan langsung pada korpus dan perlu ditangani saat *preprocessing*, *retrieval*, maupun analisis kesalahan evaluasi:

1. **Tabel terpotong lintas halaman:**
   * Terjadi di Tabel 3.1, Tabel 4.1, Tabel 9.2/9.3/9.4, Tabel 10.1, dan banyak kartu silabus di Bab 11 (`pdf_page` 50–100).
   * Saat menggabungkan baris silabus, jangan menganggap header berulang (`Kode MK`, `Nama MK`, `SKS`) sebagai MK baru.
2. **Matriks tanda centang (`✓`):**
   * Pada Tabel 4.1 (`pdf_page` 14–16) dan kolom `Praktikum` pada tabel semester (`pdf_page` 20–21), tanda `✓` akan kehilangan makna jika diekstrak menjadi teks mentah tanpa nama kolomnya.
3. **Sisa artefak template pada silabus:**
   * Beberapa kartu silabus mengandung baris artefak seperti `CPMK-1 (%): CPMK-2 (%) (CPL: CPMK-4 (%))` atau `CPMK-1 (%): CPMK-2 (%) (CPL: CPMK-5 (%))` (mis. `pdf_page` 51, 60, 67, 76, 89, 97), serta beberapa nilai `(CPL: )` kosong.
4. **Perbedaan kode MK di beberapa bagian dokumen:**
   * *Machine Learning Operations (MLOps)* tercatat sebagai `CIF60048` di Tabel 7.3 (`pdf_page` 24) & Tabel 9.7 (`pdf_page` 43), tetapi tertulis `CIF60050` pada kartu silabus (`pdf_page` 99–100).
   * Di tabel Semester 5 (`pdf_page` 21) dan kartu silabus (`pdf_page` 63–65), prasyarat/kode tertulis `CIF63107` (*Analisis dan Perancangan Sistem*) dan `CIF63109` (*Interaksi Manusia dan Komputer*), sedangkan di Tabel 6.4 & Semester 3 (`pdf_page` 19–20) tertulis `CIF63106` dan `CIF63108`.
   * *Administrasi Sistem Server* tertulis `CIF61233` di Tabel 7.2 & Tabel 9.1, tetapi tertulis `CIF61235` di silabus (`pdf_page` 88).
5. **Perbedaan angka SKS antara Tabel MK Pilihan dan Diagram Learning Path:**
   * Contoh: *Penjaminan Kualitas Perangkat Lunak* tertulis **3 SKS** di Tabel 7.1 (`pdf_page` 23), tetapi **4 SKS** di Gambar 7.2 (`pdf_page` 26); *Sistem Berbasis Pengetahuan* tertulis **4 SKS** di Tabel 7.3 (`pdf_page` 24), tetapi **3 SKS** di Gambar 7.11 (`pdf_page` 35).

---

## 5. Implikasi Praktis per Modul (Tanpa Mengubah Pembagian Tugas)

* **Anggota 1 — Mas Syafiq (Ingestion):** Prioritaskan `pdfplumber` / `PyMuPDF` untuk tabel terstruktur + transkripsi terstruktur untuk Gambar 7.1–7.11. Simpan `pdf_page` dan `doc_page`.
* **Anggota 2 — Radit (Preprocessing):** Gabungkan tabel/silabus yang terpotong lintas halaman, ubah simbol `✓` menjadi teks eksplisit (mis. `"Praktikum: Ya"` atau daftar kode CPL yang dicentang), bersihkan artefak seperti `CPMK-1 (%):`, dan pertahankan kode MK (`CIF...`, `COM...`, `MPK...`, `UBU...`).
* **Anggota 3 — Yusuf (Question Processing):** Kenali pola entitas kode MK (`[A-Z]{3}\d{5}(-5)?`), nomor semester (`1–8`, `antara`), angka SKS, nama *learning path*, dan kode CPL (`IF_CPL_...`).
* **Anggota 4 — Azza Arsyada (Retrieval):** Pastikan tokenizer tidak menghapus atau memecah kode MK dan angka semester/SKS, serta pertimbangkan *boosting* bila kode MK atau nama MK cocok persis.
* **Anggota 5 — Zulfan (Answer Extraction & Evaluasi):** Selalu tampilkan halaman sumber (`doc_page` / `pdf_page`) dan nama bagian/tabel, serta catat ketidakkonsistenan dokumen asli jika memengaruhi hasil evaluasi.
