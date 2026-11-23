"""Pembersihan artefak PDF, tokenisasi, normalisasi, stopword selektif, dan stemming.

Modul Anggota 2 (Radit) untuk menyiapkan representasi teks terstruktur (IR)
tanpa merusak teks asli maupun entitas domain kurikulum (kode MK, kode CPL, SKS).
"""

from __future__ import annotations

import re
from functools import lru_cache

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Pola entitas/kode domain yang harus dipertahankan keutuhannya saat tokenisasi & stemming.
_COURSE_CODE_RE = re.compile(r"^[a-z]{3}\d{5}(?:-\d)?$", re.IGNORECASE)
_CPL_CODE_RE = re.compile(r"^if_cpl_[a-z]+\d+$", re.IGNORECASE)
_CPMK_OR_PLO_RE = re.compile(r"^(?:cpmk|plo)-\d+$", re.IGNORECASE)
_NUMBER_OR_VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")

# Tokenisasi sadar-domain: menjaga kode MK, kode CPL, CPMK/PLO, angka desimal/tabel, & operator.
_TOKEN_PATTERN = re.compile(
    r"if_cpl_[a-z]+\d+"
    r"|[a-z]{3}\d{5}(?:-\d)?"
    r"|(?:cpmk|plo)-\d+"
    r"|>=|<=|>"
    r"|\d+(?:\.\d+)+"
    r"|[a-z0-9]+(?:-[a-z0-9]+)*",
    re.IGNORECASE,
)

# Artefak template silabus & fragmen kosong yang ditemukan di audit Modul 1.
_SYLLABUS_ARTIFACT_RE = re.compile(
    r"CPMK-\d+\s*\(%\)\s*:?(?:\s*CPMK-\d+\s*\(%\))*(?:\s*\(CPL:\s*(?:CPMK-\d+\s*\(%\))?\s*\))?",
    re.IGNORECASE,
)
_EMPTY_CPL_RE = re.compile(r"\(\s*CPL\s*:\s*\)", re.IGNORECASE)
_GLUED_CPL_PREFIX_RE = re.compile(r"\bCPL-\d+(?=IF_CPL_)", re.IGNORECASE)

# Akronim & kode domain yang huruf kapitalnya dipertahankan pada normalize_text.
_PRESERVE_UPPER_TOKENS = {
    "AI",
    "BK",
    "CPL",
    "CPMK",
    "FILKOM",
    "IF",
    "IT",
    "KA",
    "KK",
    "KU",
    "MBKM",
    "MK",
    "MKU",
    "ML",
    "NLP",
    "PLO",
    "PL",
    "SA",
    "SKS",
    "TI",
    "TIF",
    "UB",
    "UI",
    "UX",
}

