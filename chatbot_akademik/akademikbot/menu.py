"""
menu.py  -  Menu TABEL PILIHAN bertingkat (tanpa mengetik) untuk CLI dan web.

PENANGGUNG JAWAB: Anggota 4 (Router, CLI & Evaluasi)

Pengguna cukup memilih nomor: Jadwal / Mata kuliah / Cari mata kuliah / FAQ / Atur semester.
Setiap pilihan akhir menunjuk satu entri KB (mis. 'jadwal-s3-senin'), jadi jawabannya melewati
sumber yang sama dengan jawaban chat (terverifikasi, bersumber) dan masuk ke riwayat sesi sehingga
pertanyaan lanjutan yang diketik ("kalau dosennya siapa?") tetap nyambung.

Navigasi tanpa status (stateless): posisi menu = daftar kunci ("jalur"), mis. ["jadwal", "3", "senin"].
Itu memudahkan API web: klien cukup mengirim jalur yang dipilih.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .data_akademik import HARI_KULIAH, DataAkademik
from .kb_loader import Entri


# --------------------------------------------------------------------------- #
# Pilihan cepat (Quick Reply) -- dipakai bersama oleh CLI (cli.py) dan web (web.py)
# --------------------------------------------------------------------------- #
# Kata kunci di pertanyaan pengguna -> 3 pertanyaan lanjutan. Setiap pertanyaan SENGAJA dibuat
# sama dengan pertanyaan di knowledge_base.json / info_umum.json supaya jawabannya terverifikasi.
# Ubah daftar ini bila KB berubah (tes tests/test_saran_cepat.py memastikan tidak ada opsi mati).
SARAN_CEPAT: dict[str, list[str]] = {
    "jadwal": [
        "Jadwal kuliah semester 3",
        "Jam kuliah dimulai dan selesai pukul berapa?",
        "Bagaimana jika jadwal kuliah berubah atau dosen berhalangan hadir?",
    ],
    "krs": [
        "Berapa maksimal SKS yang boleh diambil per semester?",
        "Siapa dosen pembimbing akademik saya dan apa tugasnya?",
        "Di mana saya bisa melihat kalender akademik dan jadwal UTS/UAS?",
    ],
    "skripsi": [
        "Berapa kali bimbingan skripsi yang harus dilakukan?",
        "Berapa batas kemiripan (plagiarisme) yang diizinkan pada skripsi?",
        "Bagaimana prosedur sidang, yudisium, dan wisuda?",
    ],
    "cuti": [
        "Berapa lama batas maksimal masa studi?",
        "Bagaimana cara meminta surat keterangan aktif kuliah atau legalisir?",
        "Bagaimana cara mengisi KRS?",
    ],
    "ujian": [
        "Berapa batas minimal kehadiran agar boleh mengikuti UAS?",
        "Bagaimana cara mengajukan sanggahan atau komplain nilai?",
        "Bagaimana jika nilai saya D atau E, apakah bisa mengulang mata kuliah?",
    ],
    "uts": [
        "Di mana saya bisa melihat kalender akademik dan jadwal UTS/UAS?",
        "Apa yang harus dilakukan jika tidak bisa mengikuti ujian?",
        "Berapa batas minimal kehadiran agar boleh mengikuti UAS?",
    ],
    "uas": [
        "Berapa batas minimal kehadiran agar boleh mengikuti UAS?",
        "Bagaimana cara menghitung IPK dan IPS?",
        "Bagaimana cara mengajukan sanggahan atau komplain nilai?",
    ],
}
MAKS_SARAN_CEPAT = 3
_NOMOR_SARAN = re.compile(r"^\s*([1-9])\s*[.)]?\s*$")


def _normal(teks: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", teks.lower()).split())


def saran_cepat(pertanyaan: str, maks: int = MAKS_SARAN_CEPAT) -> list[str]:
    """Pertanyaan lanjutan (maks. 3) untuk kata kunci yang ditemukan di `pertanyaan`.

    Kata kunci dicocokkan sebagai kata utuh (mis. 'uas' tidak cocok dengan 'luas'). Pertanyaan yang
    sama dengan yang baru ditanyakan dibuang supaya tidak menyarankan hal yang sama.
    """
    q = _normal(pertanyaan)
    if not q:
        return []
    kata = set(q.split())
    hasil: list[str] = []
    for kunci, daftar in SARAN_CEPAT.items():
        if kunci not in kata:
            continue
        for s in daftar:
            if _normal(s) != q and s not in hasil:
                hasil.append(s)
    return hasil[:maks]


def pilih_saran(teks: str, opsi: list[str]) -> Optional[str]:
    """Bila `teks` hanya berupa angka ('1', '2.', '3)') yang menunjuk salah satu `opsi`,
    kembalikan pertanyaan lengkapnya; selain itu None (diperlakukan sebagai pertanyaan biasa)."""
    m = _NOMOR_SARAN.match(teks or "")
    if not m or not opsi:
        return None
    n = int(m.group(1))
    return opsi[n - 1] if 1 <= n <= len(opsi) else None


@dataclass
class Opsi:
    no: int
    label: str
    jalur: list[str]
    ket: str = ""


@dataclass
class Layar:
    judul: str
    jalur: list[str]
    opsi: list[Opsi] = field(default_factory=list)
    kolom: tuple[str, str, str] = ("No", "Pilihan", "Keterangan")
    petunjuk: str = "Ketik nomor pilihan. 0 = kembali. Atau langsung ketik pertanyaan Anda."


@dataclass
class HasilMenu:
    layar: Optional[Layar] = None          # menu yang harus ditampilkan
    entri_id: Optional[str] = None         # bila pilihan akhir = jawaban dari entri KB ini
    balik: list[str] = field(default_factory=list)   # menu yang ditampilkan lagi setelah jawaban
    atur_semester: Optional[int] = None    # bila pilihan akhir = mengatur semester pengguna
    pesan: str = ""


class MenuAkademik:
    def __init__(self, data: Optional[DataAkademik], entri_faq: list[Entri]):
        self.data = data
        self.faq = entri_faq
        kat: list[str] = []
        for e in entri_faq:
            if e.kategori not in kat:
                kat.append(e.kategori)
        self.kategori = kat

    # -- API ------------------------------------------------------------------ #
    def buka(self, jalur: Optional[list[str]] = None) -> HasilMenu:
        """Terjemahkan jalur menu menjadi layar berikutnya atau jawaban akhir.
        Jalur yang tidak dikenal dikembalikan ke menu utama (aman untuk input web)."""
        jalur = [str(x) for x in (jalur or [])][:4]
        try:
            return self._buka(jalur)
        except (KeyError, ValueError, IndexError):
            return HasilMenu(layar=self._utama())

    # -- layar ---------------------------------------------------------------- #
    def _utama(self) -> Layar:
        o = [Opsi(1, "Jadwal kuliah", ["jadwal"], "per semester & hari"),
             Opsi(2, "Mata kuliah per semester", ["kurikulum"], "daftar & total SKS"),
             Opsi(3, "Cari mata kuliah", ["matkul"], "SKS, dosen, ruang, jadwal"),
             Opsi(4, "Info & layanan akademik", ["faq"], "KRS, cuti, skripsi, dll."),
             Opsi(5, "Atur semester saya", ["semester"], "agar 'jadwal hari ini' langsung dipahami")]
        if not self.data:
            o = [Opsi(1, "Info & layanan akademik", ["faq"], "KRS, cuti, skripsi, dll.")]
        return Layar("MENU UTAMA", [], o)

    def _buka(self, j: list[str]) -> HasilMenu:
        if not j:
            return HasilMenu(layar=self._utama())
        d = self.data
        if j[0] == "faq":
            return self._faq(j)
        if d is None:
            raise KeyError(j[0])
        if j[0] == "jadwal":
            return self._jadwal(j, d)
        if j[0] == "kurikulum":
            return self._kurikulum(j, d)
        if j[0] == "matkul":
            return self._matkul(j, d)
        if j[0] == "semester":
            return self._semester(j, d)
        raise KeyError(j[0])

    def _pilih_semester(self, nama: str, judul: str, semuanya: list[int], d: DataAkademik) -> Layar:
        o = []
        for i, n in enumerate(semuanya, 1):
            mk = d.matkul_semester(n)
            ket = f"{len(mk)} mata kuliah, {sum(m.sks for m in mk if m.jenis == 'wajib')} SKS wajib"
            o.append(Opsi(i, f"Semester {n}", [nama, str(n)], ket))
        return Layar(judul, [nama], o)

    def _jadwal(self, j: list[str], d: DataAkademik) -> HasilMenu:
        if len(j) == 1:
            ada = d.semester_berjadwal()
            if not ada:
                return HasilMenu(layar=self._utama(), pesan="Data jadwal belum diisi (data/jadwal.csv).")
            lay = self._pilih_semester("jadwal", "JADWAL KULIAH - pilih semester", ada, d)
            for o in lay.opsi:
                n = int(o.jalur[1])
                o.ket = f"{len(d.sesi_semester(n))} pertemuan per minggu"
            return HasilMenu(layar=lay)
        n = int(j[1])
        if n not in d.semester_berjadwal():
            raise KeyError(n)
        if len(j) == 2:
            o = [Opsi(1, "Semua hari", ["jadwal", str(n), "semua"], f"{len(d.sesi_semester(n))} pertemuan")]
            for i, h in enumerate(HARI_KULIAH, 2):
                o.append(Opsi(i, h, ["jadwal", str(n), h.lower()], f"{len(d.sesi_semester(n, h))} pertemuan"))
            return HasilMenu(layar=Layar(f"JADWAL SEMESTER {n} - pilih hari", j[:2], o))
        hari = j[2]
        if hari == "semua":
            return HasilMenu(entri_id=f"jadwal-s{n}", balik=j[:2])
        if hari not in {h.lower() for h in HARI_KULIAH}:
            raise KeyError(hari)
        return HasilMenu(entri_id=f"jadwal-s{n}-{hari}", balik=j[:2])

    def _kurikulum(self, j: list[str], d: DataAkademik) -> HasilMenu:
        if len(j) == 1:
            return HasilMenu(layar=self._pilih_semester(
                "kurikulum", "MATA KULIAH - pilih semester", d.semester_kurikulum(), d))
        n = int(j[1])
        if n not in d.semester_kurikulum():
            raise KeyError(n)
        return HasilMenu(entri_id=f"sem-{n}", balik=j[:1])

    def _matkul(self, j: list[str], d: DataAkademik) -> HasilMenu:
        if len(j) == 1:
            return HasilMenu(layar=self._pilih_semester(
                "matkul", "CARI MATA KULIAH - pilih semester", d.semester_kurikulum(), d))
        n = int(j[1])
        if n not in d.semester_kurikulum():
            raise KeyError(n)
        if len(j) == 2:
            o = [Opsi(i, m.nama, ["matkul", str(n), m.kode],
                      f"{m.kode}, {m.sks} SKS" + (", pilihan" if m.jenis == "pilihan" else ""))
                 for i, m in enumerate(d.matkul_semester(n), 1)]
            return HasilMenu(layar=Layar(f"SEMESTER {n} - pilih mata kuliah", j[:2], o,
                                         kolom=("No", "Mata kuliah", "Kode, SKS")))
        if j[2] not in d.matkul or d.matkul[j[2]].semester != n:
            raise KeyError(j[2])
        return HasilMenu(entri_id=f"mk-{j[2]}", balik=j[:2])

    def _semester(self, j: list[str], d: DataAkademik) -> HasilMenu:
        if len(j) == 1:
            return HasilMenu(layar=self._pilih_semester(
                "semester", "SEMESTER SAYA - pilih semester Anda", d.semester_kurikulum(), d))
        n = int(j[1])
        if n not in d.semester_kurikulum():
            raise KeyError(n)
        return HasilMenu(layar=self._utama(), atur_semester=n,
                         pesan=f"Semester Anda diatur ke {n}. Sekarang Anda bisa mengetik, mis. "
                               f"'jadwal hari ini' atau 'mata kuliah saya'.")

    def _faq(self, j: list[str]) -> HasilMenu:
        if len(j) == 1:
            o = [Opsi(i, k, ["faq", str(i)], f"{sum(1 for e in self.faq if e.kategori == k)} topik")
                 for i, k in enumerate(self.kategori, 1)]
            return HasilMenu(layar=Layar("INFO AKADEMIK - pilih kategori", j, o))
        kat = self.kategori[int(j[1]) - 1]
        daftar = [e for e in self.faq if e.kategori == kat]
        if len(j) == 2:
            o = [Opsi(i, e.pertanyaan, ["faq", j[1], e.id], "") for i, e in enumerate(daftar, 1)]
            return HasilMenu(layar=Layar(f"{kat.upper()} - pilih pertanyaan", j[:2], o,
                                         kolom=("No", "Pertanyaan", "")))
        if j[2] not in {e.id for e in daftar}:
            raise KeyError(j[2])
        return HasilMenu(entri_id=j[2], balik=j[:2])


def induk(jalur: list[str]) -> list[str]:
    return jalur[:-1]
