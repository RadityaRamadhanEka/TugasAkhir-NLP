# Draf Bahan Bab II — Tinjauan Pustaka (Bagian Anggota 4: Passage Retrieval & Reranking)

> **Catatan Penulis (Azza Arsyada):** Dokumen ini berisi landasan teori komprehensif, formulasi matematis, dan studi literatur yang mendasari implementasi pada modul `src/retrieval/` (`index_builder.py`, `retriever.py`, dan `ranking.py`). Dokumen ini disusun untuk digabungkan ke dalam Bab II Laporan Proyek Akhir bersama Anggota 3 (Yusuf). Seluruh rujukan menggunakan format **Harvard Anglia-Ruskin** yang telah terverifikasi metadata-nya.

---

## Kerangka Subbab Tinjauan Pustaka Modul Retrieval

### 2.X Information Retrieval (IR) dalam Arsitektur Question Answering Klasik
- Jelaskan peran sentral *Information Retrieval* (IR) sebagai komponen jembatan antara analisis pertanyaan (*Question Processing*) dan pengekstraksian jawaban (*Answer Processing*) pada sistem tanya jawab klasik non-LLM (Jurafsky & Martin, 2009; PBA14 Slide 49–54).
- Bandingkan perbedaan mendasar antara *Document Retrieval* konvensional (mengembalikan dokumen utuh puluhan halaman) dengan *Passage Retrieval* pada QA (mengembalikan unit teks padat berukuran 50–200 kata atau blok baris tabel), yang bertujuan meningkatkan *precision* dan menyaring interferensi konteks yang tidak relevan bagi modul ekstraksi jawaban (Roberts & Gaizauskas, 2004).

### 2.X Struktur Data Inverted Index & Tokenisasi Dokumen Korpus
- Jelaskan konsep *Inverted Index* (indeks terbalik) sebagai struktur data standar dalam temu kembali informasi (Manning, Raghavan & Schütze, 2008), yang memetakan setiap term/token unik $t$ dalam kosakata (*vocabulary*) ke daftar kemunculan (*posting list*):
  $$\text{Posting}(t) = \left[ (d_1, tf_{t, d_1}), (d_2, tf_{t, d_2}), \dots, (d_k, tf_{t, d_k}) \right]$$
- Jelaskan kebutuhan strategi tokenisasi domain khusus: menjaga keutuhan kode alfanumerik mata kuliah (`CIF63110`, `COM60024`), kode capaian pembelajaran (`IF_CPL_KK1`), serta angka kredit SKS (`3`, `5`) agar tidak terpecah oleh tokenisasi umum berbasis karakter non-alfanumerik.

### 2.X Algoritma Pembobotan TF-IDF dan Cosine Similarity
- Jelaskan model ruang vektor (*Vector Space Model*) oleh Salton & Buckley (1988), di mana kueri dan dokumen direpresentasikan sebagai vektor berdimensi $|V|$.
- Formulasi matematis *Term Frequency* (TF) ternormalisasi panjang dokumen:
  $$\text{TF}(t, d) = \frac{f_{t, d}}{|d|}$$
- Formulasi *Inverse Document Frequency* (IDF) dengan pelembutan (*smoothing*) untuk mencegah pembagian dengan nol dan logaritma tak tentu:
  $$\text{IDF}(t) = \ln\left( \frac{N + 1}{df(t) + 1} \right) + 1.0$$
  di mana $N$ adalah total passage pada korpus dan $df(t)$ adalah jumlah passage yang mengandung term $t$.
- Pembobotan akhir vektor dokumen $\vec{v}(d)$ dan pengukuran relevansi kueri-dokumen menggunakan *Cosine Similarity* ternormalisasi norma Euclidean ($L_2$):
  $$\text{Cosine}(\vec{q}, \vec{d}) = \frac{\vec{q} \cdot \vec{d}}{\|\vec{q}\|_2 \|\vec{d}\|_2} = \sum_{t \in q \cap d} \hat{q}_t \cdot \hat{d}_t$$

### 2.X Algoritma Probabilistik Okapi BM25
- Jelaskan keunggulan Okapi BM25 (Robertson & Zaragoza, 2009; Robertson et al., 1994) dibandingkan TF-IDF standar, khususnya dalam menangani saturasi frekuensi kata (*term frequency saturation*) dan normalisasi panjang dokumen (*document length normalization*).
- Formulasi skor BM25 untuk dokumen $D$ terhadap kueri $Q = \{q_1, q_2, \dots, q_m\}$:
  $$\text{BM25}(D, Q) = \sum_{i=1}^{m} \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$
  di mana:
  - $f(q_i, D)$ adalah frekuensi kemunculan kata $q_i$ pada passage $D$.
  - $|D|$ adalah panjang passage $D$ (jumlah token), dan $\text{avgdl}$ adalah rata-rata panjang seluruh passage dalam korpus.
  - $k_1$ adalah parameter bebas pengatur saturasi frekuensi (diatur $k_1 = 1.5$).
  - $b$ adalah parameter pengatur bobot penalti panjang dokumen (diatur $b = 0.75$).
  - $\text{IDF}(q_i)$ dihitung menggunakan formulasi Robertson-Spärck Jones non-negatif:
    $$\text{IDF}(q_i) = \ln\left(1 + \frac{N - df(q_i) + 0.5}{df(q_i) + 0.5}\right)$$

