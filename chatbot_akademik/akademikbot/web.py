"""
web.py  -  Antarmuka web AkademikBot (server bawaan Python, tanpa Flask/dependensi lain).

PENANGGUNG JAWAB: Anggota 4 (Router, CLI & Evaluasi)

Endpoint:
    GET  /              halaman chat
    GET  /api/health    status KB & LLM
    GET  /api/topik     daftar topik KB
    POST /api/chat      {"pesan": "...", "sesi": "<id opsional>"} -> balasan + id sesi
    GET  /api/menu      menu utama (tabel pilihan)
    POST /api/menu      {"jalur": ["jadwal", "3"], "sesi": "<id>"} -> layar menu berikutnya ATAU jawaban
    POST /api/reset     {"sesi": "<id>"} -> hapus riwayat sesi
    POST /feedback      {"nilai": "up"|"down", "pertanyaan": "...", "jawaban": "...", "mode": "kb"}
                        -> rating 👎 disimpan ke logs/feedback_negatif.jsonl (👍 hanya dicatat sebagai OK)

    POST /api/dokumen   {"sesi": "<id>", "nama": "edaran.pdf", "data": "<base64>"} -> pasang dokumen TXT/PDF
                        sementara sebagai konteks tanya-jawab sesi ini (maks. 2 MB)
    POST /api/dokumen/hapus {"sesi": "<id>"} -> lepas dokumen
    GET  /api/banner    pengingat kalender akademik (acara berlangsung / dalam 14 hari)

Balasan chat/menu memuat `opsi_cepat` (maks. 3 pertanyaan lanjutan, dari menu.SARAN_CEPAT) yang
ditampilkan klien sebagai tombol Quick Reply; mengetik angka 1/2/3 juga dipahami server.

Keamanan dasar: bind ke 127.0.0.1 secara default, ukuran body dibatasi, rate limit per IP,
jumlah & umur sesi dibatasi, dan klien selalu menampilkan teks dengan textContent (anti-XSS).
"""

from __future__ import annotations

import base64
import binascii
import importlib.util
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .config import BANNER_HARI, FEEDBACK_PATH, KB_PATH, LOG_AKTIF, MAKS_DOK_BYTES, MAKS_PANJANG_PERTANYAAN
from .dokumen import DokumenError
from .menu import HasilMenu, Layar
from .router import Balasan, Chatbot

STATIC = Path(__file__).resolve().parent / "static"
MAKS_BODY = 4096                 # byte
MAKS_BODY_FEEDBACK = 16384       # byte; memuat teks jawaban bot (jawaban jadwal bisa panjang)
MAKS_FB_PERTANYAAN = 1000        # karakter yang disimpan per rating
MAKS_FB_JAWABAN = 3000
MODE_VALID = {"kb", "llm", "fallback", "sapaan", "saran", "alat"}
JALUR_FEEDBACK = ("/feedback", "/api/feedback")
JALUR_DOKUMEN = ("/api/dokumen", "/api/dokumen/hapus")
MAKS_BODY_DOKUMEN = (MAKS_DOK_BYTES * 4) // 3 + 4096   # base64 membengkak ~33%


def batas_body(path: str) -> int:
    if path in JALUR_FEEDBACK:
        return MAKS_BODY_FEEDBACK
    return MAKS_BODY_DOKUMEN if path == "/api/dokumen" else MAKS_BODY
MAKS_SESI = 500
UMUR_SESI_DETIK = 60 * 60
RATE_MAKS = 30                   # permintaan chat
RATE_JENDELA = 60.0              # per detik, per IP


