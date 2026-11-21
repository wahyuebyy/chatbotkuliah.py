"""
setup_otomatis.py  -  Persiapan "sekali klik": .env otomatis, deteksi mode (multi/offline), dependensi.

    python -m akademikbot.setup_otomatis --pasang     # pasang paket di requirements.txt yang belum ada

Prinsip anti-error: semua fungsi di sini TIDAK melempar error ke pengguna. Bila sesuatu gagal
(tidak ada internet, pip gagal, .env.example hilang) aplikasi tetap jalan di mode offline.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from .config import BASE_DIR, muat_env

# Penyedia LLM: (nama, variabel lingkungan yang dicek, host untuk uji koneksi)
PENYEDIA = [
    ("claude", ("ANTHROPIC_API_KEY",), "api.anthropic.com"),
    ("gpt", ("OPENAI_API_KEY",), "api.openai.com"),
    ("gemini", ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "generativelanguage.googleapis.com"),
]
# nama paket pip -> nama modul untuk import
NAMA_IMPOR = {"python-dotenv": "dotenv", "anthropic": "anthropic", "pypdf": "pypdf", "tzdata": "tzdata"}


def kunci_valid(nilai: str | None) -> bool:
    """API key asli, bukan kosong / placeholder seperti 'sk-ant-...' atau 'isi_key_anda'."""
    v = (nilai or "").strip().strip('"\'')
    if len(v) < 12 or "..." in v or v.lower().startswith(("isi", "your", "xxx", "changeme")):
        return False
    return True


def siapkan_env(base: Path = BASE_DIR) -> str:
    """Pastikan .env ada: bila belum, salin dari .env.example lalu muat. Mengembalikan status singkat."""
    env, contoh = Path(base) / ".env", Path(base) / ".env.example"
    if env.exists():
        return "ada"
    if not contoh.exists():
        return "tidak-ada-contoh"
    try:
        shutil.copyfile(contoh, env)
    except OSError:
        return "gagal-salin"
    muat_env(env)
    return "dibuat"


def kunci_tersedia() -> list[tuple[str, str]]:
    """[(nama_penyedia, host)] untuk penyedia yang punya API key valid di lingkungan."""
    return [(n, h) for n, envs, h in PENYEDIA if any(kunci_valid(os.environ.get(e)) for e in envs)]


def ada_internet(host: str, timeout: float = 2.5) -> bool:
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return True
    except OSError:
        return False


def tentukan_mode(cek_internet: bool = True) -> tuple[bool, str]:
    """(pakai_multi, alasan). multi bila ada API key valid DAN host penyedianya terjangkau."""
    ada = kunci_tersedia()
    if not ada:
        return False, "API key belum diisi di .env"
    if cek_internet and not any(ada_internet(h) for _, h in ada):
        return False, "tidak ada koneksi internet ke penyedia LLM"
    return True, "API key: " + ", ".join(n for n, _ in ada)


def paket_kurang(base: Path = BASE_DIR) -> list[str]:
    """Baris requirements.txt yang modulnya belum bisa di-import (penanda platform sederhana didukung)."""
    req = Path(base) / "requirements.txt"
    if not req.exists():
        return []
    kurang = []
    for baris in req.read_text(encoding="utf-8").splitlines():
        baris = baris.split("#", 1)[0].strip()
        if not baris:
            continue
        spek, _, penanda = baris.partition(";")
        if "windows" in penanda.lower() and platform.system() != "Windows":
            continue
        nama = re.split(r"[<>=!~\[ ]", spek.strip(), maxsplit=1)[0]
        modul = NAMA_IMPOR.get(nama.lower(), nama.replace("-", "_"))
        if importlib.util.find_spec(modul) is None:
            kurang.append(spek.strip())
    return kurang


def pasang_dependensi(base: Path = BASE_DIR, diam: bool = False) -> bool:
    """pip install paket yang belum ada. True bila semuanya tersedia setelahnya (atau tak ada yang kurang)."""
    kurang = paket_kurang(base)
    if not kurang:
        return True
    if not diam:
        print("Memasang paket yang belum ada:", ", ".join(kurang))
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", *kurang],
                       check=False, timeout=600)
    except (OSError, subprocess.SubprocessError):
        pass
    sisa = paket_kurang(base)
    if sisa and not diam:
        print("Catatan: paket berikut belum terpasang (fitur terkait nonaktif, aplikasi tetap jalan):",
              ", ".join(sisa))
    return not sisa


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    siapkan_env()
    if "--pasang" in args:
        pasang_dependensi()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
