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
KB_PATH = Path(os.getenv("CHATBOT_KB_PATH", PKG_DIR / "data" / "knowledge_base.json"))
LOG_PATH = Path(os.getenv("CHATBOT_LOG_PATH", BASE_DIR / "logs" / "chat_log.jsonl"))

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

# --------------------------------------------------------------------------- #
# LLM
# --------------------------------------------------------------------------- #
LLM_MODEL = os.getenv("CHATBOT_LLM_MODEL", "claude-sonnet-5-5")
LLM_MAX_TOKENS = 700
LLM_TIMEOUT_DETIK = 30.0
LLM_MAX_RETRIES = 2
RIWAYAT_UNTUK_LLM = 2          # jumlah giliran sebelumnya yang dikirim ke LLM

# --------------------------------------------------------------------------- #
# Guardrail anti-halusinasi
# --------------------------------------------------------------------------- #
GROUNDING_MIN = 0.60           # min. porsi kata isi jawaban yang harus ada di konteks
KALIMAT_BERSITASI_MIN = 0.50   # min. porsi baris/paragraf substantif yang wajib bersitasi
KATA_MIN_KALIMAT_SUBSTANTIF = 4

FALLBACK = (
    "Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. "
    "Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat."
)
