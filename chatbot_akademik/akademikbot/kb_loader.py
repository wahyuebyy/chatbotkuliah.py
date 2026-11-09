"""
kb_loader.py  -  Memuat & memvalidasi knowledge base (KB) lokal.

PENANGGUNG JAWAB: Anggota 1 (Data & Knowledge Base)

Format knowledge_base.json:
{
  "_catatan": "...",
  "entri": [
    {
      "id": "krs-01",                 # unik
      "kategori": "Perkuliahan",
      "pertanyaan": "Bagaimana cara mengisi KRS?",
      "variasi": ["cara registrasi mata kuliah", ...],   # cara lain bertanya hal yang sama
      "kata_kunci": ["krs", "registrasi", ...],
      "jawaban": "....",              # jawaban resmi, sudah diverifikasi
      "sumber": "Panduan Akademik - Bab Registrasi"
    }
  ]
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

WAJIB = ("id", "pertanyaan", "jawaban")


class KBError(ValueError):
    """Knowledge base tidak valid (berkas rusak, field wajib hilang, id ganda)."""


@dataclass
class Entri:
    id: str
    kategori: str
    pertanyaan: str
    variasi: list[str] = field(default_factory=list)
    kata_kunci: list[str] = field(default_factory=list)
    jawaban: str = ""
    sumber: str = "-"

    def teks_indeks(self) -> str:
        """Hanya field 'penanda topik' yang diindeks (bukan isi jawaban) agar presisi.
        Pertanyaan & kata kunci diberi bobot lebih lewat pengulangan."""
        return " ".join(
            [self.pertanyaan] * 3
            + self.variasi * 2
            + self.kata_kunci * 3
        )


def muat_kb(path: Path) -> list[Entri]:
    """Baca KB dari JSON, validasi, dan kembalikan daftar Entri."""
    path = Path(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise KBError(f"Berkas knowledge base tidak ditemukan: {path}") from exc
    except json.JSONDecodeError as exc:
        raise KBError(f"Format JSON rusak di {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("entri"), list):
        raise KBError("KB harus berupa objek JSON dengan kunci 'entri' (list).")

    hasil: list[Entri] = []
    sudah: set[str] = set()
    for i, e in enumerate(data["entri"], 1):
        if not isinstance(e, dict):
            raise KBError(f"Entri ke-{i} bukan objek JSON.")
        for k in WAJIB:
            if not str(e.get(k, "")).strip():
                raise KBError(f"Entri ke-{i} ({e.get('id', '?')}): field '{k}' wajib diisi.")
        if e["id"] in sudah:
            raise KBError(f"ID ganda di KB: {e['id']}")
        sudah.add(e["id"])
        hasil.append(
            Entri(
                id=e["id"],
                kategori=e.get("kategori", "Umum"),
                pertanyaan=e["pertanyaan"],
                variasi=list(e.get("variasi", [])),
                kata_kunci=list(e.get("kata_kunci", [])),
                jawaban=e["jawaban"],
                sumber=e.get("sumber", "-"),
            )
        )
    if not hasil:
        raise KBError("KB kosong.")
    return hasil


def periksa_kualitas(entri: list[Entri]) -> list[str]:
    """Kembalikan daftar peringatan (bukan error) agar KB makin akurat untuk TF-IDF."""
    pesan: list[str] = []
    for e in entri:
        if len(e.variasi) < 3:
            pesan.append(f"[{e.id}] hanya {len(e.variasi)} variasi pertanyaan (disarankan >= 3).")
        if len(e.kata_kunci) < 3:
            pesan.append(f"[{e.id}] hanya {len(e.kata_kunci)} kata kunci (disarankan >= 3).")
        if e.sumber.strip() in ("", "-"):
            pesan.append(f"[{e.id}] belum mencantumkan sumber resmi.")
        if len(e.jawaban) < 40:
            pesan.append(f"[{e.id}] jawaban sangat pendek, pastikan sudah lengkap.")
    return pesan
