"""
data_akademik.py  -  Data TERSTRUKTUR perkuliahan (kurikulum, jadwal) + pembangkit entri KB otomatis.

PENANGGUNG JAWAB: Anggota 1 (Data & Knowledge Base)

Sumber data (folder data/):
  kurikulum.json   daftar mata kuliah per semester (dari dokumen resmi 'Daftar Matakuliah' Kurikulum 2025)
  jadwal.csv       jadwal kuliah: kode,kelas,hari,mulai,selesai,ruang,dosen,jenis   (SAAT INI DUMMY)
  jadwal_info.json tahun ajaran + penanda dummy
  info_umum.json   FAQ perkuliahan umum (format sama dengan knowledge_base.json; DUMMY)

Mengapa dijadikan entri KB? Setiap baris jadwal/mata kuliah diubah menjadi entri KB yang jawabannya
SUDAH dihitung di kode (total SKS, daftar per hari). Jadi TF-IDF, router, LLM, guardrail, dan sitasi
[S#] bekerja persis seperti entri FAQ biasa, dan LLM tidak perlu menghitung/menebak angka.
"""

from __future__ import annotations

import csv
import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .kalender import KalenderAkademik
from .kb_loader import Entri, KBError, muat_kb

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
HARI_KULIAH = HARI[:5]
_JAM = re.compile(r"^(\d{1,2})[.:](\d{2})$")
KOLOM_JADWAL = ("kode", "kelas", "hari", "mulai", "selesai", "ruang", "dosen", "jenis")


@dataclass
class Matkul:
    kode: str
    nama: str
    sks: int
    t: int
    p: int
    l: int
    jenis: str            # wajib | pilihan
    kelompok: str
    semester: int
    prasyarat: list[str] = field(default_factory=list)   # kode mata kuliah yang harus lulus lebih dulu


@dataclass
class Sesi:
    kode: str
    kelas: str
    hari: str
    mulai: str            # "07.30"
    selesai: str
    ruang: str
    dosen: str
    jenis: str            # Teori | Praktik | Lapangan

    def menit(self) -> tuple[int, int]:
        return _menit(self.mulai), _menit(self.selesai)


# Kata gelar/sapaan yang diabaikan saat mencocokkan nama dosen.
GELAR = {"prof", "dr", "drs", "dra", "ir", "h", "hj", "pak", "bu", "bapak", "ibu", "dosen"}


def token_nama(teks: str) -> list[str]:
    """Token nama orang: huruf kecil, tanpa gelar di belakang koma ('Budi, S.Kom' -> ['budi'])."""
    inti = teks.split(",")[0].lower()
    return [t for t in re.findall(r"[a-z0-9]+", inti) if t not in GELAR]


@dataclass
class HasilRencana:
    """Hasil simulasi rencana studi (cek SKS & prasyarat)."""
    dipilih: list["Matkul"] = field(default_factory=list)
    tidak_ditemukan: list[str] = field(default_factory=list)
    ambigu: dict[str, list["Matkul"]] = field(default_factory=dict)
    lulus: list["Matkul"] = field(default_factory=list)
    prasyarat_kurang: list[tuple["Matkul", "Matkul"]] = field(default_factory=list)   # (matkul, prasyarat)
    prasyarat_bersamaan: list[tuple["Matkul", "Matkul"]] = field(default_factory=list)

    @property
    def total_sks(self) -> int:
        return sum(m.sks for m in self.dipilih)


def _menit(jam: str) -> int:
    h, m = _JAM.match(jam).groups()  # type: ignore[union-attr]
    return int(h) * 60 + int(m)


