"""
llm_demo.py  -  LLM DUMMY (tiruan) untuk demo & pengujian tanpa API key / internet.

PENANGGUNG JAWAB: Anggota 3 (LLM & Anti-Halusinasi)

Ini BUKAN model bahasa sungguhan. Objek ini meniru antarmuka klien Anthropic
(`client.messages.create(...)`) dan menyusun jawaban dengan aturan sederhana dari blok
KONTEKS [S1], [S2], ... pada pesan pengguna. Gunanya memperlihatkan seluruh jalur
router -> LLM -> guardrail -> sumber bekerja, termasuk saat LLM "nakal".

Mode:
  baik          jawaban dirangkum dari konteks, tiap baris bersitasi          -> LOLOS guardrail
  halusinasi    menambahkan angka karangan (mis. biaya) yang tidak ada di KB   -> DITOLAK
  tanpa_sitasi  isi benar tetapi tidak ada penanda [S#]                        -> DITOLAK
  sitasi_palsu  mengutip [S9] yang tidak ada                                   -> DITOLAK
  tidak_tahu    membalas TIDAK_ADA_INFO                                        -> DITOLAK -> fallback
"""

from __future__ import annotations

import re
from types import SimpleNamespace

MODE_DEMO = ("baik", "halusinasi", "tanpa_sitasi", "sitasi_palsu", "tidak_tahu")
MODEL_DEMO = "demo-llm (tiruan)"

# Jawaban boleh berbaris banyak (jadwal/daftar mata kuliah): ambil sampai blok [S#] berikutnya.
_BLOK = re.compile(r"\[S(\d+)\][^\n]*\nQ: ([^\n]*)\nA: (.*?)(?=\n\n\[S\d+\]|\Z)", re.S)


def _parse_konteks(pesan: str) -> list[tuple[int, str, str]]:
    """Ambil (nomor, pertanyaan, jawaban) dari blok KONTEKS pada pesan pengguna."""
    bagian = pesan.split("PERTANYAAN PENGGUNA:")[0]
    return [(int(n), q.strip(), a.strip()) for n, q, a in _BLOK.findall(bagian)]


def _kutip(teks: str, n: int) -> list[str]:
    """Beri sitasi [S#] pada tiap baris (jawaban berbaris banyak: tiap butir bersitasi)."""
    return [f"{b} [S{n}]" for b in teks.splitlines() if b.strip()]


def _susun(mode: str, blok: list[tuple[int, str, str]]) -> str:
    if not blok or mode == "tidak_tahu":
        return "TIDAK_ADA_INFO"
    if len(blok) == 1:
        baris = _kutip(blok[0][2], blok[0][0])
    else:                                   # beberapa topik: judul topik + isi tiap topik
        baris = []
        for n, q, a in blok:
            baris.append(f"{q.rstrip('?')}: [S{n}]")
            baris += _kutip(a, n)
    if mode == "baik":
        return "\n".join(baris)
    if mode == "halusinasi":
        return "\n".join(baris) + "\nBiaya pengurusannya sebesar Rp 2.500.000 [S1]."
    if mode == "tanpa_sitasi":
        return re.sub(r" ?\[S\d+\]", "", "\n".join(baris))
    if mode == "sitasi_palsu":
        return "\n".join(baris) + "\nInformasi tambahan ada di aturan terbaru [S9]."
    raise ValueError(f"mode tidak dikenal: {mode}")


class _Messages:
    def __init__(self, mode: str):
        self.mode = mode
        self.panggilan = 0

    def create(self, **kwargs):
        self.panggilan += 1
        pesan_terakhir = kwargs["messages"][-1]["content"]
        teks = _susun(self.mode, _parse_konteks(pesan_terakhir))
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=teks)])


class DemoClient:
    """Pengganti `anthropic.Anthropic(...)` untuk demo. Suntikkan lewat LLMClient(client=...)."""

    def __init__(self, mode: str = "baik"):
        if mode not in MODE_DEMO:
            raise ValueError(f"mode harus salah satu dari {MODE_DEMO}")
        self.mode = mode
        self.messages = _Messages(mode)


def buat_llm_demo(mode: str = "baik"):
    """LLMClient yang memakai DemoClient (tanpa API key)."""
    from .llm_client import LLMClient
    return LLMClient(client=DemoClient(mode), model=f"{MODEL_DEMO} - {mode}")


class DemoProvider:
    """Provider DUMMY (antarmuka sama dengan llm_providers.Provider) untuk demo multi-model."""

    def __init__(self, nama: str, mode: str = "baik"):
        self.nama = nama
        self.mode = mode
        self.model = f"demo-{nama}({mode})"
        self.api_key = "demo"
        self.klien = DemoClient(mode)

    @property
    def tersedia(self) -> bool:
        return True

    def generate(self, system: str, pesan: list[dict[str, str]]) -> str:
        if system.startswith("Kamu pemeriksa fakta"):      # peran verifikator
            return "YA" if self.mode == "baik" else "TIDAK"
        resp = self.klien.messages.create(system=system, messages=pesan)
        return resp.content[0].text.strip()