class SesiManager:
    """Satu Chatbot per sesi (riwayat terpisah), indeks TF-IDF & LLM dibagi bersama."""

    def __init__(self, dasar: Chatbot):
        self.dasar = dasar
        self._sesi: dict[str, tuple[Chatbot, float]] = {}
        self._kunci = threading.Lock()

    def ambil(self, sid: Optional[str]) -> tuple[str, Chatbot]:
        sekarang = time.time()
        with self._kunci:
            self._bersihkan(sekarang)
            if sid and sid in self._sesi:
                bot = self._sesi[sid][0]
            else:
                sid = secrets.token_urlsafe(12)
                bot = self.dasar.sesi_baru()
            self._sesi[sid] = (bot, sekarang)
            return sid, bot

    def hapus(self, sid: Optional[str]) -> None:
        with self._kunci:
            self._sesi.pop(sid or "", None)

    def _bersihkan(self, sekarang: float) -> None:
        for k in [k for k, (_, t) in self._sesi.items() if sekarang - t > UMUR_SESI_DETIK]:
            del self._sesi[k]
        while len(self._sesi) >= MAKS_SESI:           # buang yang paling lama tidak dipakai
            del self._sesi[min(self._sesi, key=lambda k: self._sesi[k][1])]


class RateLimiter:
    def __init__(self, maks: int = RATE_MAKS, jendela: float = RATE_JENDELA):
        self.maks, self.jendela = maks, jendela
        self._log: dict[str, deque] = defaultdict(deque)
        self._kunci = threading.Lock()

    def boleh(self, kunci: str) -> bool:
        sekarang = time.monotonic()
        with self._kunci:
            q = self._log[kunci]
            while q and sekarang - q[0] > self.jendela:
                q.popleft()
            if len(q) >= self.maks:
                return False
            q.append(sekarang)
            if len(self._log) > 5000:                  # cegah dict membengkak
                self._log = defaultdict(deque, {kunci: q})
            return True


class FeedbackLog:
    """Menyimpan rating negatif (👎) ke JSONL sebagai bahan evaluasi knowledge_base.json."""

    def __init__(self, path: Optional[Path]):
        self.path = Path(path) if path else None
        self._kunci = threading.Lock()

    def simpan(self, pertanyaan: str, jawaban: str, mode: str) -> bool:
        if self.path is None:
            return False
        baris = json.dumps({
            "waktu": datetime.now().isoformat(timespec="seconds"),
            "nilai": "negatif",
            "pertanyaan": pertanyaan[:MAKS_FB_PERTANYAAN],
            "jawaban": jawaban[:MAKS_FB_JAWABAN],
            "mode": mode if mode in MODE_VALID else "",
        }, ensure_ascii=False)
        try:
            with self._kunci:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(baris + "\n")
            return True
        except OSError:
            return False


def proses_feedback(log: FeedbackLog, data: dict) -> tuple[int, dict]:
    """Validasi payload /feedback; kembalikan (kode_http, json)."""
    nilai, tanya, jawab = data.get("nilai"), data.get("pertanyaan"), data.get("jawaban")
    if nilai not in ("up", "down"):
        return 400, {"error": "field 'nilai' harus 'up' atau 'down'"}
    if nilai == "up":
        return 200, {"ok": True, "tersimpan": False}
    if (not isinstance(tanya, str) or not tanya.strip()
            or not isinstance(jawab, str) or not jawab.strip()):
        return 400, {"error": "field 'pertanyaan' dan 'jawaban' wajib berupa teks"}
    mode = data.get("mode")
    ok = log.simpan(tanya.strip(), jawab.strip(), mode if isinstance(mode, str) else "")
    return 200, {"ok": True, "tersimpan": ok}


def banner_json(dasar: Chatbot) -> dict:
    """Pengingat kalender akademik untuk banner web (acara berlangsung / mulai dalam BANNER_HARI hari)."""
    kal = dasar.data.kalender if dasar.data else None
    if kal is None:
        return {"banner": [], "dummy": False}
    item = kal.banner(dasar.sekarang(), BANNER_HARI)
    return {"banner": [{"teks": s.ringkas(), "status": s.status, "hari": s.hari, "nama": s.acara.nama,
                        "tanggal": s.acara.teks_tanggal()} for s in item],
            "dummy": kal.dummy}


def proses_dokumen(bot: Chatbot, data: dict) -> tuple[int, dict]:
    """Validasi & pasang dokumen unggahan (base64) ke sesi."""
    nama, isi = data.get("nama"), data.get("data")
    if not isinstance(nama, str) or not nama.strip() or not isinstance(isi, str) or not isi:
        return 400, {"error": "field 'nama' dan 'data' (base64) wajib diisi"}
    try:
        mentah = base64.b64decode(isi, validate=True)
    except (binascii.Error, ValueError):
        return 400, {"error": "data bukan base64 yang valid"}
    try:
        return 200, {"ok": True, **bot.muat_dokumen(nama.strip()[:120], mentah)}
    except DokumenError as exc:
        return 400, {"error": str(exc)}