# Stopword Bahasa Indonesia umum (tidak memuat negasi, syarat, angka, atau istilah kurikulum).
_INDONESIAN_STOPWORDS = frozenset(
    {
        "ada",
        "adalah",
        "adanya",
        "adapun",
        "agar",
        "akan",
        "akankah",
        "akhir",
        "akhirnya",
        "aku",
        "antara",
        "antaranya",
        "apa",
        "apabila",
        "apakah",
        "apalagi",
        "atas",
        "atau",
        "ataukah",
        "ataupun",
        "bagai",
        "bagaikan",
        "bagaimana",
        "bagaimanakah",
        "bagaimanapun",
        "bagi",
        "bagian",
        "bahkan",
        "bahwa",
        "bahwasanya",
        "baik",
        "banyak",
        "baru",
        "bawah",
        "beberapa",
        "begini",
        "beginian",
        "beginikah",
        "beginilah",
        "begitu",
        "begitukah",
        "begitulah",
        "begitupun",
        "bekerja",
        "belakang",
        "berada",
        "berapa",
        "berapakah",
        "berapalah",
        "berapapun",
        "berikut",
        "berikutnya",
        "berjumlah",
        "berkali",
        "berkata",
        "berkenaan",
        "berlainan",
        "berlalu",
        "berlangsung",
        "bermacam",
        "bermaksud",
        "bermula",
        "bersama",
        "bersiap",
        "bertanya",
        "berturut",
        "bertutur",
        "berujar",
        "berupa",
        "besar",
        "betul",
        "biasa",
        "biasanya",
        "bila",
        "bilakah",
        "bisa",
        "bisakah",
        "boleh",
        "bolehkah",
        "bolehlah",
        "buat",
        "bulan",
        "bung",
        "cara",
        "caranya",
        "cukup",
        "cukupkah",
        "cukuplah",
        "dahulu",
        "dalam",
        "dan",
        "dapat",
        "dari",
        "daripada",
        "datang",
        "dekat",
        "demi",
        "demikian",
        "demikianlah",
        "dengan",
        "depan",
        "di",
        "dia",
        "diantaranya",
        "dibuat",
        "didapat",
        "digunakan",
        "diinginkan",
        "dijelaskan",
        "dikarenakan",
        "dikatakan",
        "dikenal",
        "dilakukan",
        "dimaksud",
        "dimana",
        "dimisalkan",
        "dimulai",
        "diperbuat",
        "dipergunakan",
        "diperkirakan",
        "diperlukan",
        "dipersoalkan",
        "dipertanyakan",
        "dipunyai",
        "diri",
        "dirinya",
        "disampaikan",
        "disebut",
        "disebutkan",
        "disini",
        "disampaikan",
        "ditambahkan",
        "ditanya",
        "ditujukan",
        "diucapkan",
        "diungkapkan",
        "dong",
        "dulu",
        "empat",
        "enggak",
        "entah",
        "guna",
        "gunakan",
        "hal",
        "hampir",
        "hanya",
        "hanyalah",
        "hari",
        "harus",
        "haruslah",
        "harusnya",
        "hendak",
        "hendaklah",
        "hendaknya",
        "hingga",
        "ia",
        "ialah",
        "ibu",
        "ikut",
        "ingat",
        "ingin",
        "ini",
        "inikah",
        "inilah",
        "itu",
        "itukah",
        "itulah",
        "jadi",
        "jadilah",
        "jadinya",
        "jangan",
        "jangankan",
        "janganlah",
        "jauh",
        "jawab",
        "jawaban",
        "jawabnya",
        "jelas",
        "jika",
        "jikalau",
        "juga",
        "justru",
        "kala",
        "kalau",
        "kalaulah",
        "kalaupun",
        "kalian",
        "kami",
        "kamu",
        "kan",
        "kapan",
        "kapankah",
        "kapanpun",
        "karena",
        "karenanya",
        "kasus",
        "kata",
        "katakan",
        "katakanlah",
        "katanya",
        "ke",
        "keadaan",
        "kebetulan",
        "kecil",
        "kedua",
        "keduanya",
        "keinginan",
        "kelamaan",
        "kelihatan",
        "kelihatannya",
        "keluar",
        "kembali",
        "kemudian",
        "kemungkinan",
        "kemungkinannya",
        "kenapa",
        "kepada",
        "kepadanya",
        "kesampaian",
        "keseluruhan",
        "keterlaluan",
        "ketika",
        "khususnya",
        "kini",
        "kinilah",
        "kira",
        "kiranya",
        "kita",
        "kok",
        "lagi",
        "lagian",
        "lah",
        "lain",
        "lainnya",
        "lalu",
        "lama",
        "lamanya",
        "lanjut",
        "lanjutnya",
        "lewat",
        "lima",
        "luar",
        "macam",
        "maka",
        "makanya",
        "makin",
        "malah",
        "malahan",
        "mampu",
        "mampukah",
        "mana",
        "manakala",
        "manalagi",
        "masa",
        "masalah",
        "masih",
        "masihkah",
        "masing",
        "mau",
        "maupun",
        "melainkan",
        "melakukan",
        "melalui",
        "melihat",
        "memang",
        "membuat",
        "memberi",
        "memberikan",
        "membuatnya",
        "memerlukan",
        "memihak",
        "meminta",
        "memintakan",
        "memisalkan",
        "memperbuat",
        "mempergunakan",
        "memperkirakan",
        "memperlihatkan",
        "mempersiapkan",
        "mempersoalkan",
        "mempertanyakan",
        "mempunyai",
        "memulai",
        "memungkinkan",
        "menaiki",
        "menambahkan",
        "menandaskan",
        "menanti",
        "menanya",
        "menanyai",
        "menanyakan",
        "mendapat",
        "mendapatkan",
        "mendatang",
        "mendatangi",
        "mendatangkan",
        "menegaskan",
        "mengakhiri",
        "mengapa",
        "mengatakan",
        "mengatakannya",
        "mengenai",
        "mengerjakan",
        "mengetahui",
        "menggunakan",
        "menghendaki",
        "mengibaratkan",
        "mengibaratkannya",
        "mengingat",
        "mengingatkan",
        "menginginkan",
        "mengira",
        "mengucapkan",
        "mengucapkannya",
        "mengungkapkan",
        "menjadi",
        "menjawab",
        "menjelaskan",
        "menuju",
        "menunjuk",
        "menunjuki",
        "menunjukkan",
        "menurut",
        "menuturkan",
        "menyampaikan",
        "menyangkut",
        "menyatakan",
        "menyebutkan",
        "menyeluruh",
        "menyiapkan",
        "merasa",
        "mereka",
        "merekalah",
        "merupakan",
        "meski",
        "meskipun",
        "meyakini",
        "meyakinkan",
        "minta",
        "mirip",
        "misal",
        "misalkan",
        "misalnya",
        "mula",
        "mulai",
        "mulailah",
        "mulanya",
        "mungkin",
        "mungkinkah",
        "nah",
        "naik",
        "namun",
        "nanti",
        "nantinya",
        "nyaris",
        "nyatanya",
        "oleh",
        "olehnya",
        "pada",
        "padahal",
        "padanya",
        "pak",
        "pantas",
        "para",
        "pasti",
        "pastilah",
        "penting",
        "pentingnya",
        "per",
        "percuma",
        "perlu",
        "perlukah",
        "perlunya",
        "pernah",
        "persoalan",
        "pertama",
        "pertanyaan",
        "pertanyakan",
        "pihak",
        "pihaknya",
        "pukul",
        "pula",
        "pun",
        "punya",
        "rasa",
        "rasanya",
        "rata",
        "rupanya",
        "saat",
        "saatnya",
        "saja",
        "sajalah",
        "saling",
        "sama",
        "sambil",
        "sampai",
        "sana",
        "sangat",
        "sangatlah",
        "satu",
        "saya",
        "sayalah",
        "se",
        "sebab",
        "sebabnya",
        "sebagai",
        "sebagaimana",
        "sebagainya",
        "sebagian",
        "sebaik",
        "sebaiknya",
        "sebaliknya",
        "sebanyak",
        "sebegini",
        "sebegitu",
        "sebelum",
        "sebelumnya",
        "sebenarnya",
        "seberapa",
        "sebesar",
        "sebetulnya",
        "sebisanya",
        "sebuah",
        "sebut",
        "sebutlah",
        "sebutnya",
        "secara",
        "secukupnya",
        "sedang",
        "sedangkan",
        "sedemikian",
        "sedikit",
        "sedikitnya",
        "seenaknya",
        "segala",
        "segalanya",
        "segera",
        "seharusnya",
        "sehingga",
        "seingat",
        "sejak",
        "sejauh",
        "sejenak",
        "sejumlah",
        "sekadar",
        "sekali",
        "sekalian",
        "sekaligus",
        "sekalipun",
        "sekarang",
        "sekecil",
        "seketika",
        "sekiranya",
        "sekitar",
        "sekitarnya",
        "sekurang",
        "sekurangnya",
        "sela",
        "selain",
        "selaku",
        "selalu",
        "selama",
        "selamanya",
        "selanjutnya",
        "seluruh",
        "seluruhnya",
        "semacam",
        "semakin",
        "semampu",
        "semampunya",
        "semasa",
        "semasih",
        "semata",
        "semata-mata",
        "semaunya",
        "sementara",
        "semisal",
        "semisalnya",
        "sempat",
        "semua",
        "semuanya",
        "semula",
        "sendiri",
        "sendirian",
        "sendirinya",
        "seolah",
        "seorang",
        "sepanjang",
        "sepantasnya",
        "sepantasnyalah",
        "seperlunya",
        "seperti",
        "sepertinya",
        "sepihak",
        "sering",
        "seringnya",
        "serta",
        "serupa",
        "sesaat",
        "sesama",
        "sesampai",
        "sesegera",
        "sesekali",
        "seseorang",
        "sesuatu",
        "sesuatunya",
        "sesudah",
        "sesudahnya",
        "setelah",
        "setempat",
        "setengah",
        "seterusnya",
        "setiap",
        "setiba",
        "setibanya",
        "setinggi",
        "seusai",
        "sewaktu",
        "siap",
        "siapa",
        "siapakah",
        "siapapun",
        "sini",
        "sinilah",
        "soal",
        "soalnya",
        "suatu",
        "sudah",
        "sudahkah",
        "sudahlah",
        "supaya",
        "tadi",
        "tadinya",
        "tahu",
        "tahun",
        "tampak",
        "tampaknya",
        "tandas",
        "tandasnya",
        "tanya",
        "tanyakan",
        "tanyanya",
        "tapi",
        "tegas",
        "tegasnya",
        "telah",
        "tempat",
        "tengah",
        "tentang",
        "tentu",
        "tentulah",
        "tentunya",
        "tepat",
        "terakhir",
        "terasa",
        "terbanyak",
        "terdahulu",
        "terdapat",
        "terdiri",
        "terhadap",
        "terhadapnya",
        "teringat",
        "terjadi",
        "terjadilah",
        "terjadinya",
        "terkira",
        "terlalu",
        "terlebih",
        "terlihat",
        "termasuk",
        "ternyata",
        "tersampaikan",
        "tersebut",
        "tersebutlah",
        "tertentu",
        "tertuju",
        "terus",
        "terutama",
        "tetap",
        "tetapi",
        "tiap",
        "tiba",
        "tidakkah",
        "tidaklah",
        "tiga",
        "tinggi",
        "toh",
        "tunjuk",
        "turut",
        "tutur",
        "tuturnya",
        "ucap",
        "ucapnya",
        "ujar",
        "ujarnya",
        "umum",
        "umumnya",
        "ungkap",
        "ungkapnya",
        "untuk",
        "usah",
        "usai",
        "waduh",
        "wah",
        "wahai",
        "waktu",
        "waktunya",
        "walau",
        "walaupun",
        "wong",
        "yaitu",
        "yakin",
        "yakni",
        "yang",
    }
)

