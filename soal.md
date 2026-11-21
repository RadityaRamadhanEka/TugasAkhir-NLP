# Tugas Akhir (TP) Pemrosesan Bahasa Alami

> **STUDY HARD. DO GOOD AND THE GOOD LIFE WILL FOLLOW.**  
> **Putra Pandu Adikara, S.Kom., M.Kom.**  
> *2026*

---

## A. ATURAN PENGERJAAN

* Dikerjakan secara berkelompok maksimal **5 (lima) orang**.
* Dikerjakan dengan bahasa pemrograman **Python**.
* Baca dan pahami soal dengan sebaik-baiknya supaya tidak ada poin nilai yang terlewatkan. Bila perlu dicetak. Apabila ada hal yang tidak dimengerti segera ditanyakan.
* **Plagiarisme** (bahkan hanya satu baris saja) tidak akan ditolerir dan akan mendapatkan nilai **E**. Baik yang memberi contoh atau pun yang mencontoh akan mendapatkan pengurangan nilai (atau akan ada kebijakan lain).
* Penggunaan AI sangat terbatas dan tidak diperbolehkan untuk membuat semuanya seperti kode program atau laporan. Lakukan pembuatan sendiri (*from scratch*) secara berkelompok dengan pembagian tugas merata.

---

## B. PENGUMPULAN TUGAS

* Batas waktu pengumpulan di **BRONE**, perhatikan jam server.
* Keterlambatan akan mengakibatkan pengurangan nilai sebesar **~10 poin tiap hari** (dan ada pengurangan tiap menit/jam keterlambatan).
* Pengumpulan berupa *soft-copy* oleh salah satu anggota.
* Lampirkan **SEMUA FAIL** (`.DOCX`/`.PDF`, `.py`, dll.) dengan terkompres `ZIP`/`RAR` dengan format:
  `[TX][PBA-PRODI-KELAS] NamaMahasiswa.ZIP`
* Nama fail yang dikumpulkan dikompres (`.ZIP`/`.RAR`) meski isinya satu fail dengan format:
  `[TX][PBA-Kelas] NamaMahasiswa`
  * `TX` adalah kode tugas, apabila Tugas 1 maka `T1`, Tugas 2 maka `T2`, dst. Tugas Akhir/Proyek Akhir: `TP`.
  * `KELAS` diisi kode kelas misal `A`, `B`, `C`, dst.
  * `NamaMahasiswa` maksudnya tidak perlu menuliskan semua nama anggota, tapi nama satu anggota saja, sebagai ketua kelompok/penanggung jawab unggahan.
  * **Contoh:** `[TP][PBA-B] Steve Gates.ZIP` *(Tugas 1, kelas PIPT Kelas B)*
* Di dalam fail `.ZIP` di atas berisi:
  * Fail `.DOCX`/`.PDF` untuk Penjelasan Kode Program (seluruh jawaban soal jadi satu dokumen)
  * Fail `.py` (Python) untuk kode program
  * Fail lainnya yang diperlukan (korpus, pembobotan kata, dll.)

---

## C. TUJUAN TUGAS

Pada tugas ini mahasiswa diharapkan dapat mengimplementasikan atau mengembangkan beberapa *task* untuk pembuatan aplikasi pemrosesan bahasa alami. Diharapkan dengan mengerjakan tugas ini mahasiswa dapat mengimplementasikan alat bantu umum di bidang Pemrosesan Bahasa Alami seperti *POS tagger*, *syntactic parser*, *LLM*, dll. dalam aplikasi nyata. Implementasi dari materi yang telah diajarkan dalam bentuk proyek akhir dengan topik **Sistem Tanya Jawab (*Question Answer System*)**.

Dengan adanya tugas ini diharapkan dapat membentuk perilaku kecendekiawanan sesuai tujuan kurikulum, dapat bekerjasama dalam tim, disiplin, dan mampu bekerja keras sesuai batas waktu yang ditentukan.

---

## D. DESKRIPSI TUGAS

Pada tugas ini titik beratnya adalah implementasi aplikasi dengan memanfaatkan beberapa *task* yang sudah dijelaskan sebelumnya seperti *POS Tagger*, *Named Entity Recognition*, *Dependency Parsing*, *Word Embedding*, *LLM*, dll. Implementasi/pengembangan yang dimaksud tentunya harus disertai dengan metodologi layaknya metodologi penelitian yang jelas.

**Topik tugas akhir ini adalah:**

1. **Question Answering Sederhana (Tanpa LLM)** - Menjawab pertanyaan yang diajukan pengguna dengan sederhana berdasarkan teks yang diberikan. Pertanyaan dapat berupa *closed* (spesifik) atau *open question* (subjektif). Menjawab pertanyaan subjektif merupakan tantangan utama saat ini, misalnya *virtual assistant* yang realistis. Namun, masalah dapat dibatasi hanya untuk pertanyaan *factoid* saja, meski jika memungkinkan jenis pertanyaan lainnya.
   * Jelaskan arsitektur dan bagaimana tahapan dalam sistem *Question Answer*, misalnya *question processing* seperti *question classification/intent classification*, *answer type detection*, *passage retrieval*, hingga *answer processing*.
