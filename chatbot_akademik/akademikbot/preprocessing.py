"""
preprocessing.py  -  Pembersihan teks bahasa Indonesia untuk TF-IDF.

PENANGGUNG JAWAB: Anggota 2 (NLP & TF-IDF)

Tahapan: lowercase -> normalisasi singkatan chat -> buang tanda baca ->
         buang stopword -> stemming ringan (berbantuan kamus kata dasar domain).
"""

from __future__ import annotations

import re

STOPWORDS = frozenset("""
yang dan di ke dari untuk pada dengan atau ini itu adalah ada akan juga saya aku kami kita
anda kamu dia mereka sudah belum bisa dapat boleh harus perlu agar supaya karena jika kalau
bila maka sebagai oleh dalam antara tentang apa apakah bagaimana berapa kapan siapa mengapa
kenapa dimana mana tolong mohon dong sih deh ya nih lah kah nya para sebuah suatu saat
lagi masih sangat paling lebih hanya saja pun serta bahwa tapi tetapi namun yaitu yakni
cara gimana gmn bagaimanakah minta tanya mau ingin terus bandingkan banding dibandingkan
beda bedanya perbedaan keduanya kedua tersebut punya memiliki
halo hai hi hello assalamualaikum selamat pagi siang sore malam min admin kak pak bu bapak ibu
""".split())

# Singkatan / bahasa chat yang umum dipakai mahasiswa -> bentuk baku.
SINGKATAN = {
    "gmn": "bagaimana", "gimana": "bagaimana", "bgmn": "bagaimana",
    "brp": "berapa", "kpn": "kapan", "dmn": "dimana",
    "yg": "yang", "utk": "untuk", "dgn": "dengan", "krn": "karena", "karna": "karena",
    "tdk": "tidak", "gak": "tidak", "ga": "tidak", "nggak": "tidak", "ngga": "tidak",
    "sy": "saya", "bs": "bisa", "sdh": "sudah", "blm": "belum", "jd": "jadi",
    "dsn": "dosen", "mhs": "mahasiswa", "mk": "mata kuliah", "sem": "semester",
    "ta": "tugas akhir", "kp": "kerja praktik", "kkp": "kerja praktik",
    "sks": "sks", "ipk": "ipk", "ips": "ips",
}

# Kata dasar yang sering muncul di domain akademik. Dipakai agar stemmer tidak
# "kebablasan" (mis. 'nilai' jangan jadi 'nila', 'pengajuan' harus jadi 'aju').
KAMUS_DASAR = frozenset("""
isi nilai kuliah ujian uji susul aju daftar bimbing ambil hitung urus hadir batal ubah
ganti tunda lulus tempuh sidang jadwal bayar cuti aktif legalisir syarat skripsi beasiswa
semester mahasiswa dosen akademik registrasi kontak hubung tugas akhir wajib tetap
laksana ikut sakit studi ulang perbaikan perbaiki praktik magang wisuda yudisium kalender
tunjuk tetapkan tetap lengkap lampir surat keterangan mohon proposal judul pustaka
prodi sekretariat fakultas universitas informatika kampus sistem informasi ipk ips sks krs uts uas pa
setuju hubungi hubung ruang
""".split()) | frozenset(f"semester{i}" for i in range(1, 9))

# Sinonim / padanan kata -> kata kunci yang dipakai KB (diterapkan setelah SINGKATAN).
SINONIM = {
    "perpanjangan": "batas", "perpanjang": "batas", "diperpanjang": "batas",
    "libur": "cuti", "berhenti": "cuti",
    "absen": "tidak hadir", "berhalangan": "tidak hadir",
    "transkrip": "nilai", "indeks": "nilai",
    "do": "drop out",
}

_PREFIX = ("meng", "meny", "mem", "men", "me", "peng", "peny", "pem", "pen", "per",
           "ber", "ter", "di", "ke", "se", "pe")
_SUFFIX = ("kanlah", "kan", "nya", "lah", "kah", "an", "i")

_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
# "semester 3", "sem 3", "smt ke-3" -> "semester semester3": angka satu digit dibuang tokenizer,
# jadi nomor semester dijadikan SATU token agar bisa membedakan entri jadwal/kurikulum per semester.
_SEMESTER_N = re.compile(r"\b(?:semester|sem|smt)\s*(?:ke[-\s]?)?([1-8])\b")


def _kandidat(kata: str):
    """Hasilkan kemungkinan kata dasar (buang sufiks dan/atau prefiks)."""
    sufiks = [""] + [s for s in _SUFFIX if kata.endswith(s)]
    for s in sufiks:
        b = kata[: -len(s)] if s else kata
        yield b
        for p in _PREFIX:
            if b.startswith(p):
                sisa = b[len(p):]
                yield sisa
                # peluluhan konsonan: meny+sulit -> sulit, mem+ukul -> pukul, dst.
                if p in ("meny", "peny"):
                    yield "s" + sisa
                elif p in ("mem", "pem"):
                    yield "p" + sisa
                elif p in ("men", "pen"):
                    yield "t" + sisa
                elif p in ("meng", "peng"):
                    yield "k" + sisa


def stem(kata: str) -> str:
    """Stemmer ringan: utamakan hasil yang ada di KAMUS_DASAR, jika tidak ada pakai heuristik."""
    if kata in KAMUS_DASAR:
        return kata
    for c in _kandidat(kata):
        if len(c) >= 2 and c in KAMUS_DASAR:
            return c
    if len(kata) <= 4:
        return kata
    # Heuristik cadangan untuk kata di luar kamus.
    for s in _SUFFIX:
        if kata.endswith(s) and len(kata) - len(s) >= 4:
            kata = kata[: -len(s)]
            break
    for p in _PREFIX:
        if kata.startswith(p) and len(kata) - len(p) >= 4:
            kata = kata[len(p):]
            break
    return kata


def normalisasi(teks: str) -> str:
    """Lowercase, ganti singkatan chat, buang tanda baca."""
    teks = _SEMESTER_N.sub(lambda m: f"semester semester{m.group(1)}", teks.lower())
    teks = _NON_ALNUM.sub(" ", teks)
    return " ".join(SINONIM.get(SINGKATAN.get(t, t), SINGKATAN.get(t, t)) for t in teks.split())


def tokenize(teks: str) -> list[str]:
    """Teks -> daftar token bersih (tanpa stopword, sudah di-stem)."""
    return [stem(t) for t in normalisasi(teks).split() if t not in STOPWORDS and len(t) > 1]
