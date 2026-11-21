"""
guardrail.py  -  Validasi jawaban LLM agar tidak keluar dari knowledge base.

PENANGGUNG JAWAB: Anggota 3 (LLM & Anti-Halusinasi)

Catatan tugas: "LLM tidak boleh menjawab dari pengetahuannya sendiri."
Prompt saja tidak cukup, jadi setiap jawaban LLM diperiksa lagi lewat 5 lapis:

  1. LLM menjawab TIDAK_ADA_INFO                      -> tolak
  2. Tidak ada sitasi [S#] sama sekali                -> tolak
  3. Ada sitasi ke nomor yang tidak ada ([S9], [S0])  -> tolak
  4. Ada angka di jawaban yang tidak ada di konteks   -> tolak (anti angka karangan)
  5. Kata isi jawaban kurang "berpijak" pada konteks, atau terlalu sedikit
     baris/paragraf yang bersitasi                    -> tolak

Jawaban yang lolos membawa daftar sitasi yang benar-benar dipakai.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import GROUNDING_MIN, KALIMAT_BERSITASI_MIN, KATA_MIN_KALIMAT_SUBSTANTIF
from .preprocessing import tokenize

_SITASI = re.compile(r"\[S(\d+)\]")
_PENANDA_LIST = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*\u2022])\s+")
_ANGKA = re.compile(r"\d+(?:[.,]\d+)*")
_PISAH_BARIS = re.compile(r"\n+")

TIDAK_ADA_INFO = "TIDAK_ADA_INFO"


@dataclass
class HasilValidasi:
    lolos: bool
    alasan: str = "ok"
    sitasi: list[int] = field(default_factory=list)   # nomor S# yang valid dan dipakai
    grounding: float = 0.0


def _angka_dalam(teks: str) -> set[str]:
    """Ambil semua angka; '18-24' dan '2,5' dipecah supaya perbandingan adil."""
    hasil: set[str] = set()
    for m in _ANGKA.findall(teks):
        hasil.add(m)
        hasil.update(re.split(r"[.,]", m))
    return hasil


def _bersihkan(teks: str) -> str:
    """Buang sitasi dan penanda daftar bernomor agar tidak dianggap fakta/angka."""
    return _PENANDA_LIST.sub("", _SITASI.sub(" ", teks))


def validasi_jawaban(jawaban: str, konteks: list[str]) -> HasilValidasi:
    """
    jawaban : teks mentah dari LLM
    konteks : daftar teks potongan KB; konteks[0] = [S1], konteks[1] = [S2], ...
    """
    jawaban = (jawaban or "").strip()
    if not jawaban:
        return HasilValidasi(False, "jawaban_kosong")
    if TIDAK_ADA_INFO in jawaban:
        return HasilValidasi(False, "llm_tidak_tahu")

    # (2) & (3) sitasi
    nomor = [int(n) for n in _SITASI.findall(jawaban)]
    if not nomor:
        return HasilValidasi(False, "tanpa_sitasi")
    tak_valid = sorted({n for n in nomor if n < 1 or n > len(konteks)})
    if tak_valid:
        return HasilValidasi(False, f"sitasi_tidak_valid:{tak_valid}")
    sitasi = sorted(set(nomor))

    teks_konteks = "\n".join(konteks)
    bersih = _bersihkan(jawaban)

    # (4) angka harus berasal dari konteks
    asing = sorted(_angka_dalam(bersih) - _angka_dalam(teks_konteks))
    if asing:
        return HasilValidasi(False, f"angka_tidak_ada_di_konteks:{asing}", sitasi)

    # (5a) kata isi harus berpijak pada konteks
    tok_jawaban = tokenize(bersih)
    tok_konteks = set(tokenize(teks_konteks))
    grounding = (
        sum(1 for t in tok_jawaban if t in tok_konteks) / len(tok_jawaban)
        if tok_jawaban else 1.0
    )
    if grounding < GROUNDING_MIN:
        return HasilValidasi(False, f"grounding_rendah:{grounding:.2f}", sitasi, grounding)

    # (5b) baris/paragraf substantif harus bersitasi (satu sitasi di ujung paragraf cukup;
    #      butir daftar dihitung per baris)
    substantif = bersitasi = 0
    for baris in _PISAH_BARIS.split(jawaban):
        if len(tokenize(_bersihkan(baris))) >= KATA_MIN_KALIMAT_SUBSTANTIF:
            substantif += 1
            if _SITASI.search(baris):
                bersitasi += 1
    if substantif and bersitasi / substantif < KALIMAT_BERSITASI_MIN:
        return HasilValidasi(False, "sitasi_kurang", sitasi, grounding)

    return HasilValidasi(True, "ok", sitasi, grounding)
