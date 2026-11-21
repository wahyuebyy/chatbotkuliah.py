"""
kalender.py  -  Hitung mundur kalender akademik (data dari info_umum.json -> "kalender_akademik").

Format satu acara:
    {"id": "uts", "nama": "Minggu UTS", "mulai": "2026-10-19", "akhir": "2026-10-30",
     "kata_kunci": ["uts", "ujian tengah semester"]}        # "akhir" opsional (tanpa = satu hari/tenggat)

Semua selisih dihitung dalam hari KALENDER antar tanggal (bukan jam), jadi hasilnya tidak bergeser
karena zona waktu: hari ini WIB vs tanggal acara.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .kb_loader import KBError

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]
HARI_NAMA = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def tanggal_id(d: date, dengan_hari: bool = False) -> str:
    s = f"{d.day} {BULAN[d.month - 1]} {d.year}"
    return f"{HARI_NAMA[d.weekday()]}, {s}" if dengan_hari else s


def _tgl(teks: str, asal: str) -> date:
    try:
        return date.fromisoformat(str(teks).strip())
    except ValueError:
        raise KBError(f"{asal}: tanggal '{teks}' salah (pakai YYYY-MM-DD)") from None


@dataclass
class Acara:
    id: str
    nama: str
    mulai: date
    akhir: date
    kata_kunci: list[str] = field(default_factory=list)

    @property
    def rentang(self) -> bool:
        return self.akhir > self.mulai

    def teks_tanggal(self) -> str:
        if not self.rentang:
            return tanggal_id(self.mulai, True)
        return f"{tanggal_id(self.mulai)} s.d. {tanggal_id(self.akhir)}"


@dataclass
class StatusAcara:
    acara: Acara
    status: str      # akan | berlangsung | lewat
    hari: int        # akan: hari sampai mulai; berlangsung: hari sampai akhir; lewat: hari sejak akhir

    def ringkas(self) -> str:
        a = self.acara
        if self.status == "akan":
            if self.hari == 0:
                return f"⏳ {a.nama}: HARI INI"
            if self.hari == 1:
                return f"⏳ {a.nama}: besok"
            return f"⏳ {a.nama} tinggal {self.hari} hari lagi"
        if self.status == "berlangsung":
            sisa = "berakhir hari ini" if self.hari == 0 else f"berakhir {self.hari} hari lagi"
            return f"🔔 {a.nama} sedang berlangsung ({sisa})"
        return f"✔ {a.nama} sudah lewat {self.hari} hari lalu"


class KalenderAkademik:
    def __init__(self, acara: list[Acara], dummy: bool = False):
        self.acara = sorted(acara, key=lambda a: (a.mulai, a.id))
        self.dummy = dummy

    # -- pemuatan ---------------------------------------------------------- #
    @classmethod
    def dari_json(cls, path: Path) -> Optional["KalenderAkademik"]:
        path = Path(path)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise KBError(f"Format JSON rusak di {path}: {exc}") from exc
        return cls.dari_daftar(data.get("kalender_akademik") or [], bool(data.get("kalender_dummy", False)))

    @classmethod
    def dari_daftar(cls, daftar: list[dict], dummy: bool = False) -> Optional["KalenderAkademik"]:
        acara: list[Acara] = []
        for i, e in enumerate(daftar, 1):
            asal = f"kalender_akademik[{i}]"
            if not e.get("id") or not e.get("nama") or not e.get("mulai"):
                raise KBError(f"{asal}: field 'id', 'nama', 'mulai' wajib diisi")
            mulai = _tgl(e["mulai"], asal)
            akhir = _tgl(e["akhir"], asal) if e.get("akhir") else mulai
            if akhir < mulai:
                raise KBError(f"{asal}: 'akhir' tidak boleh sebelum 'mulai'")
            acara.append(Acara(str(e["id"]), str(e["nama"]), mulai, akhir,
                               [str(k).lower() for k in e.get("kata_kunci", [])]))
        if len({a.id for a in acara}) != len(acara):
            raise KBError("kalender_akademik: id acara ganda")
        return cls(acara, dummy) if acara else None

    # -- kueri ------------------------------------------------------------- #
    @staticmethod
    def _hari_ini(sekarang: datetime | date) -> date:
        return sekarang.date() if isinstance(sekarang, datetime) else sekarang

    def status(self, a: Acara, sekarang: datetime | date) -> StatusAcara:
        h = self._hari_ini(sekarang)
        if h < a.mulai:
            return StatusAcara(a, "akan", (a.mulai - h).days)
        if h <= a.akhir:
            return StatusAcara(a, "berlangsung", (a.akhir - h).days)
        return StatusAcara(a, "lewat", (h - a.akhir).days)

    def semua(self, sekarang: datetime | date) -> list[StatusAcara]:
        """Urut: yang sedang berlangsung & akan datang (terdekat dulu), lalu yang sudah lewat."""
        st = [self.status(a, sekarang) for a in self.acara]
        aktif = sorted((s for s in st if s.status != "lewat"), key=lambda s: (s.acara.mulai, s.acara.id))
        lewat = sorted((s for s in st if s.status == "lewat"), key=lambda s: s.hari)
        return aktif + lewat

    def cocok(self, teks: str) -> list[Acara]:
        """Acara yang kata kuncinya disebut di `teks` (kata utuh; frasa lebih panjang diutamakan)."""
        t = " " + " ".join(re.sub(r"[^\w\s]", " ", teks.lower()).split()) + " "
        kena = []
        for a in self.acara:
            panjang = max((len(k) for k in a.kata_kunci if f" {k} " in t), default=0)
            if panjang:
                kena.append((panjang, a))
        if not kena:
            return []
        puncak = max(p for p, _ in kena)
        # frasa spesifik ("revisi krs") menang atas kata umum ("krs")
        return [a for p, a in kena if p == puncak] if puncak >= 8 else [a for _, a in kena]

    def banner(self, sekarang: datetime | date, dalam_hari: int = 14, maks: int = 2) -> list[StatusAcara]:
        """Acara yang sedang berlangsung atau mulai dalam `dalam_hari` hari (untuk banner web)."""
        hasil = [s for s in self.semua(sekarang)
                 if s.status == "berlangsung" or (s.status == "akan" and s.hari <= dalam_hari)]
        return hasil[:maks]

    # -- teks jawaban -------------------------------------------------------- #
    def jawab(self, teks: str, sekarang: datetime | date) -> str:
        h = self._hari_ini(sekarang)
        dipilih = self.cocok(teks)
        baris = [f"Hitung mundur kalender akademik (per {tanggal_id(h, True)}, WIB):"]
        for a in (dipilih or []):
            s = self.status(a, sekarang)
            baris += [s.ringkas(), f"   Jadwal: {a.teks_tanggal()}"]
        if not dipilih:
            for s in self.semua(sekarang):
                baris += [s.ringkas(), f"   Jadwal: {s.acara.teks_tanggal()}"]
        if self.dummy:
            baris.append("\nCATATAN: tanggal ini DATA CONTOH (belum resmi); pastikan ke kalender akademik resmi Prodi.")
        return "\n".join(baris)

    def sumber(self) -> str:
        return "Kalender akademik (info_umum.json" + (", DATA CONTOH)" if self.dummy else ")")