def layar_json(lay: Layar) -> dict:
    return {"judul": lay.judul, "jalur": lay.jalur, "kolom": list(lay.kolom), "petunjuk": lay.petunjuk,
            "opsi": [{"no": o.no, "label": o.label, "ket": o.ket, "jalur": o.jalur} for o in lay.opsi]}


def balasan_json(sid: str, b: Balasan, bot: Chatbot) -> dict:
    return {"sesi": sid, "jawaban": b.teks, "mode": b.mode, "skor": round(b.skor, 3),
            "sumber": b.sumber, "model": b.model, "percobaan": b.percobaan,
            "waktu_ms": round(b.waktu_ms, 1), "alasan": b.alasan, "semester": bot.semester,
            "opsi_cepat": b.opsi_cepat, "dipilih": b.dipilih, "kuis": b.kuis,
            "dokumen": bot.dokumen.nama if bot.dokumen else None}


def jalankan_menu(bot: Chatbot, sid: str, jalur: list) -> dict:
    """Satu langkah menu: kembalikan layar berikutnya atau jawaban (+ layar yang ditampilkan lagi)."""
    h: HasilMenu = bot.menu.buka(jalur)
    pesan = h.pesan
    if h.atur_semester is not None:
        bot.atur_semester(h.atur_semester)
    if h.entri_id:
        e = bot.entri_id[h.entri_id]
        d = {"tipe": "jawaban", "pertanyaan": e.pertanyaan, **balasan_json(sid, bot.jawab_entri(h.entri_id, dengan_opsi=True), bot)}
        lay = bot.menu.buka(h.balik).layar
        d["balik"] = layar_json(lay) if lay else None      # menu yang ditampilkan lagi setelah jawaban
        return d
    assert h.layar is not None
    return {"tipe": "layar", "sesi": sid, "pesan": pesan, "semester": bot.semester, **layar_json(h.layar)}


