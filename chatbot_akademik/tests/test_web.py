"""Tes antarmuka web (Anggota 4): sesi, rate limit, dan endpoint HTTP sungguhan."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from akademikbot.config import KB_PATH
from akademikbot.kb_loader import muat_kb
from akademikbot.router import Chatbot
from akademikbot.web import RateLimiter, SesiManager, buat_handler


class TestSesi(unittest.TestCase):
    def test_riwayat_terpisah_antar_sesi(self):
        dasar = Chatbot(offline=True, log_path=None)
        m = SesiManager(dasar)
        s1, b1 = m.ambil(None)
        s2, b2 = m.ambil(None)
        self.assertNotEqual(s1, s2)
        b1.tanya("bagaimana cara mengisi KRS?")
        self.assertEqual(len(b1.riwayat), 1)
        self.assertEqual(len(b2.riwayat), 0)
        self.assertIs(b1.index, b2.index)            # indeks dibagi, tidak dimuat ulang
        self.assertIs(m.ambil(s1)[1], b1)            # id yang sama -> bot yang sama

    def test_hapus_sesi(self):
        m = SesiManager(Chatbot(offline=True, log_path=None))
        s, b = m.ambil(None)
        m.hapus(s)
        self.assertIsNot(m.ambil(s)[1], b)

    def test_rate_limiter(self):
        r = RateLimiter(maks=3, jendela=60)
        self.assertEqual([r.boleh("ip") for _ in range(4)], [True, True, True, False])
        self.assertTrue(r.boleh("ip-lain"))


class TestHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dasar = Chatbot(offline=True, log_path=None)
        cls.jumlah_entri = len(dasar.index.entri)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0),
                                      buat_handler(SesiManager(dasar), RateLimiter(maks=100)))
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _post(self, path, data):
        req = urllib.request.Request(self.url + path, data=data if isinstance(data, bytes)
                                     else json.dumps(data).encode(), method="POST")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_halaman_dan_health(self):
        with urllib.request.urlopen(self.url + "/") as r:
            self.assertIn(b"AkademikBot", r.read())
            self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        with urllib.request.urlopen(self.url + "/api/health") as r:
            self.assertEqual(json.loads(r.read())["entri_kb"], self.jumlah_entri)

    def test_menu_http(self):
        with urllib.request.urlopen(self.url + "/api/menu") as r:
            self.assertEqual(len(json.loads(r.read())["opsi"]), 5)
        kode, d = self._post("/api/menu", {"jalur": ["kurikulum", "3"]})
        self.assertEqual((kode, d["tipe"]), (200, "jawaban"))
        self.assertIn("Sistem Operasi", d["jawaban"])
        kode, d2 = self._post("/api/menu", {"jalur": ["semester", "3"], "sesi": d["sesi"]})
        self.assertEqual(d2["semester"], 3)
        kode, d3 = self._post("/api/chat", {"pesan": "jadwal kuliah saya", "sesi": d["sesi"]})
        self.assertIn("Jadwal kuliah semester 3", d3["jawaban"])
        self.assertEqual(self._post("/api/menu", {"jalur": "bukan-list"})[0], 400)
        self.assertEqual(self._post("/api/menu", {"jalur": ["a"] * 9})[0], 400)

    def test_chat(self):
        kode, d = self._post("/api/chat", {"pesan": "Bagaimana cara mengisi KRS?"})
        self.assertEqual(kode, 200)
        self.assertEqual(d["mode"], "kb")
        self.assertTrue(d["sesi"])

    def test_input_buruk(self):
        self.assertEqual(self._post("/api/chat", b"bukan json")[0], 400)
        self.assertEqual(self._post("/api/chat", {"pesan": "   "})[0], 400)
        self.assertEqual(self._post("/api/chat", {"pesan": 123})[0], 400)
        self.assertEqual(self._post("/api/chat", b"x" * 5000)[0], 400)
        self.assertEqual(self._post("/api/tidakada", {"a": 1})[0], 404)


if __name__ == "__main__":
    unittest.main()