# Istilah negasi, syarat, dan domain kurikulum yang HARUS dipertahankan saat filtering.
_PROTECTED_TERMS = frozenset(
    {
        "tidak",
        "bukan",
        "tanpa",
        "belum",
        "minimal",
        "minimum",
        "maksimal",
        "maksimum",
        "lebih",
        "kurang",
        "wajib",
        "pilihan",
        "prasyarat",
        "syarat",
        "lulus",
        "nilai",
        "semester",
        "sks",
        "praktikum",
        "mk",
        "cpl",
        "cpmk",
        "mbkm",
        "sa",
        "setara",
        "ekuivalen",
        "peralihan",
        "konversi",
        "total",
        "jumlah",
        "ya",
    }
)

_NON_STEM_ACRONYMS = frozenset(
    {
        "ai",
        "api",
        "bk",
        "cpl",
        "cpmk",
        "dns",
        "filkom",
        "it",
        "kb",
        "kk",
        "ku",
        "mbkm",
        "mk",
        "mku",
        "ml",
        "mlops",
        "nlp",
        "plo",
        "qa",
        "sa",
        "sks",
        "ti",
        "tif",
        "ub",
        "ui",
        "ux",
        "web",
    }
)


@lru_cache(maxsize=1)
def _get_stemmer():
    """Menginisialisasi stemmer Sastrawi sekali saja dengan lookup kamus O(1) berbasis set."""
    stemmer = StemmerFactory().create_stemmer()
    delegated = getattr(stemmer, "delegatedStemmer", None)
    dictionary = getattr(delegated, "dictionary", None)
    if dictionary is not None and isinstance(getattr(dictionary, "words", None), list):
        dictionary.words = set(dictionary.words)
    return stemmer


