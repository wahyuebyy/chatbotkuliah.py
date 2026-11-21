"""
alat.py  -  "Alat" akademik yang menjawab LANGSUNG dari data terstruktur & hitungan kode (tanpa LLM).

Pertanyaan yang dikenali (dicek berurutan, yang pertama cocok menang):
    1. Kalkulator target IPK   "IPK sekarang 3.40 dari 80 SKS, ambil 20 SKS, target IPK 3.50"
    2. Simulasi rencana studi  "cek sks: Algoritma, Basis Data, Sistem Operasi [| lulus: ...]"
    3. Draf surat/email/WA     "buatkan email izin tidak masuk kuliah"
    4. Hitung mundur kalender  "berapa hari lagi UAS?"  "batas revisi KRS tinggal berapa hari"
    5. Ruangan kosong          "ruangan kosong hari Selasa jam 10.00"
    6. Jadwal dosen            "jadwal mengajar Pak Budi"

Semua angka dihitung di kode sehingga tidak ada risiko halusinasi. Jawaban alat bermode "alat".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .config import MAKS_SKS_SEMESTER
from .data_akademik import GELAR, HARI, DataAkademik, token_nama
from .surat import buat_draf


@dataclass
class HasilAlat:
    teks: str
    alasan: str
    sumber: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Utilitas
# --------------------------------------------------------------------------- #
def _angka(teks: str) -> float:
    return float(teks.replace(",", "."))


def _f2(x: float) -> str:
    return f"{x:.2f}"


def _menit_ke_jam(m: int) -> str:
    return f"{m // 60:02d}.{m % 60:02d}"


def _hari_dari(q: str, sekarang: datetime) -> tuple[str, str]:
    """(nama hari, keterangan) dari 'hari ini/besok/lusa' atau nama hari; default hari ini."""
    t = q.lower()
    rel = re.search(r"\b(hari ini|besok|lusa)\b", t)
    if rel:
        geser = {"hari ini": 0, "besok": 1, "lusa": 2}[rel.group(1)]
        return HARI[(sekarang.weekday() + geser) % 7], rel.group(1)
    h = re.search(r"\b(senin|selasa|rabu|kamis|jumat|jum'at|sabtu|minggu)\b", t)
    if h:
        return h.group(1).capitalize().replace("Jum'at", "Jumat"), ""
    return HARI[sekarang.weekday()], "hari ini"


# --------------------------------------------------------------------------- #
# 1. Kalkulator target IPK
# --------------------------------------------------------------------------- #
_NUM = r"(\d(?:[.,]\d+)?)"
_TARGET = [
    re.compile(rf"target\s*(?:ipk)?\s*(?:saya|akhir)?\s*[:=]?\s*(?:adalah|sebesar)?\s*{_NUM}"),
    re.compile(rf"ipk\s*target\s*[:=]?\s*{_NUM}"),
    re.compile(rf"(?:ingin|mau|agar|supaya|pengen|biar)\s*(?:ipk\s*)?(?:saya\s*)?"
               rf"(?:jadi|naik\s*(?:ke|jadi)|mencapai|menjadi)\s*{_NUM}"),
]
_IPK_SEKARANG = re.compile(
    rf"ipk(?:\s+(?:saya|sekarang|saat ini|kini|kumulatif|ku|adalah|sebesar|awal))*\s*[:=]?\s*{_NUM}")


def hitung_target_ipk(q: str) -> Optional[str]:
    """Teks hasil bila `q` meminta perhitungan target IPK; None bila bukan."""
    t = q.lower()
    if not re.search(r"\bipk\b", t):
        return None
    m_t = next((m for m in (p.search(t) for p in _TARGET) if m), None)
    if not m_t and "target" not in t:
        return None
    contoh = ("Format: \"IPK sekarang 3.40 dari 80 SKS, ambil 20 SKS, target IPK 3.50\" "
              "(IPK saat ini, SKS yang sudah ditempuh, SKS yang akan diambil semester ini, dan target IPK).")
    if not m_t:
        return "Saya butuh angka target IPK-nya. " + contoh
    target = _angka(m_t.group(1))
    sisa = t[:m_t.start()] + " " + t[m_t.end():]
    m_i = _IPK_SEKARANG.search(sisa)
    sks = []
    batas_depan = 0
    for m in re.finditer(r"(\d{1,3})\s*sks", sisa):
        # konteks hanya sejak angka SKS sebelumnya (supaya "dari" milik 80 SKS tak ikut terbaca untuk 20 SKS)
        depan = sisa[max(batas_depan, m.start() - 22):m.start()]
        belakang = re.split(r"\d{1,3}\s*sks", sisa[m.end():m.end() + 22])[0]
        batas_depan = m.end()
        baru = bool(re.search(r"(ambil|mengambil|semester ini|rencana|akan|ke depan|depan|nambah)", depan))
        lalu = bool(re.search(r"(dari|sudah|telah|total|kumulatif)", depan)
                    or re.search(r"(ditempuh|lulus|selesai|sebelumnya|lalu)", belakang))
        sks.append((int(m.group(1)), "baru" if baru and not lalu else "lalu" if lalu else "?"))
    if not m_i or len(sks) < 2:
        return "Data belum lengkap. " + contoh
    lalu_n = next((n for n, j in sks if j == "lalu"), None)
    baru_n = next((n for n, j in sks if j == "baru"), None)
    sisa_sks = [n for n, j in sks if j == "?"]
    if lalu_n is None and sisa_sks:
        lalu_n = sisa_sks.pop(0)
    if baru_n is None and sisa_sks:
        baru_n = sisa_sks.pop(0)
    if lalu_n is None or baru_n is None:
        return "Saya tidak bisa membedakan SKS yang sudah ditempuh dan yang akan diambil. " + contoh
    ipk = _angka(m_i.group(1))
    if not (0 <= ipk <= 4 and 0 <= target <= 4) or lalu_n <= 0 or baru_n <= 0:
        return "Nilai tidak valid: IPK harus 0-4, SKS harus lebih dari 0. " + contoh

    total = lalu_n + baru_n
    ips_min = (target * total - ipk * lalu_n) / baru_n
    maks = (ipk * lalu_n + 4.0 * baru_n) / total
    mins = (ipk * lalu_n) / total
    kepala = (f"Kalkulator target IPK:\n- IPK sekarang {_f2(ipk)} dari {lalu_n} SKS\n"
              f"- SKS semester ini {baru_n} (total {total} SKS)\n- Target IPK {_f2(target)}\n")
    if ips_min > 4.0 + 1e-9:
        return (kepala + f"\n⚠ Target belum bisa dicapai semester ini: IPS yang dibutuhkan {_f2(ips_min)} "
                f"melebihi 4.00. IPK tertinggi yang mungkin dengan {baru_n} SKS adalah {_f2(maks)}. "
                "Target bisa dicapai bertahap lewat beberapa semester.")
    if ips_min <= 0:
        return (kepala + f"\n✅ Target sudah aman: IPK tidak akan turun di bawah {_f2(mins)} "
                "meskipun IPS semester ini rendah.")
    return (kepala + f"\n✅ IPS minimal semester ini: {_f2(ips_min)}\n"
            f"(Rumus: (target × total SKS − IPK × SKS lalu) ÷ SKS baru. IPK tertinggi yang mungkin: {_f2(maks)}.)")


# --------------------------------------------------------------------------- #
# 2. Simulasi rencana studi (cek SKS & prasyarat)
# --------------------------------------------------------------------------- #
_CEK_SKS = re.compile(r"\b(?:cek|hitung|simulasi|periksa)\s+(?:total\s+)?(?:sks|krs|rencana studi|rencana)\b\s*[:\-]?\s*(.*)$",
                      re.I)
_LULUS = re.compile(r"\b(?:sudah lulus|telah lulus|lulus)\b\s*[:\-]?|\|", re.I)


def _pecah_daftar(teks: str, data: DataAkademik) -> list[str]:
    teks = teks.strip(" .;,")
    if not teks:
        return []
    bagian = [b.strip() for b in re.split(r"[,;+&\n]", teks) if b.strip()]
    hasil: list[str] = []
    for b in bagian:                      # "dan" bisa pemisah ATAU bagian nama ("Organisasi dan Arsitektur Komputer")
        pecah = re.split(r"\s+dan\s+", b, flags=re.I)
        i = 0
        while i < len(pecah):
            for j in range(len(pecah), i, -1):
                gabung = " dan ".join(pecah[i:j])
                m, _ = data.cari_matkul(gabung)
                if m or j == i + 1:
                    hasil.append(gabung)
                    i = j
                    break
    return hasil


def simulasi_rencana(q: str, data: DataAkademik) -> Optional[str]:
    m = _CEK_SKS.search(q)
    if not m:
        return None
    sisa = m.group(1)
    bagian = _LULUS.split(sisa, maxsplit=1)
    daftar = _pecah_daftar(bagian[0], data)
    lulus = _pecah_daftar(bagian[1], data) if len(bagian) > 1 else []
    if not daftar:
        return ("Tuliskan mata kuliahnya, dipisah koma. Contoh: \"cek sks: Algoritma Pemrograman, "
                "Struktur Data, Sistem Operasi\". Tambahkan \"| lulus: Algoritma Pemrograman\" bila sebagian "
                "prasyarat sudah Anda lulus.")
    h = data.cek_rencana(daftar, lulus)
    baris = [f"Simulasi rencana studi ({len(h.dipilih)} mata kuliah):"]
    for mk in h.dipilih:
        baris.append(f"- {mk.kode} {mk.nama}: {mk.sks} SKS (semester {mk.semester}"
                     + (", pilihan" if mk.jenis == "pilihan" else "") + ")")
    batas = MAKS_SKS_SEMESTER
    baris.append(f"\nTotal: {h.total_sks} SKS (batas maksimal {batas} SKS)")
    if h.total_sks > batas:
        baris.append(f"⚠ MELEBIHI batas maksimal {batas} SKS (kelebihan {h.total_sks - batas} SKS). "
                     "Kurangi mata kuliah atau konsultasikan ke Dosen PA.")
    else:
        baris.append(f"✅ Masih dalam batas (sisa {batas - h.total_sks} SKS). "
                     "Batas sebenarnya bergantung pada IPS semester sebelumnya.")
    if not data.ada_prasyarat:
        baris.append("\nPrasyarat: data prasyarat belum tersedia di kurikulum.json.")
    elif h.dipilih:
        baris.append("\nPrasyarat" + (" (DATA CONTOH, belum resmi)" if data.prasyarat_dummy else "") + ":")
        masalah = False
        for mk, pm in h.prasyarat_bersamaan:
            baris.append(f"⚠ {mk.nama} mensyaratkan {pm.nama}, tetapi keduanya ada di rencana yang sama. "
                         f"{pm.nama} harus lulus lebih dulu.")
            masalah = True
        for mk, pm in h.prasyarat_kurang:
            baris.append(f"⚠ {mk.nama} mensyaratkan {pm.nama}: belum tercantum lulus, pastikan sudah lulus.")
            masalah = True
        if not masalah:
            baris.append("✅ Tidak ada prasyarat yang terlanggar.")
    for kata, daftar_mk in h.ambigu.items():
        baris.append(f"\n❓ \"{kata}\" cocok dengan beberapa mata kuliah: "
                     + "; ".join(x.nama for x in daftar_mk[:5]) + ". Tulis nama yang lebih lengkap.")
    if h.tidak_ditemukan:
        baris.append("\n❓ Tidak dikenali: " + ", ".join(f"\"{x}\"" for x in h.tidak_ditemukan)
                     + " (periksa penulisan nama mata kuliah).")
    return "\n".join(baris)


# --------------------------------------------------------------------------- #
# 3. Hitung mundur kalender
# --------------------------------------------------------------------------- #
KALENDER_RE = re.compile(
    r"\b(hitung mundur|berapa hari lagi|tinggal berapa hari|sisa waktu|sisa hari|countdown|tenggat|deadline)\b"
    r"|\bkapan\s+(?:batas|awal|mulai|dimulai|uts|uas|pengisian|krs|skripsi|revisi|ujian)\b"
    r"|\b(?:batas|tenggat)\b.*\b(?:krs|skripsi|revisi|pengisian|pengajuan)\b"
    r"|\bminggu\s+(?:uts|uas)\b", re.I)


# --------------------------------------------------------------------------- #
# 4. Ruangan kosong
# --------------------------------------------------------------------------- #
RUANG_RE = re.compile(r"\b(ruang|ruangan|lab|laboratorium)\b", re.I)
KOSONG_RE = re.compile(r"\b(kosong|tidak terpakai|tidak dipakai|menganggur|free)\b", re.I)
_RENTANG_JAM = re.compile(r"(\d{1,2})[.:](\d{2})\s*(?:-|–|s\.?d\.?|sampai|hingga)\s*(\d{1,2})[.:](\d{2})")
_JAM_TUNGGAL = re.compile(r"(?:\b(?:jam|pukul|pkl)\.?\s*(\d{1,2})(?:[.:](\d{2}))?\b)|(?:\b(\d{1,2})[.:](\d{2})\b)")


def _ambil_jam(q: str) -> Optional[tuple[int, int]]:
    """(mulai, selesai) dalam menit dari teks; jam tunggal -> rentang 1 menit. None bila tak ada."""
    m = _RENTANG_JAM.search(q)
    if m:
        a, b = int(m.group(1)) * 60 + int(m.group(2)), int(m.group(3)) * 60 + int(m.group(4))
        return (a, b) if b > a else None
    m = _JAM_TUNGGAL.search(q)
    if not m:
        return None
    jam = int(m.group(1) or m.group(3))
    mnt = int(m.group(2) or m.group(4) or 0)
    if jam > 23 or mnt > 59:
        return None
    return jam * 60 + mnt, jam * 60 + mnt + 1


def ruang_kosong(q: str, data: DataAkademik, sekarang: datetime) -> Optional[str]:
    if not (RUANG_RE.search(q) and KOSONG_RE.search(q)) or not data.jadwal:
        return None
    hari, rel = _hari_dari(q, sekarang)
    jam = _ambil_jam(q)
    sekarang_menit = sekarang.hour * 60 + sekarang.minute
    if jam is None:
        jam = (sekarang_menit, sekarang_menit + 1)
        waktu = f"sekarang ({_menit_ke_jam(sekarang_menit)} WIB)"
    elif jam[1] - jam[0] == 1:
        waktu = f"pukul {_menit_ke_jam(jam[0])}"
    else:
        waktu = f"pukul {_menit_ke_jam(jam[0])}-{_menit_ke_jam(jam[1])}"
    label_hari = f"hari {hari}" + (f" ({rel})" if rel else "")
    if hari in ("Sabtu", "Minggu"):
        return f"Tidak ada jadwal kuliah di data pada hari {hari}, sehingga semua ruangan kosong."
    kosong, terpakai = data.ruang_status(hari, *jam)
    t = q.lower()
    hanya_lab = bool(re.search(r"\b(lab|laboratorium)\b", t))
    hanya_kelas = bool(re.search(r"\b(ruang kelas|ruangan kelas|kelas)\b", t)) and not hanya_lab
    if hanya_lab:
        kosong = [r for r in kosong if r.lower().startswith("lab")]
        terpakai = [s for s in terpakai if s.ruang.lower().startswith("lab")]
    elif hanya_kelas:
        kosong = [r for r in kosong if not r.lower().startswith("lab")]
        terpakai = [s for s in terpakai if not s.ruang.lower().startswith("lab")]
    baris = [f"Ruangan {'laboratorium ' if hanya_lab else ''}kosong {label_hari}, {waktu}:"]
    baris.append(", ".join(kosong) if kosong else "(tidak ada ruangan kosong)")
    if terpakai:
        baris.append("\nSedang dipakai:")
        for s in terpakai:
            baris.append(f"- {s.ruang}: {data.matkul[s.kode].nama} {s.mulai}-{s.selesai} ({s.dosen})")
    baris.append("\nDaftar ruangan diambil dari jadwal.csv (ruangan yang tidak pernah dijadwalkan tidak ikut terdata)"
                 + (" - DATA CONTOH." if data.dummy else "."))
    return "\n".join(baris)


# --------------------------------------------------------------------------- #
# 5. Jadwal dosen
# --------------------------------------------------------------------------- #
JADWAL_KATA = re.compile(r"\b(jadwal|mengajar|ngajar|mengampu|kapan)\b", re.I)
GELAR_RE = re.compile(r"\b(pak|bu|bapak|ibu|prof|dr|drs|dra)\b\.?", re.I)
_STOP = {"jadwal", "mengajar", "ngajar", "mengampu", "kapan", "hari", "apa", "saja", "yang", "di", "ke", "pada",
         "dosen", "tolong", "cek", "cari", "lihat", "minggu", "ini", "dong", "ya", "kah", "nya", "itu", "adalah",
         "mulai", "jam", "pukul", "dan", "atau", "berapa", "saya", "kuliah", "kelas", "dengan", "untuk", "the"}


def jadwal_dosen(q: str, data: DataAkademik) -> Optional[str]:
    if not JADWAL_KATA.search(q) or not data.jadwal or data.matkul_cocok(q):
        return None
    t = q.lower().replace("?", " ")
    toks = re.findall(r"[a-z0-9]+", t)
    g = GELAR_RE.search(t)
    if g:                                                   # mode gelar: "pak budi"
        sesudah = re.findall(r"[a-z0-9]+", t[g.end():])
        calon = [x for x in sesudah if x not in _STOP and x not in GELAR]
        label = " ".join(calon).title()
        if not calon:
            return "Sebutkan nama dosennya, mis. \"jadwal mengajar Pak Budi\"."
        cocok = data.cari_dosen(calon)
    else:                                                   # mode nama lengkap yang ada di jadwal
        cocok = []
        label = ""
        for nama in data.daftar_dosen():
            nt = token_nama(nama)
            if nt and (len(nt) >= 2 or len(nt[0]) >= 4) and all(x in toks for x in nt):
                cocok.append(nama)
        if not cocok:
            return None
    if not cocok:
        contoh = ", ".join(data.daftar_dosen()[:8])
        return (f"Dosen dengan nama \"{label}\" tidak ditemukan di jadwal.csv. "
                f"Dosen yang tercatat, mis.: {contoh}"
                + (" ..." if len(data.daftar_dosen()) > 8 else "") + ". Coba tulis nama sesuai data.")
    if len(cocok) > 5:
        return (f"Ada {len(cocok)} dosen yang cocok dengan \"{label}\" (mis. {', '.join(cocok[:5])}). "
                "Sebutkan nama yang lebih lengkap.")
    blok = []
    for nama in cocok:
        baris = [f"Jadwal mengajar {nama}" + (" (DATA CONTOH)" if data.dummy else "") + ":"]
        hari_sebelum = ""
        for s in data.sesi_dosen(nama):
            if s.hari != hari_sebelum:
                baris.append(f"{s.hari}:")
                hari_sebelum = s.hari
            mk = data.matkul[s.kode]
            baris.append(f"- {s.mulai}-{s.selesai} {mk.nama} (semester {mk.semester}, kelas {s.kelas}, "
                         f"{s.ruang}, {s.jenis})")
        blok.append("\n".join(baris))
    return "\n\n".join(blok)


# --------------------------------------------------------------------------- #
# Pintu masuk
# --------------------------------------------------------------------------- #
class AlatAkademik:
    def __init__(self, data: Optional[DataAkademik]):
        self.data = data

    def coba(self, q: str, sekarang: datetime) -> Optional[HasilAlat]:
        """HasilAlat bila `q` dijawab oleh salah satu alat; None -> lanjut ke KB/LLM."""
        d = self.data
        teks = hitung_target_ipk(q)
        if teks:
            return HasilAlat(teks, "alat:ipk")
        if d is None:
            return None
        teks = simulasi_rencana(q, d)
        if teks:
            return HasilAlat(teks, "alat:cek_sks", ["kurikulum.json"])
        mk = d.matkul_cocok(q)
        teks = buat_draf(q, mk[0].nama if mk else None)
        if teks:
            return HasilAlat(teks, "alat:surat")
        if d.kalender and KALENDER_RE.search(q):
            return HasilAlat(d.kalender.jawab(q, sekarang), "alat:kalender", [d.kalender.sumber()])
        teks = ruang_kosong(q, d, sekarang)
        if teks:
            return HasilAlat(teks, "alat:ruang_kosong", [d._sumber_jadwal()])
        teks = jadwal_dosen(q, d)
        if teks:
            return HasilAlat(teks, "alat:jadwal_dosen", [d._sumber_jadwal()])
        return None