### 2.X Passage Retrieval & Query Expansion
- Jelaskan pemanfaatan *Query Expansion* dan *Query Formulation* (Lin, 2007; PBA14 Slide 47) yang dihasilkan oleh Modul Question Processing (Anggota 3).
- Kombinasi linier pembobotan skor kueri utama ($\text{score}_{\text{primary}}$) dengan kueri hasil ekspansi sinonim dan reformulasi deklaratif ($\text{score}_{\text{expanded}}$):
  $$\text{Score}_{\text{base}}(D) = \text{Score}(D, Q_{\text{primary}}) + \alpha \cdot \text{Score}(D, Q_{\text{expanded}}) + \beta \cdot \text{Boost}_{\text{entity}}(D)$$
  di mana $\alpha = 0.25$ dan $\beta$ adalah bobot penguat bila entitas kunci (seperti kode MK atau kode CPL) cocok secara identik pada metadata atau judul tabel passage.

### 2.X Pemeringkatan Ulang Kandidat (*Passage Reranking*) Berbasis 6 Fitur PBA14 Slide 52
- Jelaskan keterbatasan retrieval tahap pertama yang hanya mengandalkan kemunculan leksikal bag-of-words tanpa mempertimbangkan tipe jawaban yang dituju maupun struktur sintaktis teks (PBA14 Slide 51).
- Jelaskan definisi operasional dan formulasi ke-6 fitur pemeringkatan passage menurut materi perkuliahan PBA14 Slide 52:
  1. **`answer_type_ne_count`**: Jumlah entitas bernama atau pola gramatikal pada passage yang cocok dengan tipe jawaban yang diharapkan (*expected answer type* dari taksonomi Li & Roth). Misalnya, pada pertanyaan bertipe `NUMERIC:grade`, passage yang memuat huruf mutu prasyarat (`nilai minimum C`) mendapat skor lebih tinggi.
  2. **`keyword_match_count`**: Jumlah kata kunci pertanyaan (*query keywords*) yang muncul di dalam teks passage.
  3. **`longest_keyword_seq`**: Panjang rantai kata kunci kueri terpanjang yang muncul secara berurutan (*contiguous*) pada passage. Fitur ini merepresentasikan keutuhan frasa nama mata kuliah atau istilah resmi kurikulum.
  4. **`source_doc_rank`**: Skor inversi peringkat awal passage dari tahap retrieval pertama ($1.0 / \text{doc\_rank}$).
  5. **`keyword_proximity`**: Kedekatan jarak token antar kata kunci pertanyaan di dalam passage. Dihitung melalui rasio jumlah kata kunci yang cocok terhadap rentang span token terpendek:
     $$\text{Proximity} = \frac{|K_{\text{matched}}|}{\text{span}_{\min} + 1.0}$$
  6. **`ngram_overlap`**: Koefisien tumpang tindih bigram dan trigram antara pertanyaan teranotasi dan passage, dihitung dengan rata-rata koefisien Dice n-gram:
     $$\text{Dice}_n = \frac{2 \cdot |G_n(Q) \cap G_n(D)|}{|G_n(Q)| + |G_n(D)|}$$
- Penggabungan skor reranking menggunakan kombinasi linier terbobot (*weighted linear combination*):
  $$\text{Score}_{\text{rerank}}(D) = w_0 \cdot \hat{S}_{\text{base}} + w_1 \cdot \text{Rank}_{\text{doc}} + w_2 \cdot \hat{F}_{\text{kw}} + w_3 \cdot \hat{F}_{\text{seq}} + w_4 \cdot F_{\text{prox}} + w_5 \cdot F_{\text{ngram}} + w_6 \cdot \hat{F}_{\text{ne}}$$

### 2.X Cabang Structured Knowledge-Based QA & Relation Retrieval
- Jelaskan arsitektur *Hybrid Question Answering* (ala IBM Watson, Ferrucci dkk., 2010; PBA14 Slide 66–75), yang menempatkan cabang *Knowledge-Based QA* berdampingan dengan cabang *IR-based QA*.
- Jelaskan struktur data *Knowledge Triples* $(s, p, o)$ di mana $s$ adalah subjek entitas, $p$ adalah relasi predikat (15 predikat GATE-A), dan $o$ adalah objek/nilai.
- Jelaskan mekanisme pengindeksan hash berwaktu $O(1)$ untuk pasangan $(s, p)$, subjek $s$, predikat $p$, dan objek $o$, serta penanganan alias dua arah antara kode mata kuliah (`CIF64311`) dan nama kanonik mata kuliah (`Kecerdasan Artifisial Lanjut`).