2. **Question Answering dengan RAG (Dengan LLM)** - Menjawab pertanyaan yang kompleks berdasarkan referensi yang ada di korpus dengan *Retrieval Augmented Generation* (RAG) untuk menghindari halusinasi dan bias. Diperbolehkan menggunakan dataset *benchmark* yang berisi pasangan pertanyaan dan jawaban.
   * Jelaskan arsitektur dan bagaimana tahapan dalam sistem *Question Answer* khusus untuk RAG seperti halnya pada topik 1.
   * Topik kedua ini *"tricky"* dalam artian bagaimana menghubungkan dengan materi-materi kuliah yang sudah pernah diberikan sebelumnya dibandingkan dengan topik nomor 1.
   * Jelaskan pengembangan sistem secara rinci termasuk bagaimana melakukan evaluasi terhadap pertanyaan dan jawaban yang diberikan oleh sistem dibandingkan dengan *ground truth*.

**Ketentuan Tambahan:**
* Korpus, data latih, dan data uji dapat dicari/dibuat sendiri dengan berbagai genre: berita, novel, musik, sinopsis film, artikel ilmiah, dll.
* Jelaskan bagaimana hubungan materi kuliah yang telah diberikan dengan tugas akhir yang tim Anda buat seperti *POS Tagger*, *NER*, *Grammar* (termasuk RegEx), *Dependency Parsing*, *Word Embedding*, dll.
* Penggunaan AI hanya diperbolehkan misalnya untuk pembuatan pasangan pertanyaan dan jawaban dengan catatan wajib dicek manual kembali.

---

### Struktur Laporan

* **Sampul muka**
* **Lembar 1:** Tuliskan identitas kelompok, nama dan NIM anggota kelompok, kelas, program studi.
* **Lembar 2:** Jelaskan tanggung jawab tiap anggota dalam proyek akhir. Bila tidak mengerjakan sama sekali, tidak usah dituliskan tanggung jawabnya.
* **Abstrak**
  Abstrak harus menguraikan secara cermat dan singkat tentang latar belakang, data dan metodologi yang digunakan, hingga bagaimana pengujian dilakukan. Di bagian akhir tuliskan hasil pengujian disertai metrik dan nilai kuantitatifnya.
* **Bab I. Pendahuluan**
  Uraikan latar belakang dan permasalahan yang akan dilakukan, tujuan khusus dan urgensi penelitian. Pada bab ini juga dijelaskan temuan yang ditargetkan (gejala atau kaidah, metode, teori atau antisipasi) yang mempunyai kontribusi mendasar. Tuliskan rumusan masalah, tujuan, manfaat, dan batasan masalah. Isi dari rumusan masalah, tujuan, manfaat haruslah berkaitan.
* **Bab II. Tinjauan Pustaka**
  Gunakan sumber pustaka acuan primer yang relevan dan terkini dengan mengemukakan hasil penelitian pada jurnal ilmiah. Jelaskan juga studi pendahuluan yang telah dilaksanakan dan hasil yang sudah dicapai. Jelaskan pula bagaimana melakukan evaluasi sesuai kajian pustaka yang dilakukan. Jangan lupa tuliskan rujukan yang digunakan dan bagaimana melakukan kutipan sesuai di Daftar Rujukan dengan mematuhi gaya penulisan Daftar Rujukan/Pustaka menggunakan **Harvard Anglia-Ruskin** (sesuai Panduan Skripsi versi 2).