@lru_cache(maxsize=16384)
def _stem_word(word: str) -> str:
    """Melakukan stemming satu kata dengan memoization agar token berulang diproses instan."""
    return _get_stemmer().stem(word)


def is_protected_code(token: str) -> bool:
    """Memeriksa apakah token adalah kode domain/angka yang tidak boleh diubah stemmer."""
    return bool(
        _COURSE_CODE_RE.match(token)
        or _CPL_CODE_RE.match(token)
        or _CPMK_OR_PLO_RE.match(token)
        or _NUMBER_OR_VERSION_RE.match(token)
        or token in {">=", "<=", ">"}
    )


def clean_text(raw_text: str) -> str:
    """Membersihkan artefak PDF (nomor halaman sisipan, spasi berlebih, artefak CPMK-1, pemenggalan baris)."""
    if not raw_text:
        return ""

    text = raw_text.replace("\xa0", " ").replace("\u200b", "")
    # Hilangkan artefak template silabus seperti "CPMK-1 (%): CPMK-2 (%) (CPL: CPMK-5 (%))"
    text = _SYLLABUS_ARTIFACT_RE.sub(" ", text)
    # Hilangkan tag CPL kosong "(CPL: )"
    text = _EMPTY_CPL_RE.sub("", text)
    # Pisahkan prefix typo seperti "CPL-3IF_CPL_KK2" -> "IF_CPL_KK2"
    text = _GLUED_CPL_PREFIX_RE.sub("", text)
    # Rapikan baris baru dan spasi ganda
    text = re.sub(r"[ \t]*\r?\n[ \t]*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    # Rapikan spasi sebelum tanda baca penutup
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def normalize_text(text: str) -> str:
    """Menormalisasi teks (case folding selektif, simbol centang & operator, tanpa merusak kode MK/SKS/semester)."""
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    cleaned = cleaned.replace("≥", ">=").replace("≤", "<=")
    cleaned = cleaned.replace("✓", "ya").replace("✔", "ya")

    def _norm_word(match: re.Match[str]) -> str:
        word = match.group(0)
        if _COURSE_CODE_RE.match(word) or _CPL_CODE_RE.match(word) or _CPMK_OR_PLO_RE.match(word):
            return word.upper()
        if word.upper() in _PRESERVE_UPPER_TOKENS:
            return word.upper()
        return word.lower()

    normalized = re.sub(
        r"IF_CPL_[A-Za-z]+\d+|[A-Za-z]{3}\d{5}(?:-\d)?|(?:CPMK|PLO)-\d+|[A-Za-z]+",
        _norm_word,
        cleaned,
    )
    return re.sub(r"\s{2,}", " ", normalized).strip()


def tokenize_text(text: str) -> list[str]:
    """Memecah teks menjadi token lowercase dengan tetap menjaga kode MK (mis. cif63110) & kode CPL."""
    if not text:
        return []

    cleaned = clean_text(text).replace("≥", ">=").replace("≤", "<=").replace("✓", "ya").replace("✔", "ya")
    tokens = [tok.lower() for tok in _TOKEN_PATTERN.findall(cleaned)]
    return [tok for tok in tokens if tok]


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Menghapus stopword Bahasa Indonesia secara selektif (pertahankan negasi/angka/kode penting)."""
    if not tokens:
        return []

    filtered: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if low in _PROTECTED_TERMS or is_protected_code(low):
            filtered.append(low)
            continue
        if low in _INDONESIAN_STOPWORDS:
            continue
        filtered.append(low)
    return filtered


def stem_text(tokens: list[str]) -> str:
    """Melakukan stemming Bahasa Indonesia (Sastrawi) untuk keperluan indexing/retrieval.

    Catatan: Simpan hasil stemming di field `stemmed_text` dan tetap pertahankan `text` asli
    agar Answer Extraction tidak menghasilkan potongan kata yang rusak.
    """
    if not tokens:
        return ""

    stemmed_tokens: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if (
            is_protected_code(low)
            or any(ch.isdigit() for ch in low)
            or low in _NON_STEM_ACRONYMS
            or len(low) <= 2
        ):
            stemmed_tokens.append(low)
        else:
            stemmed_tokens.append(_stem_word(low))
    return " ".join(stemmed_tokens).strip()


def preprocess_for_indexing(raw_text: str) -> tuple[str, list[str], str]:
    """Menjalankan pipeline lengkap: clean -> tokenize -> selective stopwords -> stem.

    Returns:
        Tuple `(cleaned_text, filtered_tokens, stemmed_text)` sehingga `cleaned_text` tetap utuh
        untuk pembacaan/ekstraksi jawaban sedangkan `tokens` & `stemmed_text` siap untuk IR.
    """
    cleaned = clean_text(raw_text)
    tokens = tokenize_text(cleaned)
    filtered = remove_stopwords(tokens)
    stemmed = stem_text(filtered)
    return cleaned, filtered, stemmed