### 2.X Metrik Evaluasi Retrieval (Recall@K dan Retrieval MRR)
- Jelaskan fungsi metrik evaluasi retrieval menurut standar TREC QA (Voorhees, 1999; PBA14 Slide 64):
  - **$\text{Recall@}K$**: Proporsi pertanyaan di mana passage acuan (*ground truth source page*) berhasil ditemukan pada urutan $K$ teratas ($K \in \{1, 3, 5, 10\}$):
    $$\text{Recall@}K = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \mathbb{I}(\text{rank}_i \le K)$$
  - **Retrieval Mean Reciprocal Rank (Retrieval MRR)**: Mengukur ketepatan peringkat passage acuan pertama yang ditemukan:
    $$\text{Retrieval MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
    di mana $\frac{1}{\text{rank}_i} = 0$ apabila passage acuan tidak ditemukan di dalam daftar kandidat.

### 2.X Studi Terkait Information Retrieval & Question Answering Bahasa Indonesia
Kaitkan pembahasan modul dengan minimal 3 penelitian bereputasi berikut:
1. **Purwarianti, Masuda, & Matsuo (2007)** — merancang sistem *Question Answering* Bahasa Indonesia pertama yang menerapkan passage retrieval berjenjang dan ekstraksi tipe jawaban; relevan langsung dengan pemisahan tahap retrieval awal dan pemeringkatan ulang berbasis fitur.
2. **Suhartono, Christiansen, & Aryo (2014)** — membandingkan Vector Space Model (TF-IDF) dan BM25 pada penelusuran dokumen akademik berbahasa Indonesia; membuktikan keunggulan BM25 dalam membatasi pengaruh saturasi term frekuen.
3. **Taufik & Purwarianti (2011)** — meneliti pengaruh perluasan kueri (*query expansion*) berbasis sinonim dan variasi morfologi terhadap peningkatan *recall* pada sistem temu kembali informasi Bahasa Indonesia.

---

## Daftar Referensi (Harvard Anglia Ruskin — Terverifikasi)

- Ferrucci, D., Brown, E., Chu-Carroll, J., Fan, J., Gondek, D., Kalyanpur, A.A., Lally, A., Murdock, J.W., Nyberg, E., Prager, J., Schlaefer, N. & Welty, C. (2010) 'Building Watson: An overview of the DeepQA project', *AI Magazine*, 31(3), pp. 59–79. doi: 10.1609/aimag.v31i3.3678.
- Jurafsky, D. & Martin, J.H. (2009) *Speech and Language Processing: An Introduction to Natural Language Processing, Computational Linguistics, and Speech Recognition*. 2nd edn. Upper Saddle River, NJ: Prentice Hall.
- Lin, J. (2007) 'An exploration of the principles underlying redundancy-based factoid question answering', *ACM Transactions on Information Systems*, 25(2), p. 6. doi: 10.1145/1229179.1229181.
- Manning, C.D., Raghavan, P. & Schütze, H. (2008) *Introduction to Information Retrieval*. Cambridge: Cambridge University Press. doi: 10.1017/CBO9780511809071.
- Purwarianti, A., Masuda, F. & Matsuo, H. (2007) 'A method of question answering system for Indonesian language', *Proceeding of the 2007 International Conference on Electrical Engineering and Informatics (ICEEI)*, Bandung, Indonesia, pp. 248–251.
- Roberts, I. & Gaizauskas, R. (2004) 'Evaluating passage retrieval approaches for question answering', in *Proceedings of the 26th European Conference on Information Retrieval (ECIR 2004)*. Berlin: Springer, pp. 72–84. doi: 10.1007/978-3-540-24752-4_6.
- Robertson, S. & Zaragoza, H. (2009) 'The probabilistic relevance framework: BM25 and beyond', *Foundations and Trends in Information Retrieval*, 3(4), pp. 333–389. doi: 10.1561/1500000019.
- Robertson, S.E., Walker, S., Jones, S., Hancock-Beaulieu, M.M. & Gatford, M. (1994) 'Okapi at TREC-3', in *Proceedings of the Third Text REtrieval Conference (TREC-3)*. Gaithersburg, MD: NIST, pp. 109–126.
- Salton, G. & Buckley, C. (1988) 'Term-weighting approaches in automatic text retrieval', *Information Processing & Management*, 24(5), pp. 513–523. doi: 10.1016/0306-4573(88)90021-0.
- Suhartono, D., Christiansen, K. & Aryo, B. (2014) 'Analysis on TF-IDF and BM25 performance in Indonesian question answering system', *Journal of Telecommunication, Electronic and Computer Engineering*, 6(2), pp. 15–20.
- Taufik, M. & Purwarianti, A. (2011) 'Query expansion implementation in Indonesian question answering system for factoid question', in *Proceedings of the 2011 International Conference on Electrical Engineering and Informatics (ICEEI)*. IEEE, pp. 1–5. doi: 10.1109/ICEEI.2011.6021671.
- Voorhees, E.M. (1999) 'The TREC-8 question answering track report', in *Proceedings of the Eighth Text REtrieval Conference (TREC-8)*. Gaithersburg, MD: NIST, pp. 77–82.
