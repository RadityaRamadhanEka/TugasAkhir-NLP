# Taksonomi Question Processing & Kontrak Nilai (Modul Anggota 3 — Yusuf)

Dokumen ini menjadi acuan resmi antara modul **Question Processing** (Anggota 3 — Yusuf), **Preprocessing / Knowledge Triples** (Anggota 2 — Radit), **Retrieval & Reranking** (Anggota 4 — Azza), dan **Answer Extraction & Evaluasi** (Anggota 5 — Zulfan).

Seluruh tipe dasar mengikuti [`src/contracts.py`](../src/contracts.py).

---

## 1. Pemetaan Resmi `intent` → `question_category` → `answer_type` → `predicate`

- `question_category` wajib salah satu dari `Literal["factoid", "definition", "list", "narrative", "yes_no"]`.
- `answer_type_coarse` wajib salah satu dari 6 kelas umum Taksonomi Li & Roth (2005): `ABBREVIATION`, `ENTITY`, `DESCRIPTION`, `HUMAN`, `LOCATION`, `NUMERIC`.
- `answer_type` berformat `<COARSE>:<fine>`.

| `intent` | Contoh Pertanyaan | `question_category` | `answer_type_coarse` | `answer_type` | `relations[].predicate` |
|---|---|---|---|---|---|
| `course_prerequisite` | Apa prasyarat Kecerdasan Artifisial Lanjut? | `factoid` | `ENTITY` | `ENTITY:prerequisite` | `prerequisite_of` |
| `course_min_grade` | Berapa nilai minimum prasyarat Jaringan Saraf Tiruan? | `factoid` | `NUMERIC` | `NUMERIC:grade` | `min_grade` |
| `course_sks` | Berapa SKS Basis Data? | `factoid` | `NUMERIC` | `NUMERIC:count` | `sks` |
| `course_semester` | Basis Data diambil di semester berapa? | `factoid` | `NUMERIC` | `NUMERIC:order` | `semester` |
| `course_code` | Apa kode MK Basis Data? | `factoid` | `NUMERIC` | `NUMERIC:code` | `course_code` |
| `course_name` | Mata kuliah apa yang berkode CIF63110? | `factoid` | `ENTITY` | `ENTITY:course_name` | `course_name` |
| `course_practicum` | Apakah Sistem Operasi memiliki praktikum? | `yes_no` | `DESCRIPTION` | `DESCRIPTION:yes_no` | `has_practicum` |
| `course_list_semester` | Sebutkan mata kuliah semester 3! | `list` | `ENTITY` | `ENTITY:course_list` | `semester` *(object terisi)* |
| `elective_group` | MK pilihan apa saja di kelompok Perekayasa Infrastruktur Komputasi? | `list` | `ENTITY` | `ENTITY:course_list` | `elective_group_member` |
| `learning_path` | MK apa saja pada learning path Data Scientist? | `list` | `ENTITY` | `ENTITY:course_list` | `learning_path_member` |
| `learning_path_list` | Learning path apa saja yang tersedia? | `list` | `ENTITY` | `ENTITY:learning_path` | *(tidak ada / `[]`)* |
| `total_sks` | Berapa total SKS mata kuliah muatan program studi? | `factoid` | `NUMERIC` | `NUMERIC:count` | `total_sks` |
| `curriculum_transition` | Bagaimana aturan peralihan bagi mahasiswa semester 5? | `narrative` | `DESCRIPTION` | `DESCRIPTION:manner` | *(tidak ada / `[]`)* |
| `course_equivalence` | MK kurikulum 2024 apa yang setara dengan CIF61011 Kecerdasan Buatan? | `factoid` | `ENTITY` | `ENTITY:course_name` | `equivalent_to` |
| `cpl` | Apa isi IF_CPL_KK1? | `definition` | `DESCRIPTION` | `DESCRIPTION:definition` | `cpl_description` |
| `graduate_profile` | Apa saja profil lulusan Teknik Informatika? | `list` | `HUMAN` | `HUMAN:title` | *(tidak ada / `[]`)* |
| `vision_mission` | Apa visi program studi Teknik Informatika? | `definition` | `DESCRIPTION` | `DESCRIPTION:definition` | *(tidak ada / `[]`)* |
| `course_description` | Apa yang dipelajari di MK Komputer Grafis? | `definition` | `DESCRIPTION` | `DESCRIPTION:definition` | `course_description` |
| `mbkm` | Apa saja bentuk kegiatan Merdeka Belajar? | `list` | `ENTITY` | `ENTITY:other` | *(tidak ada / `[]`)* |
| `abbreviation` | Apa kepanjangan MBKM? | `definition` | `ABBREVIATION` | `ABBREVIATION:expansion` | *(tidak ada / `[]`)* |
| `other` | *(fallback pertanyaan di luar cakupan domain)* | `factoid` | `DESCRIPTION` | `DESCRIPTION:other` | *(tidak ada / `[]`)* |

> **Catatan keselarasan Li & Roth (2005):**
> - Nomor semester memakai `NUMERIC:order` (urutan ordinal), bukan `NUMERIC:period` (durasi).
> - Kode mata kuliah memakai `NUMERIC:code` (kode identifikasi alfanumerik).
> - Aturan peralihan memakai `DESCRIPTION:manner` (prosedur/cara penanganan).
> - Bila `speech_act == "yes_no"`, `question_category` ditetapkan menjadi `"yes_no"`.

