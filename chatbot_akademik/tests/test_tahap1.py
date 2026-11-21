"""Tes Tahap 1: .env otomatis, SARAN_CEPAT (pilihan 1/2/3), feedback 👍/👎, dan halaman web."""
import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from akademikbot.cli import cetak_balasan, jalankan_cli
from akademikbot.config import muat_env
from akademikbot.menu import SARAN_CEPAT, pilih_saran, saran_cepat
from akademikbot.router import Chatbot
from akademikbot.web import MAKS_FB_JAWABAN, RateLimiter, SesiManager, buat_handler


def bot():
    return Chatbot(offline=True, log_path=None)


class TestMuatEnv(unittest.TestCase):
    def test_memuat_env_tanpa_menimpa_variabel_yang_sudah_ada(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"TES_AKB_LAMA": "dari-terminal"}):
            p = Path(d) / ".env"
            p.write_text("TES_AKB_BARU=halo  # komentar\nTES_AKB_LAMA=dari-env\n", encoding="utf-8")
            self.assertTrue(muat_env(p))
            self.assertEqual(os.environ["TES_AKB_BARU"], "halo")
            self.assertEqual(os.environ["TES_AKB_LAMA"], "dari-terminal")   # perintah manual menang
            os.environ.pop("TES_AKB_BARU", None)

    def test_env_tidak_ada_tidak_error(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(muat_env(Path(d) / "tidak-ada.env"))


class TestSaranCepat(unittest.TestCase):
    def test_semua_kata_kunci_yang_diminta_ada_dan_berisi_tiga_opsi(self):
        for k in ("jadwal", "krs", "skripsi", "cuti", "ujian", "uts", "uas"):
            self.assertEqual(len(SARAN_CEPAT[k]), 3, k)

    def test_cocok_kata_utuh_saja(self):
        self.assertEqual(len(saran_cepat("bagaimana cara isi KRS?")), 3)
        self.assertEqual(saran_cepat("luas ruangan"), [])     # 'uas' di dalam 'luas' bukan kata kunci
        self.assertEqual(saran_cepat(""), [])

    def test_tidak_menyarankan_pertanyaan_yang_sama(self):
        q = SARAN_CEPAT["uts"][0]                  # mengandung kata 'uts' dan 'uas'
        hasil = saran_cepat(q)
        self.assertNotIn(q, hasil)
        self.assertTrue(hasil)                     # opsi lain dari kata kunci yang sama tetap muncul
        self.assertLessEqual(len(saran_cepat("jadwal uts uas krs cuti")), 3)

    def test_setiap_opsi_menghasilkan_jawaban_bukan_fallback(self):
        """Tidak ada opsi mati: semua pertanyaan di SARAN_CEPAT dikenali KB."""
        b = bot()
        for kunci, daftar in SARAN_CEPAT.items():
            for q in daftar:
                self.assertNotEqual(b.tanya(q).mode, "fallback", f"{kunci}: {q}")

    def test_pilih_saran(self):
        o = ["a", "b", "c"]
        self.assertEqual(pilih_saran("1", o), "a")
        self.assertEqual(pilih_saran(" 3. ", o), "c")
        self.assertEqual(pilih_saran("2)", o), "b")
        self.assertIsNone(pilih_saran("4", o))
        self.assertIsNone(pilih_saran("0", o))
        self.assertIsNone(pilih_saran("12", o))
        self.assertIsNone(pilih_saran("satu", o))
        self.assertIsNone(pilih_saran("1", []))


class TestAngkaDiChatbot(unittest.TestCase):
    def test_angka_memilih_opsi_dari_balasan_terakhir(self):
        b = bot()
        r = b.tanya("Bagaimana cara mengisi KRS?")
        self.assertEqual(r.mode, "kb")
        self.assertEqual(r.opsi_cepat, SARAN_CEPAT["krs"])
        r2 = b.tanya("2")
        self.assertEqual(r2.dipilih, SARAN_CEPAT["krs"][1])
        self.assertEqual(r2.mode, "kb")
        self.assertEqual(b.riwayat[-1][0], SARAN_CEPAT["krs"][1])   # riwayat memuat pertanyaan lengkap

    def test_angka_tanpa_opsi_diperlakukan_seperti_biasa(self):
        b = bot()
        r = b.tanya("2")
        self.assertEqual((r.dipilih, r.mode), ("", "fallback"))

    def test_opsi_hilang_setelah_pertanyaan_tanpa_opsi(self):
        b = bot()
        b.tanya("Bagaimana cara mengisi KRS?")
        b.tanya("Bagaimana cara masuk ke e-learning?")            # tanpa kata kunci SARAN_CEPAT
        self.assertEqual(b.tanya("1").dipilih, "")

    def test_sapaan_dan_fallback_tanpa_opsi(self):
        b = bot()
        self.assertEqual(b.tanya("halo").opsi_cepat, [])
        self.assertEqual(b.tanya("siapa presiden Indonesia pertama?").opsi_cepat, [])

    def test_menu_cli_tidak_menyisakan_opsi_basi(self):
        b = bot()
        b.tanya("Bagaimana cara mengisi KRS?")
        r = b.jawab_entri("krs-01")                              # default: tanpa opsi (angka = baris tabel)
        self.assertEqual(r.opsi_cepat, [])
        self.assertEqual(b.tanya("1").dipilih, "")
        self.assertTrue(b.jawab_entri("krs-01", dengan_opsi=True).opsi_cepat)   # perilaku web


class TestCLI(unittest.TestCase):
    def test_cetak_balasan_menampilkan_opsi_bernomor(self):
        r = bot().tanya("Bagaimana cara mengisi KRS?")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cetak_balasan(r)
        out = buf.getvalue()
        for i, o in enumerate(r.opsi_cepat, 1):
            self.assertIn(f"{i}. {o}", out)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cetak_balasan(r, tampil_opsi=False)
        self.assertNotIn("Pertanyaan lanjutan", buf.getvalue())

    def test_alur_cli_mengetik_angka(self):
        buf = io.StringIO()
        with mock.patch("builtins.input", side_effect=["Bagaimana cara mengisi KRS?", "1", "/keluar"]), \
                contextlib.redirect_stdout(buf):
            jalankan_cli(bot())
        out = buf.getvalue()
        self.assertIn("memilih pilihan cepat: " + SARAN_CEPAT["krs"][0], out)
        self.assertIn("SKS", out)


class TestWebTahap1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fb = Path(cls.tmp.name) / "logs" / "feedback_negatif.jsonl"
        dasar = Chatbot(offline=True, log_path=None)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), buat_handler(
            SesiManager(dasar), RateLimiter(maks=200), feedback_path=cls.fb))
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def _post(self, path, data):
        req = urllib.request.Request(self.url + path, data=data if isinstance(data, bytes)
                                     else json.dumps(data).encode(), method="POST")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def _baris_feedback(self):
        if not self.fb.exists():
            return []
        return [json.loads(x) for x in self.fb.read_text(encoding="utf-8").splitlines() if x.strip()]

    def test_chat_memuat_opsi_cepat_dan_angka_dipahami(self):
        kode, d = self._post("/api/chat", {"pesan": "Bagaimana cara mengisi KRS?"})
        self.assertEqual(kode, 200)
        self.assertEqual(d["opsi_cepat"], SARAN_CEPAT["krs"])
        kode, d2 = self._post("/api/chat", {"pesan": "3", "sesi": d["sesi"]})
        self.assertEqual(d2["dipilih"], SARAN_CEPAT["krs"][2])
        self.assertEqual(d2["mode"], "kb")

    def test_sapaan_tanpa_opsi_cepat(self):
        self.assertEqual(self._post("/api/chat", {"pesan": "halo"})[1]["opsi_cepat"], [])

    def test_jawaban_menu_web_memuat_opsi_cepat(self):
        kode, d = self._post("/api/menu", {"jalur": ["faq", "1"]})   # layar kategori
        self.assertEqual(d["tipe"], "layar")
        kode, d = self._post("/api/menu", {"jalur": ["kurikulum", "3"]})
        self.assertEqual(d["tipe"], "jawaban")
        self.assertIn("opsi_cepat", d)

    def test_feedback_negatif_disimpan(self):
        sebelum = len(self._baris_feedback())
        kode, d = self._post("/feedback", {"nilai": "down", "pertanyaan": "Kapan UTS?",
                                           "jawaban": "Lihat kalender akademik.", "mode": "kb"})
        self.assertEqual((kode, d), (200, {"ok": True, "tersimpan": True}))
        baris = self._baris_feedback()
        self.assertEqual(len(baris), sebelum + 1)
        self.assertEqual(baris[-1]["pertanyaan"], "Kapan UTS?")
        self.assertEqual(baris[-1]["jawaban"], "Lihat kalender akademik.")
        self.assertEqual((baris[-1]["nilai"], baris[-1]["mode"]), ("negatif", "kb"))
        self.assertIn("waktu", baris[-1])

    def test_feedback_positif_tidak_disimpan(self):
        sebelum = len(self._baris_feedback())
        kode, d = self._post("/api/feedback", {"nilai": "up"})      # alias /api/feedback
        self.assertEqual((kode, d["tersimpan"]), (200, False))
        self.assertEqual(len(self._baris_feedback()), sebelum)

    def test_feedback_input_buruk(self):
        self.assertEqual(self._post("/feedback", {"nilai": "mungkin"})[0], 400)
        self.assertEqual(self._post("/feedback", {"nilai": "down"})[0], 400)
        self.assertEqual(self._post("/feedback", {"nilai": "down", "pertanyaan": "a", "jawaban": 5})[0], 400)
        self.assertEqual(self._post("/feedback", b"bukan json")[0], 400)
        self.assertEqual(self._post("/feedback", b"x" * 17000)[0], 400)

    def test_feedback_jawaban_panjang_dipotong_dan_mode_asing_dikosongkan(self):
        kode, _ = self._post("/feedback", {"nilai": "down", "pertanyaan": "q", "mode": "<script>",
                                           "jawaban": "j" * 8000})
        self.assertEqual(kode, 200)                 # > 4096 byte tetap diterima khusus /feedback
        b = self._baris_feedback()[-1]
        self.assertEqual(len(b["jawaban"]), MAKS_FB_JAWABAN)
        self.assertEqual(b["mode"], "")

    def test_feedback_tanpa_jalur_log_tidak_menulis(self):
        dasar = Chatbot(offline=True, log_path=None)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), buat_handler(
            SesiManager(dasar), RateLimiter(maks=50), feedback_path=None))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{srv.server_address[1]}/feedback", method="POST",
                data=json.dumps({"nilai": "down", "pertanyaan": "q", "jawaban": "j"}).encode())
            with urllib.request.urlopen(req) as r:
                self.assertEqual(json.loads(r.read())["tersimpan"], False)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_halaman_memuat_fitur_baru(self):
        with urllib.request.urlopen(self.url + "/") as r:
            html = r.read().decode("utf-8")
        for kata in ("Unduh Ringkasan Chat", "/feedback", "opsi_cepat", "👍", "👎", '<option value="md">',
                     '<option value="txt">'):
            self.assertIn(kata, html)


if __name__ == "__main__":
    unittest.main()
