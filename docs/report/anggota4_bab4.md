# Draf Bahan Bab IV — Implementasi Modul Passage Retrieval & Reranking (Bagian Anggota 4: Azza Arsyada)

> **Catatan Penulis (Azza Arsyada):** Dokumen ini disusun untuk Bab IV Laporan Proyek Akhir (bobot 20%), menguraikan secara mendalam bagaimana kode program diimplementasikan, membedakan komponen yang dibuat sendiri (*from scratch*) dengan pustaka standar, serta menyajikan cuplikan kode inti beserta analisis eksekusinya.

---

## 4.X Pembagian Implementasi: Dibuat Sendiri vs Library Eksternal

Sesuai aturan pengerjaan Proyek Akhir NLP, implementasi modul retrieval dikembangkan secara mandiri (*from scratch*) tanpa bergantung pada kerangka kerja retrieval otomatis atau mesin pencari eksternal.

| Komponen | Bagian yang Dibuat Sendiri (*From Scratch*) | Library / Standar Eksternal |
|---|---|---|
| **Struktur Indeks (`index_builder.py`)** | Struktur data `RetrievalIndex`, logika pembuatan *Inverted Index* berbasis hash, penghitungan *Document Frequency* (DF), formula non-negatif Robertson-Spärck Jones Okapi BM25 IDF, vektorisasi TF-IDF dengan normalisasi Euclidean $L_2$, serta sistem indeks relasi Knowledge Base multi-arah dengan resolusi alias dua arah | Python Standard Library (`math`, `re`, `collections`, `dataclasses`) |
| **Penelusuran Relevansi (`retriever.py`)** | Algoritma *scoring* Okapi BM25 ($k_1=1.5, b=0.75$), kalkulasi dot-product *Cosine Similarity* pada vektor berdimensi jarang, mekanisme pembobotan kueri ekspansi (*Query Expansion*), dan *boost* prior berbasis pencocokan entitas domain | Python Standard Library |
| **Pengambilan Relasi KB (`retriever.py`)** | Logika *Structured Relation Retrieval* $(s, p, o)$ berkecepatan $O(1)$, pencocokan kode MK $\leftrightarrow$ nama MK, pencarian berbasis pasangan $(s, p)$, serta penyaringan relasi berdasarkan preferensi *intent* | Python Standard Library |
| **Ekstraksi Fitur Reranking (`ranking.py`)** | Implementasi lengkap **6 Fitur PBA14 Slide 52**: pengenal pola entitas tipe jawaban Li & Roth, pelacak rantai kata kunci berurutan (*longest sequence*), kalkulasi jarak kedekatan token (*keyword proximity sliding window*), dan koefisien Dice bigram/trigram | Python Standard Library (`re`) |
| **Pemeringkatan Ulang (`ranking.py`)** | Normalisasi fitur min-max, kombinasi linier terbobot, pengurutan ulang kandidat, dan pembaruan struktur peringkat `doc_rank` | Python Standard Library |

---

## 4.X Penjelasan Implementasi Per Komponen

### 1. Pembangunan Inverted Index & Indeks KB (`src/retrieval/index_builder.py`)

- **Tujuan:** Mengonversi 392 rekaman *passage* korpus kurikulum menjadi struktur indeks terbalik berbasis token alfanumerik serta mengindeks 1.177 *knowledge triples* ke dalam tabel hash relasional.
- **Cuplikan Kode Inti (Pembangunan Indeks BM25 & IDF):**
```python
# Perhitungan IDF Robertson-Spärck Jones dengan smoothing non-negatif
idf: dict[str, float] = {}
if method == "bm25":
    for term, df in doc_freqs.items():
        idf_val = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
        idf[term] = max(idf_val, 0.01)
else:
    for term, df in doc_freqs.items():
        idf[term] = math.log((total_docs + 1.0) / (df + 1.0)) + 1.0
```
- **Penjelasan & Mekanisme Alias KB:**
  Pada pengindeksan *Knowledge Base*, fungsi `_build_kb_indices` secara otomatis mendeteksi predikat `course_code` dan `course_name` untuk membangun kamus `kb_subject_aliases`. Jika pengguna menanyakan kueri menggunakan kode mata kuliah seperti `"CIF64311"`, sistem dapat langsung menautkannya ke subjek kanonik `"Kecerdasan Artifisial Lanjut"`, dan sebaliknya.

---

### 2. Algoritma Pencarian Teks & Query Expansion (`src/retrieval/retriever.py`)