---

## 2. Aturan `speech_act` (PBA14 Slide 17)

Urutan evaluasi prioritas (aturan pertama yang cocok menang):

1. `indirect_request`: mengandung ungkapan permintaan sopan/tidak langsung (`tolong`, `mohon`, `saya ingin (tahu|mengetahui)`, `boleh(kah)? (saya )?(tahu|minta)`, `bisa(kah)? (anda|kamu)? (sebutkan|jelaskan|beri)`).
2. `command`: diawali kata kerja imperatif (`sebutkan`, `jelaskan`, `tampilkan`, `tuliskan`, `berikan`, `uraikan`, `daftarkan`, `daftar`).
3. `yes_no`: diawali `apakah`, `apa benar`, `benarkah`, atau kata tanya `-kah` di awal (`adakah`, `wajibkah`, `bisakah` tanpa kata kerja perintah sesudahnya).
4. `wh`: mengandung kata tanya WH Bahasa Indonesia (`apa`, `siapa`, `berapa`, `kapan`, `dimana`, `di mana`, `mengapa`, `kenapa`, `bagaimana`, `mana`, `manakah`, atau bentuk singkat informal seperti `brp`).
5. Default: `wh`.

---

## 3. Tipe Entitas (`entities[].type`) & Normalisasi

| `type` | Metode Ekstraksi | Format `normalized_value` | Contoh |
|---|---|---|---|
| `course_code` | Regex `\b[a-z]{3}\d{5}(?:-\d)?\b` | UPPERCASE | `cif63110` → `CIF63110` |
| `course_name` | Gazetteer *longest-match* (termasuk alias seperti `AI`, `KA`, `KAL`, `IMK`, `APS`, `RPL`, `MLOps`) | Nama kanonik resmi 2024 | `"kecerdasan artifisial lanjut"` → `"Kecerdasan Artifisial Lanjut"` |
| `semester` | Regex `semester\s+(\d|[ivx]+|satu..delapan|antara)` | `"1"`–`"8"` atau `"antara"` | `"semester tiga"` → `"3"` |
| `sks_value` | Regex `(\d+)\s*sks` | Angka string | `"3 sks"` → `"3"` |
| `cpl_code` | Regex `if[_\s-]?cpl[_\s-]?(s|p|ku|kk|kp)\s?(\d)` | `IF_CPL_<KATEGORI><N>` | `"cpl kk1"` → `"IF_CPL_KK1"` |
| `learning_path` | Gazetteer 11 *learning path* + alias spasi | Nama kanonik | `"data science"` → `"Data Scientist"` |
| `elective_group` | Gazetteer 3 kelompok MK pilihan Tabel 7.1–7.3 | Nama kanonik | `"infrastruktur komputasi"` → `"Perekayasa Infrastruktur Komputasi"` |
| `grade` | Regex `nilai\s+(minimal\s+|minimum\s+)?([a-e])\b` | UPPERCASE huruf | `"nilai minimal c"` → `"C"` |
| `curriculum_year` | Regex `\b(2020|2024)\b` | Tahun string | `"2024"` |
| `abbreviation` | Kamus singkatan (`MBKM`, `SKS`, `CPL`, `CPMK`, `MK`, `PkM`, `BK`) | UPPERCASE | `"mbkm"` → `"MBKM"` |

---

## 4. Vocabulary `relations[].predicate` (Sinkronisasi ⛔ GATE-A)

Daftar predikat standar yang dihasilkan oleh `extract_relations` (slot yang ditanyakan diisi `null`/`None`):

- `course_code`
- `course_name`
- `sks`
- `semester`
- `prerequisite_of`
- `min_grade`
- `has_practicum`
- `elective_group_member`
- `learning_path_member`
- `equivalent_to`
- `cpl_description`
- `course_description`
- `total_sks`

**Catatan untuk Anggota 2 (Radit):** Mohon konfirmasi apakah `knowledge_triples.jsonl` dapat menggunakan daftar predikat di atas agar `retrieve_triples()` milik Anggota 4 dapat mencocokkan langsung tanpa lapisan pemetaan tambahan.

---

## 5. Kontrak `query_keywords`, `expanded_queries`, dan `pos_tags`

- **`query_keywords`**: berisi token kata kunci ter-normalisasi **tanpa stemming** (stemming dilakukan di sisi modul Preprocessing/Retrieval oleh Anggota 2 dan 4), tanpa kata tanya & stopword umum, namun tetap mempertahankan negasi (`tidak`), angka, kode MK, kode CPL, serta frasa `normalized_value` entitas.
- **`expanded_queries`**: maksimal 5 string ekspansi tanpa duplikat, berisi perluasan sinonim/singkatan domain (`MK` ↔ `mata kuliah`, `AI` ↔ `kecerdasan artifisial`, kode MK ↔ nama MK) dan reformulasi pola deklaratif (gaya Lin 2007).
- **`pos_tags`**: memakai tagset IDN Tagged Corpus (Dinakaramani dkk., 2014) yang membedakan kata tanya dengan tag **`WH`** (bukan `WP`), serta memberikan override **`NNP`** untuk kode MK, kode CPL, dan token nama mata kuliah dari gazetteer.
