"""
dokumen.py  -  Dokumen unggahan SEMENTARA (TXT/PDF) sebagai konteks tambahan tanya-jawab.

Alur: berkas -> teks (pypdf untuk PDF bila terpasang) -> dipotong jadi potongan ~700 karakter ->
dibungkus sebagai Entri (kategori "Dokumen Unggahan") -> diindeks TF-IDF yang sama dengan KB.
Dengan begitu LLM, sitasi [S#], dan guardrail anti-halusinasi bekerja persis seperti untuk KB.

Dokumen hanya hidup di memori satu sesi (tidak ditulis ke disk). Isinya TIDAK DIPERCAYA: teks di
dalamnya diperlakukan sebagai data, bukan perintah (lihat aturan 9 di SYSTEM_PROMPT).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Optional

from .config import (MAKS_DOK_BYTES, MAKS_DOK_HALAMAN_PDF, MAKS_DOK_KARAKTER, TOP_K,
                     UKURAN_POTONGAN_DOK)
from .kb_loader import Entri
from .tfidf import Hasil, TfidfIndex

KATEGORI_DOK = "Dokumen Unggahan"
_KONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class DokumenError(ValueError):
    """Berkas tidak bisa dipakai (format, ukuran, kosong, terenkripsi, dsb.). Pesan aman ditampilkan."""


def _dekode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", errors="replace")


def _teks_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise DokumenError("Membaca PDF butuh paket 'pypdf' (pip install pypdf). "
                           "Alternatif: simpan sebagai .txt lalu unggah.") from None
    try:
        rd = PdfReader(io.BytesIO(data))
        if rd.is_encrypted:
            raise DokumenError("PDF terenkripsi/berpassword tidak dapat dibaca.")
        halaman = rd.pages[:MAKS_DOK_HALAMAN_PDF]
        teks = "\n\n".join((p.extract_text() or "") for p in halaman)
    except DokumenError:
        raise
    except Exception:
        raise DokumenError("PDF rusak atau tidak dapat dibaca.") from None
    if not teks.strip():
        raise DokumenError("PDF tidak memuat teks (mungkin hasil scan/gambar). Gunakan PDF berteks atau .txt.")
    return teks


def ekstrak_teks(nama: str, data: bytes) -> str:
    """Teks bersih dari berkas .txt / .pdf. Melempar DokumenError dengan pesan ramah."""
    if not data:
        raise DokumenError("Berkas kosong.")
    if len(data) > MAKS_DOK_BYTES:
        raise DokumenError(f"Berkas terlalu besar (maks {MAKS_DOK_BYTES // (1024 * 1024)} MB).")
    ext = (nama.rsplit(".", 1)[-1] if "." in nama else "").lower()
    if ext == "pdf" or data[:5] == b"%PDF-":
        teks = _teks_pdf(data)
    elif ext in ("txt", "text", "md"):
        teks = _dekode(data)
    else:
        raise DokumenError("Format belum didukung. Unggah berkas .txt atau .pdf.")
    teks = _KONTROL.sub(" ", teks).replace("\r\n", "\n").replace("\r", "\n")
    teks = re.sub(r"[ \t]+", " ", teks)
    teks = re.sub(r"\n{3,}", "\n\n", teks).strip()
    if len(teks) < 20:
        raise DokumenError("Isi dokumen terlalu sedikit untuk dipakai.")
    return teks[:MAKS_DOK_KARAKTER]


def potong(teks: str, ukuran: int = UKURAN_POTONGAN_DOK) -> list[str]:
    """Potong per paragraf, gabungkan sampai ~`ukuran` karakter; paragraf panjang dipecah per kalimat."""
    unit: list[str] = []
    for para in re.split(r"\n\s*\n", teks):
        para = " ".join(para.split())
        if not para:
            continue
        if len(para) <= ukuran:
            unit.append(para)
        else:
            unit += [k for k in re.split(r"(?<=[.!?])\s+", para) if k]
    hasil: list[str] = []
    cur = ""
    for u in unit:
        while len(u) > ukuran:                       # kalimat super panjang
            if cur:
                hasil.append(cur)
                cur = ""
            hasil.append(u[:ukuran])
            u = u[ukuran:]
        if cur and len(cur) + 1 + len(u) > ukuran:
            hasil.append(cur)
            cur = u
        else:
            cur = f"{cur} {u}".strip()
    if cur:
        hasil.append(cur)
    return hasil


@dataclass
class Dokumen:
    nama: str
    teks: str
    potongan: list[str] = field(default_factory=list)
    index: Optional[TfidfIndex] = None

    @classmethod
    def buat(cls, nama: str, teks: str) -> "Dokumen":
        nama = re.sub(r"[^\w.\- ()]", "_", nama.split("/")[-1].split("\\")[-1])[:80] or "dokumen"
        pot = potong(teks)
        if not pot:
            raise DokumenError("Isi dokumen terlalu sedikit untuk dipakai.")
        entri = [Entri(id=f"dok-{i}", kategori=KATEGORI_DOK,
                       pertanyaan=f"{nama} bagian {i}", variasi=[p], kata_kunci=[],
                       jawaban=p, sumber=f"Dokumen unggahan: {nama}")
                 for i, p in enumerate(pot, 1)]
        return cls(nama, teks, pot, TfidfIndex(entri))

    @classmethod
    def dari_berkas(cls, nama: str, data: bytes) -> "Dokumen":
        return cls.buat(nama, ekstrak_teks(nama, data))

    def cari(self, q: str, k: int = TOP_K) -> list[Hasil]:
        return self.index.cari(q, k=k) if self.index else []

    def ringkas(self) -> dict:
        return {"nama": self.nama, "karakter": len(self.teks), "potongan": len(self.potongan)}