- **Tujuan:** Menghitung skor kemiripan antara pertanyaan pengguna dan seluruh passage dalam korpus, mengintegrasikan kueri utama dan kueri ekspansi, serta mengambil relasi terstruktur.
- **Cuplikan Kode Inti (Skor Okapi BM25):**
```python
def _score_bm25_query(query_tokens: list[str], index: RetrievalIndex) -> dict[int, float]:
    scores: dict[int, float] = Counter()
    k1 = index.bm25_k1
    b = index.bm25_b
    avg_dl = index.avg_dl if index.avg_dl > 0 else 1.0

    q_counts = Counter(query_tokens)
    for term, q_tf in q_counts.items():
        if term not in index.inverted_index:
            continue
        idf_weight = index.idf.get(term, 0.0)
        postings = index.inverted_index[term]

        for doc_idx, doc_tf in postings:
            doc_len = index.doc_lens[doc_idx]
            denom = doc_tf + k1 * (1.0 - b + b * (doc_len / avg_dl))
            numer = doc_tf * (k1 + 1.0)
            score_term = idf_weight * (numer / denom) if denom > 0 else 0.0
            scores[doc_idx] += score_term
    return scores
```
- **Integrasi Query Expansion & Entity Boost:**
  Skor dasar digabungkan dengan skor dari `expanded_queries` dengan faktor bobot 0.25. Selain itu, bila entitas kunci (mis. nama MK atau kode CPL) cocok seutuhnya pada teks passage atau judul tabel, ditambahkan nilai penguat (*boost*) sebesar 0.5 untuk memastikan passage tabel kurikulum yang relevan masuk ke dalam kolam kandidat reranking.

---

### 3. Ekstraksi 6 Fitur Pemeringkatan Passage PBA14 Slide 52 (`src/retrieval/ranking.py`)

- **Tujuan:** Mengukur relevansi passage dari sudut pandang tipe jawaban yang diharapkan, keutuhan frasa kata kunci, dan kedekatan posisi token.
- **Rincian Implementasi 6 Fitur:**
  1. `answer_type_ne_count`: Menggunakan pencocokan pola regex terhadap teks passage berdasarkan tipe coarse dan fine Li & Roth. Untuk `NUMERIC:grade`, mendeteksi huruf mutu prasyarat (`nilai minimum C`). Untuk `ENTITY:course_list` atau `prerequisite`, mendeteksi kode mata kuliah dan frasa kurikulum.
  2. `keyword_match_count`: Menghitung kardinalitas irisan antara kata kunci kueri ter-tokenisasi dan himpunan token passage unik.
  3. `longest_keyword_seq`: Menghitung panjang subsekuens token kueri berurutan terpanjang yang muncul tanpa jeda pada teks passage:
```python
def _compute_longest_keyword_sequence(passage_tokens: list[str], keyword_tokens: list[str]) -> int:
    kw_set = set(t.lower() for t in keyword_tokens)
    max_len = 0
    current_len = 0
    for tok in passage_tokens:
        if tok in kw_set:
            current_len += 1
            if current_len > max_len:
                max_len = current_len
        else:
            current_len = 0
    return max_len
```
  4. `source_doc_rank`: Dihitung sebagai inversi peringkat dari tahap retrieval pertama ($1.0 / \text{doc\_rank}$).
  5. `keyword_proximity`: Dihitung dengan teknik *sliding window* untuk menemukan rentang token terpendek $\text{span}_{\min}$ yang memuat kemunculan kata kunci kueri yang berbeda.
  6. `ngram_overlap`: Menghitung koefisien Dice untuk bigram dan trigram antara pertanyaan teranotasi dan teks passage.

---

### 4. Contoh Eksekusi Input dan Output Riil

Berikut adalah contoh keluaran eksekusi riil pada pertanyaan evaluasi Q01 (*"Apa prasyarat Kecerdasan Artifisial Lanjut?"*):

```text
=== Masukan QuestionAnalysis ===
Pertanyaan: "Apa prasyarat Kecerdasan Artifisial Lanjut?"
Intent: course_prerequisite | Answer Type: ENTITY:prerequisite
Query Keywords: ['prasyarat', 'Kecerdasan Artifisial Lanjut', 'CIF64311']

=== Hasil Passage Retrieval & Reranking ===
[Peringkat 1]
Passage ID     : p_0158
Nomor Halaman  : PDF Hal. 21 / Dokumen Hal. 13
Judul Bagian   : 6. Struktur Kurikulum (Distribusi Mata Kuliah Semester 4 & 5)
Skor Awal BM25 : 17.9430 -> Skor Rerank: 0.8023
Fitur Slide 52 : {
  'answer_type_ne_count': 6.0,
  'keyword_match_count': 4.0,
  'longest_keyword_seq': 3.0,
  'source_doc_rank': 1.0,
  'keyword_proximity': 0.8000,
  'ngram_overlap': 0.6667
}

=== Hasil Relation Retrieval (Knowledge Triples) ===
[Triple 1] Kecerdasan Artifisial Lanjut -> prerequisite_of -> CIF63110 Kecerdasan Artifisial (Hal. 21)
[Triple 2] CIF64311 -> prerequisite_of -> CIF63110 Kecerdasan Artifisial (Hal. 21)
```

Log di atas membuktikan bahwa modul berhasil menempatkan passage acuan yang memuat tabel kurikulum semester 5 di peringkat pertama, lengkap dengan ekstraksi relasi terstruktur yang siap digunakan oleh Modul 5 untuk ekstraksi jawaban presisi.