* **Bab III. Metodologi Penelitian**
  Dilengkapi dengan diagram alir/*flowchart* penelitian yang menggambarkan metodologi penelitian termasuk gambaran umum sistem. Kesalahan umum gambar metodologi biasanya dimulai dari studi literatur hingga pengambilan simpulan (ini adalah teori metodologi penelitian secara umum, yang dimaksud dalam gambar ini adalah bagaimana tahapan penelitian sehubungan dengan tinjauan pustaka yang telah dilakukan dan spesifik/khusus terhadap penelitian yang Anda lakukan). Bagan penelitian harus dibuat secara utuh dengan penahapan yang jelas, mulai dari mana, apa masukannya, bagaimana prosesnya, dan bagaimana keluarannya. Metode penelitian menjelaskan apa yang akan dilakukan secara terstruktur, metode yang dilakukan.
  Sistem dapat berupa *open* atau *closed question*. Misalnya berupa sistem tanya jawab berupa *factoid* atau jenis yang lain. Metode/teknik yang digunakan dapat menggabungkan dengan teknik pada bidang lain, misalnya temu kembali/perolehan informasi, *machine learning*, tetapi tidak boleh semata-mata hanya teknik pada temu kembali/perolehan informasi tanpa ada teknik yang telah diajarkan pada kuliah Pemrosesan Bahasa Alami (misalnya tetap diperlukan adanya *POS Tagging*, *information extraction*, atau teknik lainnya).
* **Bab IV. Implementasi**
  Jelaskan mengenai persiapan yang dilakukan (data, *query*, tahapan penelitian, cara evaluasi dll.). Program wajib dibuat tanpa diperbolehkan adanya plagiarisme. Untuk pengembangan program yang dilakukan, jelaskan mana program yang dibuat sendiri, mana yang menggunakan program orang lain, dsb. Dalam tugas diperbolehkan menggunakan *library* NLTK, SpaCy, dll. tetapi tetap harus dapat menjelaskan fungsinya untuk apa dan jelaskan mana yang dibuat sendiri.
* **Bab V. Hasil dan Pembahasan / Hasil Evaluasi Aplikasi yang Telah Dikembangkan**
  Jelaskan percobaan beserta cara mengevaluasi yang dilakukan, hasil yang diperoleh, atau aplikasi yang telah selesai dikembangkan, apa manfaatnya, kekurangannya dan pengembangan lebih lanjut yang bisa dilakukan. Buat **20 daftar pertanyaan** sesuai korpus yang dibuat. Masing-masing anggota kelompok membuat pertanyaan. Lakukan evaluasi dengan cara menghitung berapa jawaban benar dan berapa jawaban salah (sesuai Tinjauan Pustaka pada Bab 2). Berikan penjelasan kenapa jawaban bisa salah atau bisa benar.
* **Bab VI. Penutup**
  Jelaskan hasil kesimpulan dan saran yang dapat diambil dari implementasi dan percobaan yang telah dilakukan. Isi kesimpulan harus sesuai dengan rumusan masalah. Sebagai contoh apabila ada 2 rumusan masalah, maka perlu ada 2 tujuan. Singkatnya, pertanyaan pada rumusan masalah dijawab di Kesimpulan.
* **Daftar Referensi**
  Disusun berdasarkan sistem nama dan tahun menggunakan *style* **Harvard Anglia-Ruskin** (sesuai Panduan Skripsi, gunakan program seperti Mendeley Desktop), dengan urutan abjad nama pengarang, tahun, judul tulisan, dan sumber. Hanya pustaka yang dikutip dalam usul penelitian yang dicantumkan dalam Daftar Referensi.

---

### Format Penulisan

1. Proposal berisi antara **minimal 15 halaman** (tidak termasuk halaman judul).
2. Margin tulisan adalah **3 cm** dari bagian kiri, **2 cm** dari bagian atas, bawah, dan kanan halaman.
3. Jarak antar kalimat adalah **1,15 spasi**.
4. Gunakan font **Aptos/Calibri** dengan ukuran **12** untuk isi Laporan dan **14** untuk halaman Judul.

### Keluaran yang Dikumpulkan

* *Soft copy* dalam bentuk `ZIP`/`RAR` berisi program beserta *source code* dan makalah, korpus, data latih, data uji.
* Apabila dimungkinkan maka akan diadakan presentasi tugas akhir.

---

### Referensi Penilaian Makalah

| Kategori | Poin Penilaian | Persentase |
| :--- | :--- | :---: |
| **Makalah** | Abstrak/Ringkasan | 5% |
| **Makalah** | Bab I: Pendahuluan | 15% |
| **Makalah** | Bab II: Kajian Pustaka | 10% |
| **Makalah** | Bab III: Metodologi termasuk kompleksitas metode/keterbaruan metode | 20% |
| **Makalah** | Bab IV: Implementasi termasuk penjelasan *source code* (tidak sekedar *source code* saja)* | 20% |
| **Makalah** | Bab V: Hasil, Analisis dan Pembahasan | 15% |
| **Makalah** | Bab VI: Penutup | 5% |
| **Program** | *Source code* dan data* | 10% |
| **Total** | | **100%** |

> *\*Catatan: Nilai nantinya juga akan bersifat individual.*

---

## E. PENGUMPULAN

Kompres semua berkas (masukan, termasuk misal hasil *pre-processing* maupun keluaran) berisi:

1. *Source code* Python (`file.py` atau Jupyter Notebook `.ipynb`).
2. Berkas lainnya, misalnya korpus, data latih, data uji, dll.
3. Berkas `jawaban.docx`/`pdf` berisi laporan untuk jawaban beserta beberapa *screenshot* hasil pengembangan sistem.
4. Buat fail `tanggungjawab.docx` berisi siapa yang bertanggung jawab mengerjakan setiap soalnya. Mahasiswa yang tidak mengerjakan tidak akan mendapatkan nilai meski berkelompok. Tanggung jawab ini bukan membuat laporan atau membuat presentasi, tapi menyelesaikan soal.

> *Selamat mengerjakan sebaik-baiknya. Practice makes perfect.*