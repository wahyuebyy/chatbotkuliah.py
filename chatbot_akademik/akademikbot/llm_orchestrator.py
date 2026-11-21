"""
llm_orchestrator.py  -  Orkestrasi multi-model (Claude / GPT / Gemini) di atas KB bersama.

PENANGGUNG JAWAB: Anggota 3 (LLM & Anti-Halusinasi)

Peran dalam arsitektur:
    Chatbot (router) --alasan rute--> Orchestrator --pilih model per jenis tugas--> Provider
                                          |  jawaban TIDAK lolos guardrail / error -> model berikutnya
                                          |  (opsional) model LAIN memverifikasi jawaban terhadap konteks
    Knowledge base + riwayat sesi dipakai bersama oleh semua model (konteks [S#] yang sama).

Guardrail tetap berlaku untuk SEMUA model: jawaban baru diterima jika lolos `validasi_jawaban`.
Antarmuka mengikuti LLMClient (tersedia, error, model) + `jawab_tervalidasi` yang dipakai router.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Optional

from .config import LLM_RUTE, LLM_URUTAN_DEFAULT, LLM_VERIFIKASI
from .guardrail import validasi_jawaban
from .llm_client import SYSTEM_PROMPT, bangun_konteks, bangun_pesan, teks_konteks
from .llm_providers import SEMUA_PROVIDER, Provider
from .tfidf import Hasil

SYSTEM_VERIFIKATOR = (
    "Kamu pemeriksa fakta. Terima KONTEKS dan JAWABAN. Balas HANYA satu kata: YA jika setiap "
    "klaim pada JAWABAN didukung KONTEKS, atau TIDAK jika ada klaim yang tidak didukung."
)


@dataclass
class Jawaban:
    teks: str = ""
    lolos: bool = False
    alasan: str = ""                      # alasan guardrail / kegagalan terakhir
    sitasi: list[int] = field(default_factory=list)
    model: str = ""                       # nama model yang jawabannya dipakai
    percobaan: list[str] = field(default_factory=list)   # jejak: "gpt:guardrail:...", "claude:ok"
    semua_error: bool = False             # True bila tak satu pun model berhasil dipanggil


class LLMOrchestrator:
    def __init__(self, providers: dict[str, Provider], rute: Optional[dict] = None,
                 urutan_default: Optional[list[str]] = None,
                 verifikasi: bool = LLM_VERIFIKASI):
        self.providers = providers
        self.rute = rute if rute is not None else LLM_RUTE
        self.urutan_default = urutan_default or LLM_URUTAN_DEFAULT
        self.verifikasi = verifikasi

    # -- antarmuka mirip LLMClient --------------------------------------------- #
    @property
    def aktif(self) -> list[Provider]:
        return [p for p in self.providers.values() if p.tersedia]

    @property
    def tersedia(self) -> bool:
        return bool(self.aktif)

    @property
    def error(self) -> Optional[str]:
        return None if self.tersedia else (
            "tidak ada API key (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY)")

    @property
    def model(self) -> str:
        return "multi-model: " + ", ".join(f"{p.nama}={p.model}" for p in self.aktif)

    # -- pemilihan model --------------------------------------------------------- #
    def urutan(self, alasan: str = "") -> list[Provider]:
        """Urutan model untuk alasan rute ini; hanya yang tersedia, tanpa duplikat."""
        nama = self.rute.get(alasan, self.urutan_default)
        nama = list(dict.fromkeys([*nama, *self.urutan_default, *self.providers]))
        return [self.providers[n] for n in nama if n in self.providers and self.providers[n].tersedia]

    # -- eksekusi ---------------------------------------------------------------- #
    def jawab_tervalidasi(self, pertanyaan: str, konteks: list[Hasil],
                          riwayat: list[tuple[str, str]], alasan: str = "") -> Jawaban:
        urut = self.urutan(alasan)
        if not urut:
            return Jawaban(alasan=self.error or "tidak ada model", semua_error=True)

        pesan, daftar_konteks = bangun_pesan(pertanyaan, konteks, riwayat), teks_konteks(konteks)
        hasil = Jawaban(semua_error=True)
        for p in urut:
            try:
                teks = p.generate(SYSTEM_PROMPT, pesan)
            except Exception as exc:                       # jaringan/kuota/diblokir -> model lain
                hasil.percobaan.append(f"{p.nama}:error:{type(exc).__name__}")
                hasil.alasan = f"{p.nama}_error"
                continue
            hasil.semua_error = False
            v = validasi_jawaban(teks, daftar_konteks)
            if not v.lolos:
                hasil.percobaan.append(f"{p.nama}:guardrail:{v.alasan}")
                hasil.alasan, hasil.teks = v.alasan, teks
                continue
            if self.verifikasi:
                ok, jejak = self._verifikasi(p, urut, teks, konteks)
                if jejak:
                    hasil.percobaan.append(jejak)
                if not ok:
                    hasil.percobaan.append(f"{p.nama}:verifikasi_gagal")
                    hasil.alasan = "verifikasi_silang_gagal"
                    continue
            hasil.percobaan.append(f"{p.nama}:ok")
            hasil.teks, hasil.lolos, hasil.alasan = teks, True, "ok"
            hasil.sitasi, hasil.model = v.sitasi, p.nama
            return hasil
        return hasil

    def _verifikasi(self, penjawab: Provider, urut: list[Provider], jawaban: str,
                    konteks: list[Hasil]) -> tuple[bool, str]:
        """Model LAIN menilai apakah jawaban didukung konteks. Tanpa verifikator -> dilewati."""
        verif = next((p for p in urut if p is not penjawab), None)
        if verif is None:
            return True, f"{penjawab.nama}:verifikasi_dilewati(tanpa_model_lain)"
        try:
            balas = verif.generate(SYSTEM_VERIFIKATOR, [{
                "role": "user",
                "content": f"KONTEKS:\n{bangun_konteks(konteks)}\n\nJAWABAN:\n{jawaban}"}])
        except Exception as exc:
            return True, f"{verif.nama}:verifikasi_dilewati({type(exc).__name__})"
        kata = balas.strip().upper().split()
        return bool(kata) and kata[0].strip(".,!") == "YA", f"{verif.nama}:verifikator"

    def selesaikan(self, sistem: str, teks: str, max_tokens: int = 700) -> str:
        """Panggilan bebas (mis. kuis): coba model satu per satu sampai ada yang berhasil."""
        urut = self.urutan()
        if not urut:
            raise RuntimeError(self.error)
        galat: Optional[Exception] = None
        for p in urut:
            try:
                pesan = [{"role": "user", "content": teks}]
                if "max_tokens" in inspect.signature(p.generate).parameters:
                    return p.generate(sistem, pesan, max_tokens=max_tokens)
                return p.generate(sistem, pesan)
            except Exception as exc:                       # model berikutnya
                galat = exc
        raise RuntimeError(f"semua model gagal ({type(galat).__name__})")

    # -- kompatibilitas: panggilan tunggal tanpa validasi ------------------------ #
    def jawab(self, pertanyaan: str, konteks: list[Hasil],
              riwayat: list[tuple[str, str]]) -> str:
        urut = self.urutan()
        if not urut:
            raise RuntimeError(self.error)
        return urut[0].generate(SYSTEM_PROMPT, bangun_pesan(pertanyaan, konteks, riwayat))


def buat_llm_multi() -> LLMOrchestrator:
    """Orchestrator berisi Claude, GPT, Gemini; yang punya API key di lingkungan yang aktif."""
    return LLMOrchestrator({n: cls() for n, cls in SEMUA_PROVIDER.items()})


def buat_llm_multi_demo(mode_gpt: str = "halusinasi") -> LLMOrchestrator:
    """Tiga model DUMMY: GPT bermode `mode_gpt` (default 'halusinasi') untuk memperlihatkan
    failover guardrail; Claude & Gemini menjawab baik."""
    from .llm_demo import DemoProvider
    return LLMOrchestrator({
        "claude": DemoProvider("claude", "baik"),
        "gpt": DemoProvider("gpt", mode_gpt),
        "gemini": DemoProvider("gemini", "baik"),
    })
