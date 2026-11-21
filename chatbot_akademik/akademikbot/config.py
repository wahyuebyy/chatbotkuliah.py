"""
config.py  -  Konfigurasi terpusat AkademikBot.

PENANGGUNG JAWAB: Anggota 1 (Data & Knowledge Base)

Semua angka ambang (threshold) dan pengaturan ada di sini supaya mudah di-tuning
tanpa menyentuh logika program. Hasil tuning sebaiknya dicatat di laporan
(lihat evaluasi/jalankan_evaluasi.py).
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Lokasi berkas
# --------------------------------------------------------------------------- #
PKG_DIR = Path(__file__).resolve().parent
BASE_DIR = PKG_DIR.parent


def muat_env(path: Path | None = None) -> bool:
    """Muat berkas .env (bila ada) ke os.environ memakai python-dotenv.

    - Variabel yang SUDAH diatur di lingkungan tidak ditimpa (override=False), jadi perintah
      manual seperti `$env:ANTHROPIC_API_KEY=...` tetap menang atas isi .env.
    - Bila python-dotenv belum terpasang atau .env tidak ada, fungsi diam saja (mode --offline
      tetap jalan tanpa paket apa pun). Mengembalikan True bila ada .env yang berhasil dimuat.
    """
    path = Path(path) if path else BASE_DIR / ".env"
    if not path.is_file():
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    return bool(load_dotenv(path, override=False))


# Harus dipanggil SEBELUM os.getenv(...) di bawah, supaya nilai dari .env ikut terbaca.
muat_env()

KB_PATH = Path(os.getenv("CHATBOT_KB_PATH", PKG_DIR / "data" / "knowledge_base.json"))
DATA_DIR = Path(os.getenv("CHATBOT_DATA_DIR", PKG_DIR / "data"))   # kurikulum.json, jadwal.csv, dst.
LOG_PATH = Path(os.getenv("CHATBOT_LOG_PATH", BASE_DIR / "logs" / "chat_log.jsonl"))
FEEDBACK_PATH = Path(os.getenv("CHATBOT_FEEDBACK_PATH", BASE_DIR / "logs" / "feedback_negatif.jsonl"))

# --------------------------------------------------------------------------- #
# Identitas
# --------------------------------------------------------------------------- #
NAMA_BOT = "AkademikBot"
NAMA_PRODI = "Program Studi Informatika"

# --------------------------------------------------------------------------- #
# Ambang TF-IDF / router
# --------------------------------------------------------------------------- #
THRESHOLD_SANGAT_YAKIN = 0.55  # skor >= ini: jawab dari KB walau ada kata "kompleks" yang lemah
THRESHOLD_YAKIN = 0.40         # skor >= ini: jawab langsung dari KB (jika pertanyaan sederhana)
THRESHOLD_MIRIP = 0.12         # skor >= ini: cukup relevan untuk jadi konteks LLM
CAKUPAN_MIN = 0.60             # min. porsi kata pertanyaan yang dikenali KB (anti salah-topik)
TOPIK_TAMBAHAN_MIN = 0.20      # entri lain dianggap "topik kedua" jika membawa >= 20% kata unik
TOPIK_RASIO_SKOR_MIN = 0.40    # ...dan skornya minimal 40% dari skor entri teratas
TOP_K = 3                      # jumlah potongan KB yang diberikan ke LLM
MAKS_PANJANG_PERTANYAAN = 500  # karakter; sisanya dipotong (batasi biaya & prompt injection)
MAKS_KATA_PERTANYAAN_SEDERHANA = 18

# Koreksi typo (difflib) untuk kata di luar kosakata KB
TYPO_CUTOFF = 0.75             # kemiripan minimum (0..1); makin tinggi makin hati-hati
TYPO_PANJANG_MIN = 5           # kata lebih pendek dari ini tidak dikoreksi

# --------------------------------------------------------------------------- #
# Sesi & log
# --------------------------------------------------------------------------- #
MAKS_RIWAYAT = 50              # riwayat per sesi yang disimpan di memori
LOG_AKTIF = os.getenv("CHATBOT_LOG", "1") not in ("0", "false", "off", "no")

# --------------------------------------------------------------------------- #
# LLM
# --------------------------------------------------------------------------- #
LLM_MODEL = os.getenv("CHATBOT_LLM_MODEL", "claude-sonnet-5-5")
LLM_MAX_TOKENS = 700
LLM_TIMEOUT_DETIK = 30.0
LLM_MAX_RETRIES = 2
# Multi-model (orchestrator): nama model bisa diganti lewat variabel lingkungan.
# Pastikan nama model masih berlaku di dashboard penyedia masing-masing sebelum dipakai.
LLM_MODEL_GPT = os.getenv("CHATBOT_GPT_MODEL", "gpt-4o-mini")
LLM_MODEL_GEMINI = os.getenv("CHATBOT_GEMINI_MODEL", "gemini-2.5-flash")
LLM_URUTAN_DEFAULT = ["claude", "gpt", "gemini"]
# Urutan model per alasan rute dari router. Model berikutnya = cadangan (failover).
LLM_RUTE = {
    "multitopik": ["claude", "gemini", "gpt"],             # gabungkan banyak potongan KB
    "pertanyaan_kompleks": ["gpt", "claude", "gemini"],    # perbandingan / penalaran
    "skor_sedang": ["gemini", "claude", "gpt"],            # maksud kurang jelas
    "skor_sedang_lemah": ["gemini", "claude", "gpt"],
    "dokumen": ["claude", "gemini", "gpt"],                # tanya-jawab dokumen unggahan
}
# Verifikasi silang: model LAIN memeriksa apakah jawaban didukung konteks (biaya +1 panggilan).
LLM_VERIFIKASI = os.getenv("CHATBOT_VERIFIKASI", "0") in ("1", "true", "on", "yes")
RIWAYAT_UNTUK_LLM = 2          # jumlah giliran sebelumnya yang dikirim ke LLM

# --------------------------------------------------------------------------- #
# Guardrail anti-halusinasi
# --------------------------------------------------------------------------- #
GROUNDING_MIN = 0.60           # min. porsi kata isi jawaban yang harus ada di konteks
KALIMAT_BERSITASI_MIN = 0.50   # min. porsi baris/paragraf substantif yang wajib bersitasi
KATA_MIN_KALIMAT_SUBSTANTIF = 4

# --------------------------------------------------------------------------- #
# Alat akademik, dokumen unggahan & kuis (Tahap A)
# --------------------------------------------------------------------------- #
MAKS_SKS_SEMESTER = 24         # batas atas simulasi KRS ("cek sks")
BANNER_HARI = 14               # banner pengingat: acara kalender yang jatuh dalam N hari ke depan
MAKS_DOK_BYTES = 2 * 1024 * 1024    # ukuran berkas unggahan (TXT/PDF)
MAKS_DOK_KARAKTER = 80_000          # teks yang disimpan per dokumen
MAKS_DOK_HALAMAN_PDF = 60
UKURAN_POTONGAN_DOK = 700           # karakter per potongan (chunk) dokumen
KUIS_DEFAULT = 3
KUIS_MAKS = 8
LLM_MAX_TOKENS_KUIS = 2000

FALLBACK = (
    "Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. "
    "Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat."
)