def _norm_jam(teks: str) -> str:
    m = _JAM.match(teks.strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise KBError(f"format jam salah: '{teks}' (pakai HH.MM, mis. 07.30)")
    return f"{int(m.group(1)):02d}.{m.group(2)}"


@dataclass
class DataAkademik:
    kurikulum: dict
    matkul: dict[str, Matkul] = field(default_factory=dict)
    jadwal: list[Sesi] = field(default_factory=list)
    info: dict = field(default_factory=dict)
    entri_umum: list[Entri] = field(default_factory=list)
    kalender: Optional[KalenderAkademik] = None

    # -- pemuatan ------------------------------------------------------------ #
    @classmethod
    def muat(cls, folder: Path) -> Optional["DataAkademik"]:
        """None bila folder tidak punya kurikulum.json (fitur data terstruktur dimatikan)."""
        folder = Path(folder)
        kur_path = folder / "kurikulum.json"
        if not kur_path.exists():
            return None
        try:
            kur = json.loads(kur_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise KBError(f"Format JSON rusak di {kur_path}: {exc}") from exc
        d = cls(kurikulum=kur)
        for s in kur.get("semester", []):
            for m in s.get("matkul", []):
                if m["kode"] in d.matkul:
                    raise KBError(f"Kode mata kuliah ganda di kurikulum.json: {m['kode']}")
                d.matkul[m["kode"]] = Matkul(
                    kode=m["kode"], nama=m["nama"], sks=int(m["sks"]), t=int(m.get("t", 0)),
                    p=int(m.get("p", 0)), l=int(m.get("l", 0)), jenis=m.get("jenis", "wajib"),
                    kelompok=m.get("kelompok") or "", semester=int(s["no"]),
                    prasyarat=[str(x) for x in m.get("prasyarat", [])])
        for m in d.matkul.values():
            for kp in m.prasyarat:
                if kp not in d.matkul:
                    raise KBError(f"kurikulum.json: prasyarat '{kp}' pada {m.kode} tidak ada di daftar mata kuliah")
                if kp == m.kode:
                    raise KBError(f"kurikulum.json: {m.kode} tidak boleh menjadi prasyarat dirinya sendiri")
        info = folder / "jadwal_info.json"
        d.info = json.loads(info.read_text(encoding="utf-8")) if info.exists() else {}
        csv_path = folder / "jadwal.csv"
        if csv_path.exists():
            d._muat_jadwal(csv_path)
        umum = folder / "info_umum.json"
        if umum.exists():
            d.entri_umum = muat_kb(umum)
            d.kalender = KalenderAkademik.dari_json(umum)
        return d

    def _muat_jadwal(self, path: Path) -> None:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rd = csv.DictReader(f)
            hilang = [k for k in KOLOM_JADWAL if k not in (rd.fieldnames or [])]
            if hilang:
                raise KBError(f"{path.name}: kolom wajib hilang: {', '.join(hilang)}")
            for no, r in enumerate(rd, 2):
                r = {k: (v or "").strip() for k, v in r.items() if k}
                if not any(r.values()):
                    continue
                dimana = f"{path.name} baris {no}"
                if r["kode"] not in self.matkul:
                    raise KBError(f"{dimana}: kode '{r['kode']}' tidak ada di kurikulum.json")
                hari = r["hari"].capitalize()
                if hari not in HARI:
                    raise KBError(f"{dimana}: hari '{r['hari']}' tidak valid ({', '.join(HARI)})")
                try:
                    mulai, selesai = _norm_jam(r["mulai"]), _norm_jam(r["selesai"])
                except KBError as exc:
                    raise KBError(f"{dimana}: {exc}") from exc
                if _menit(selesai) <= _menit(mulai):
                    raise KBError(f"{dimana}: jam selesai harus setelah jam mulai")
                for k in ("ruang", "dosen"):
                    if not r[k]:
                        raise KBError(f"{dimana}: kolom '{k}' wajib diisi")
                self.jadwal.append(Sesi(r["kode"], r["kelas"] or "A", hari, mulai, selesai,
                                        r["ruang"], r["dosen"], (r["jenis"] or "Teori").capitalize()))

    # -- kueri ---------------------------------------------------------------- #
    @property
    def dummy(self) -> bool:
        return bool(self.info.get("dummy", False))

    @property
    def prasyarat_dummy(self) -> bool:
        return bool(self.kurikulum.get("prasyarat_dummy", False))

    @property
    def ada_prasyarat(self) -> bool:
        return any(m.prasyarat for m in self.matkul.values())

    @property
    def tahun_ajaran(self) -> str:
        return str(self.info.get("tahun_ajaran", "")).strip()

    def semester_kurikulum(self) -> list[int]:
        return [int(s["no"]) for s in self.kurikulum["semester"]]

    def semester_berjadwal(self) -> list[int]:
        return sorted({self.matkul[s.kode].semester for s in self.jadwal})

    def matkul_semester(self, n: int) -> list[Matkul]:
        return [m for m in self.matkul.values() if m.semester == n]

    def sesi_semester(self, n: int, hari: Optional[str] = None) -> list[Sesi]:
        hasil = [s for s in self.jadwal if self.matkul[s.kode].semester == n
                 and (hari is None or s.hari == hari)]
        return sorted(hasil, key=lambda s: (HARI.index(s.hari), s.menit()[0], s.kode))

    def sesi_matkul(self, kode: str) -> list[Sesi]:
        return sorted((s for s in self.jadwal if s.kode == kode),
                      key=lambda s: (s.kelas, HARI.index(s.hari), s.menit()[0]))

    def matkul_cocok(self, teks: str) -> list[Matkul]:
        """Mata kuliah yang namanya disebut utuh di teks (mis. 'jadwal sistem operasi')."""
        t = " ".join(teks.lower().split())
        return [m for m in self.matkul.values() if m.nama.lower() in t]

    # -- dosen ------------------------------------------------------------------ #
    def daftar_dosen(self) -> list[str]:
        def kunci(n: str):
            return [int(x) if x.isdigit() else x for x in re.findall(r"\d+|\D+", n.lower())]
        return sorted({s.dosen for s in self.jadwal}, key=kunci)

    def cari_dosen(self, tokens: list[str]) -> list[str]:
        """Dosen yang SETIAP token-nya cocok dengan token namanya (angka harus persis; kata boleh awalan
        >= 3 huruf, mis. 'bud' -> 'Budi')."""
        tokens = [t for t in tokens if t]
        if not tokens:
            return []
        hasil = []
        for nama in self.daftar_dosen():
            nt = token_nama(nama)
            if all(any(n == t or (not t.isdigit() and len(t) >= 3 and n.startswith(t)) for n in nt)
                   for t in tokens):
                hasil.append(nama)
        return hasil

    def sesi_dosen(self, nama: str) -> list[Sesi]:
        return sorted((s for s in self.jadwal if s.dosen == nama),
                      key=lambda s: (HARI.index(s.hari), s.menit()[0], s.kode))

    # -- ruangan ---------------------------------------------------------------- #
    def daftar_ruang(self) -> list[str]:
        return sorted({s.ruang for s in self.jadwal})

    def ruang_status(self, hari: str, mulai: int, selesai: int) -> tuple[list[str], list[Sesi]]:
        """(ruang kosong, sesi yang memakai ruang) pada hari & rentang menit [mulai, selesai).
        Ruang yang dikenal = semua ruang yang tercatat di jadwal.csv."""
        terpakai = [s for s in self.jadwal
                    if s.hari == hari and s.menit()[0] < selesai and mulai < s.menit()[1]]
        pakai = {s.ruang for s in terpakai}
        kosong = [r for r in self.daftar_ruang() if r not in pakai]
        return kosong, sorted(terpakai, key=lambda s: (s.ruang, s.menit()[0]))

    # -- simulasi rencana studi --------------------------------------------------- #
    def cari_matkul(self, item: str) -> tuple[Optional[Matkul], list[Matkul]]:
        """Cocokkan teks bebas ke mata kuliah. (match, kandidat_ambigu).
        Urutan: kode -> nama persis -> awalan unik -> kata-utuh unik -> mirip (difflib)."""
        t = " ".join(re.sub(r"[^\w\s]", " ", item.lower()).split())
        if not t:
            return None, []
        mk = list(self.matkul.values())
        for m in mk:
            if m.kode.lower() == item.strip().lower():
                return m, []

        def norm(m: Matkul) -> str:
            return " ".join(re.sub(r"[^\w\s]", " ", m.nama.lower()).split())
        tepat = [m for m in mk if norm(m) == t]
        if tepat:
            return tepat[0], []
        for cocok in (lambda n: n.startswith(t + " "),
                      lambda n: f" {t} " in f" {n} "):
            kena = [m for m in mk if cocok(norm(m))]
            if len(kena) == 1:
                return kena[0], []
            if len(kena) > 1:
                return None, kena
        dekat = difflib.get_close_matches(t, [norm(m) for m in mk], n=1, cutoff=0.8)
        if dekat:
            return next(m for m in mk if norm(m) == dekat[0]), []
        return None, []

    def cek_rencana(self, item_rencana: list[str], item_lulus: Optional[list[str]] = None) -> HasilRencana:
        h = HasilRencana()
        kode_ada: set[str] = set()
        for it in item_rencana:
            m, amb = self.cari_matkul(it)
            if m and m.kode not in kode_ada:
                kode_ada.add(m.kode)
                h.dipilih.append(m)
            elif not m and amb:
                h.ambigu[it] = amb
            elif not m:
                h.tidak_ditemukan.append(it)
        lulus_kode: set[str] = set()
        for it in item_lulus or []:
            m, _ = self.cari_matkul(it)
            if m:
                lulus_kode.add(m.kode)
                h.lulus.append(m)
        for m in h.dipilih:
            for kp in m.prasyarat:
                pm = self.matkul[kp]
                if kp in kode_ada:
                    h.prasyarat_bersamaan.append((m, pm))
                elif kp not in lulus_kode:
                    h.prasyarat_kurang.append((m, pm))
        return h

    # -- pemeriksaan bentrok --------------------------------------------------- #
    def periksa(self) -> list[str]:
        """Peringatan (bukan error): jadwal bentrok pada kelas/semester, ruang, atau dosen yang sama."""
        pesan: list[str] = []
        s = self.jadwal
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                a, b = s[i], s[j]
                if a.hari != b.hari:
                    continue
                (a1, a2), (b1, b2) = a.menit(), b.menit()
                if not (a1 < b2 and b1 < a2):
                    continue
                na, nb = self.matkul[a.kode].nama, self.matkul[b.kode].nama
                ket = f"{a.hari} {a.mulai}-{a.selesai} {na} <-> {b.mulai}-{b.selesai} {nb}"
                if a.ruang == b.ruang:
                    pesan.append(f"Ruang bentrok ({a.ruang}): {ket}")
                if a.dosen == b.dosen:
                    pesan.append(f"Dosen bentrok ({a.dosen}): {ket}")
                if (self.matkul[a.kode].semester == self.matkul[b.kode].semester and a.kelas == b.kelas):
                    pesan.append(f"Jadwal mahasiswa bentrok (semester {self.matkul[a.kode].semester}, "
                                 f"kelas {a.kelas}): {ket}")
        sudah = {x.kode for x in s}
        for k in sorted(sudah):
            if not self.matkul[k].jenis:
                pesan.append(f"{k}: jenis mata kuliah kosong")
        return pesan

    # -- pembangkit entri KB ---------------------------------------------------- #
    def entri_kb(self) -> list[Entri]:
        """Entri yang DIBANGKITKAN dari data terstruktur (info_umum.json = FAQ biasa, tidak termasuk)."""
        e: list[Entri] = [self._ringkasan()]
        e += [self._entri_semester(n) for n in self.semester_kurikulum()]
        e += [self._entri_matkul(m) for m in self.matkul.values()]
        if self.jadwal:
            ada = set(self.semester_berjadwal())
            for n in self.semester_kurikulum():
                e.append(self._entri_jadwal(n, None))          # semester tanpa jadwal -> "belum tersedia"
                if n in ada:
                    e += [self._entri_jadwal(n, h) for h in HARI_KULIAH]
        return e

    def _label_dummy(self) -> str:
        return " (DATA CONTOH, belum resmi)" if self.dummy else ""

    def _sumber_kur(self) -> str:
        return str(self.kurikulum.get("sumber", "Daftar Matakuliah Kurikulum"))

    def _sumber_jadwal(self) -> str:
        return str(self.info.get("sumber") or "Jadwal perkuliahan")

    @staticmethod
    def _baris_mk(m: Matkul) -> str:
        return f"- {m.kode} {m.nama} ({m.sks} SKS)"

    def _ringkasan(self) -> Entri:
        k = self.kurikulum
        baris = []
        for s in k["semester"]:
            mk = self.matkul_semester(int(s["no"]))
            wajib = sum(m.sks for m in mk if m.jenis == "wajib")
            pil = sum(m.sks for m in mk if m.jenis == "pilihan")
            teks = f"- Semester {s['no']}: {len(mk)} mata kuliah, "
            teks += (f"SKS wajib {wajib} ditambah mata kuliah pilihan {pil} SKS (jumlah pada daftar {s['sks_tercetak']} SKS)"
                     if pil else f"{wajib} SKS")
            baris.append(teks)
        jawab = (f"Kurikulum tahun {k.get('kurikulum', '')} Program Studi {k.get('prodi', '')} "
                 f"{k.get('fakultas', '')} {k.get('universitas', '')} terdiri dari {len(k['semester'])} semester:\n"
                 + "\n".join(baris))
        return Entri(
            id="kurikulum-ringkasan", kategori="Kurikulum",
            pertanyaan="Berapa total SKS setiap semester pada kurikulum?",
            variasi=["ringkasan kurikulum informatika", "jumlah sks per semester kurikulum 2025",
                     "berapa semester kurikulum", "beban sks tiap semester"],
            kata_kunci=["kurikulum", "sks", "semester", "ringkasan", "informatika", "tahun 2025"],
            jawaban=jawab, sumber=self._sumber_kur())

    def _entri_semester(self, n: int) -> Entri:
        mk = self.matkul_semester(n)
        wajib = [m for m in mk if m.jenis == "wajib"]
        pil = [m for m in mk if m.jenis == "pilihan"]
        tercetak = next(int(s["sks_tercetak"]) for s in self.kurikulum["semester"] if int(s["no"]) == n)
        baris = [f"Mata kuliah semester {n} (kurikulum {self.kurikulum.get('kurikulum', '')}):"]
        if pil:
            baris.append("Wajib:")
        baris += [self._baris_mk(m) for m in wajib]
        if pil:
            baris.append("Pilihan:")
            baris += [self._baris_mk(m) for m in pil]
            baris.append(f"Total SKS wajib {sum(m.sks for m in wajib)}; SKS pilihan {sum(m.sks for m in pil)}; "
                         f"jumlah pada daftar kurikulum {tercetak} SKS ({len(mk)} mata kuliah).")
        else:
            baris.append(f"Total {sum(m.sks for m in mk)} SKS ({len(mk)} mata kuliah).")
        return Entri(
            id=f"sem-{n}", kategori="Kurikulum",
            pertanyaan=f"Mata kuliah apa saja di semester {n}?",
            variasi=[f"daftar mata kuliah semester {n}", f"matkul semester {n}",
                     f"kurikulum semester {n}", f"berapa sks semester {n}", f"semester {n} ambil apa"],
            kata_kunci=["semester", f"semester {n}", "mata kuliah", "matkul", "daftar", "kurikulum", "sks"],
            jawaban="\n".join(baris), sumber=self._sumber_kur())

    def _entri_matkul(self, m: Matkul) -> Entri:
        jenis = "pilihan" if m.jenis == "pilihan" else "wajib"
        kel = f" ({m.kelompok})" if m.kelompok else ""
        baris = [f"{m.nama} ({m.kode}) adalah mata kuliah {jenis}{kel}, semester {m.semester}, {m.sks} SKS "
                 f"({m.t} teori, {m.p} praktik, {m.l} lapangan)."]
        if m.prasyarat:
            ket = " (DATA CONTOH, belum resmi)" if self.prasyarat_dummy else ""
            baris.append("Prasyarat" + ket + ": " + ", ".join(
                f"{self.matkul[k].nama} ({k})" for k in m.prasyarat) + ".")
        sesi = self.sesi_matkul(m.kode)
        sumber = self._sumber_kur()
        if sesi:
            baris.append(f"Jadwal {self.tahun_ajaran}{self._label_dummy()}:".replace("Jadwal :", "Jadwal:"))
            baris += [f"- Kelas {s.kelas}, {s.hari} {s.mulai}-{s.selesai}, {s.ruang}, {s.dosen} ({s.jenis})"
                      for s in sesi]
            sumber = f"{sumber}; {self._sumber_jadwal()}"
        elif self.jadwal:
            baris.append("Jadwal mata kuliah ini belum tersedia di data.")
        return Entri(
            id=f"mk-{m.kode}", kategori="Mata Kuliah",
            pertanyaan=f"Informasi mata kuliah {m.nama}",
            variasi=[f"berapa sks {m.nama}", f"{m.nama} semester berapa", f"jadwal {m.nama}",
                     f"dosen pengampu {m.nama}", f"ruang kuliah {m.nama}", f"kode mata kuliah {m.nama}"],
            kata_kunci=[m.nama, m.kode, "mata kuliah", "sks", "jadwal", "dosen", "ruang"],
            jawaban="\n".join(baris), sumber=sumber)

    def _entri_jadwal(self, n: int, hari: Optional[str]) -> Entri:
        sesi = self.sesi_semester(n, hari)
        ta = f" {self.tahun_ajaran}" if self.tahun_ajaran else ""
        judul = f"semester {n}" + (f" hari {hari}" if hari else "")
        kepala = f"Jadwal kuliah {judul}{ta}{self._label_dummy()}:"
        baris = [kepala]
        if not sesi:
            baris = [f"Jadwal kuliah {judul}{ta} belum tersedia di data."]
        elif hari:
            baris += [self._baris_sesi(s, tanpa_hari=True) for s in sesi]
        else:
            for h in HARI:
                ada = [s for s in sesi if s.hari == h]
                if ada:
                    baris.append(f"{h}:")
                    baris += [self._baris_sesi(s, tanpa_hari=True) for s in ada]
        pert = f"Jadwal kuliah semester {n}" + (f" hari {hari}?" if hari else "?")
        var = [f"jadwal semester {n}", f"jadwal kuliah semester {n}", f"jam kuliah semester {n}"]
        kk = ["jadwal", "kuliah", "semester", f"semester {n}", "jam", "ruang", "dosen"]
        if hari:
            var = [f"jadwal hari {hari} semester {n}", f"kuliah hari {hari} semester {n}",
                   f"hari {hari} ada kuliah apa semester {n}", f"jadwal {hari} semester {n}"]
            kk += [hari.lower(), "hari"]
        else:
            var += [f"kuliah semester {n} hari apa saja", f"jadwal lengkap semester {n}"]
        return Entri(id=f"jadwal-s{n}" + (f"-{hari.lower()}" if hari else ""), kategori="Jadwal Kuliah",
                     pertanyaan=pert, variasi=var, kata_kunci=kk, jawaban="\n".join(baris),
                     sumber=f"{self._sumber_jadwal()}; {self._sumber_kur()}")

    def _baris_sesi(self, s: Sesi, tanpa_hari: bool = False) -> str:
        nama = self.matkul[s.kode].nama
        return f"- {s.mulai}-{s.selesai} {nama}, {s.ruang}, {s.dosen}, kelas {s.kelas} ({s.jenis})"


def muat_entri_data(folder: Path) -> list[Entri]:
    """Entri KB hasil bangkitan dari data terstruktur ([] bila folder tidak memilikinya)."""
    d = DataAkademik.muat(folder)
    return d.entri_kb() if d else []