def buat_handler(sesi: SesiManager, limiter: RateLimiter,
                 feedback_path: Optional[Path] = FEEDBACK_PATH if LOG_AKTIF else None):
    halaman = (STATIC / "index.html").read_bytes()
    dasar = sesi.dasar
    feedback = FeedbackLog(feedback_path)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AkademikBot"
        sys_version = ""

        # -- util ------------------------------------------------------------ #
        def _kirim(self, kode: int, isi: bytes, tipe: str) -> None:
            self.send_response(kode)
            self.send_header("Content-Type", tipe)
            self.send_header("Content-Length", str(len(isi)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                             "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(isi)

        def _json(self, kode: int, data: dict) -> None:
            self._kirim(kode, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8")

        def _body(self, maks: int = MAKS_BODY) -> Optional[dict]:
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return None
            if n <= 0 or n > maks:
                return None
            try:
                data = json.loads(self.rfile.read(n).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            return data if isinstance(data, dict) else None

        # -- rute ------------------------------------------------------------ #
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._kirim(200, halaman, "text/html; charset=utf-8")
            elif self.path == "/api/health":
                self._json(200, {"status": "ok", "entri_kb": len(dasar.index.entri),
                                 "llm": dasar.llm.tersedia, "model": dasar.llm.model,
                                 "llm_error": dasar.llm.error,
                                 "pdf": importlib.util.find_spec("pypdf") is not None,
                                 "maks_dokumen_mb": MAKS_DOK_BYTES // (1024 * 1024)})
            elif self.path == "/api/banner":
                self._json(200, banner_json(dasar))
            elif self.path == "/api/menu":
                self._json(200, {"tipe": "layar", **layar_json(dasar.menu.buka([]).layar)})  # type: ignore[arg-type]
            elif self.path == "/api/topik":
                self._json(200, {"topik": [
                    {"kategori": e.kategori, "pertanyaan": e.pertanyaan}
                    for e in dasar.index.entri]})
            else:
                self._json(404, {"error": "tidak ditemukan"})

        def do_POST(self) -> None:  # noqa: N802
            data = self._body(batas_body(self.path))
            if data is None:
                return self._json(400, {"error": "body JSON tidak valid atau terlalu besar"})
            if self.path in JALUR_FEEDBACK:
                if not limiter.boleh(self.client_address[0]):
                    return self._json(429, {"error": "Terlalu banyak permintaan, coba sebentar lagi."})
                kode, isi = proses_feedback(feedback, data)
                return self._json(kode, isi)
            if self.path in JALUR_DOKUMEN:
                if not limiter.boleh(self.client_address[0]):
                    return self._json(429, {"error": "Terlalu banyak permintaan, coba sebentar lagi."})
                sid_in = data.get("sesi")
                sid, bot = sesi.ambil(sid_in if isinstance(sid_in, str) else None)
                if self.path == "/api/dokumen/hapus":
                    bot.hapus_dokumen()
                    return self._json(200, {"ok": True, "sesi": sid})
                kode, isi = proses_dokumen(bot, data)
                return self._json(kode, {**isi, "sesi": sid})
            if self.path == "/api/reset":
                sesi.hapus(str(data.get("sesi", "")))
                return self._json(200, {"ok": True})
            if self.path == "/api/menu":
                if not limiter.boleh(self.client_address[0]):
                    return self._json(429, {"error": "Terlalu banyak permintaan, coba sebentar lagi."})
                jalur = data.get("jalur", [])
                if (not isinstance(jalur, list) or len(jalur) > 4
                        or not all(isinstance(x, str) and len(x) <= 40 for x in jalur)):
                    return self._json(400, {"error": "field 'jalur' harus daftar teks pendek"})
                sid_in = data.get("sesi")
                sid, bot = sesi.ambil(sid_in if isinstance(sid_in, str) else None)
                return self._json(200, jalankan_menu(bot, sid, jalur))
            if self.path != "/api/chat":
                return self._json(404, {"error": "tidak ditemukan"})

            if not limiter.boleh(self.client_address[0]):
                return self._json(429, {"error": "Terlalu banyak permintaan, coba sebentar lagi."})
            pesan = data.get("pesan")
            if not isinstance(pesan, str) or not pesan.strip():
                return self._json(400, {"error": "field 'pesan' wajib berupa teks"})
            sid_in = data.get("sesi")
            sid, bot = sesi.ambil(sid_in if isinstance(sid_in, str) else None)
            b = bot.tanya(pesan[: MAKS_PANJANG_PERTANYAAN * 2])
            self._json(200, balasan_json(sid, b, bot))

        def log_message(self, fmt: str, *args) -> None:   # log akses diringkas
            pass

    return Handler


def _buat_server(host: str, port: int, handler, cadangan: int = 10) -> tuple[ThreadingHTTPServer, int]:
    """Bind ke `port`; bila sedang dipakai program lain, coba port berikutnya (anti-error)."""
    galat: Optional[OSError] = None
    for p in range(port, port + cadangan + 1):
        try:
            return ThreadingHTTPServer((host, p), handler), p
        except OSError as exc:
            galat = exc
    raise galat or OSError("tidak ada port kosong")


def jalankan_web(host: str = "127.0.0.1", port: int = 8000, offline: bool = False,
                 kb_path: Path = KB_PATH, llm=None, buka_browser: bool = False) -> None:
    dasar = Chatbot(kb_path, offline=offline, llm=llm)
    server, port_pakai = _buat_server(host, port, buat_handler(SesiManager(dasar), RateLimiter()))
    if port_pakai != port:
        print(f"Port {port} sedang dipakai, memakai port {port_pakai}.")
    port = port_pakai
    llm = f"aktif ({dasar.llm.model})" if dasar.llm.tersedia else f"nonaktif - {dasar.llm.error}"
    print(f"AkademikBot web: http://{host}:{port}  | KB {len(dasar.index.entri)} entri | LLM {llm}")
    if buka_browser:
        import webbrowser
        url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}"
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print("Tekan Ctrl+C untuk menghentikan server.")
    if host not in ("127.0.0.1", "localhost"):
        print("PERINGATAN: server terbuka untuk jaringan; tambahkan autentikasi/HTTPS di depannya.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()
