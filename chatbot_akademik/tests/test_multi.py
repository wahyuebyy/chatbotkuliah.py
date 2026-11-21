"""Tes multi-model (Anggota 3/4): adaptor Claude/GPT/Gemini, orchestrator, failover, verifikasi."""
import os
import unittest
from unittest import mock

from akademikbot.llm_demo import DemoProvider
from akademikbot.llm_orchestrator import LLMOrchestrator, buat_llm_multi, buat_llm_multi_demo
from akademikbot.llm_providers import (ClaudeProvider, GeminiProvider, GPTProvider,
                                       ProviderError)
from akademikbot.router import Chatbot

MAJEMUK = "Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti?"
KOMPLEKS = "Kalau dosen tidak hadir dan presensi saya kurang dari batas, apakah masih boleh ikut UAS?"
SISTEM, PESAN = "sistem", [{"role": "user", "content": "halo"}, {"role": "assistant", "content": "hai"},
                           {"role": "user", "content": "tanya"}]


class Rekam:
    """Transport palsu: merekam permintaan, mengembalikan respons yang ditentukan."""
    def __init__(self, respons):
        self.respons, self.panggilan = respons, []

    def __call__(self, url, headers, body, timeout):
        self.panggilan.append((url, headers, body))
        return self.respons


class TestAdaptor(unittest.TestCase):
    def test_claude(self):
        t = Rekam({"content": [{"type": "text", "text": " jawab [S1] "}]})
        self.assertEqual(ClaudeProvider("kunci", "m1", t).generate(SISTEM, PESAN), "jawab [S1]")
        url, h, b = t.panggilan[0]
        self.assertIn("anthropic.com", url)
        self.assertEqual(h["x-api-key"], "kunci")
        self.assertEqual(b["system"], SISTEM)
        self.assertEqual(b["messages"], PESAN)

    def test_gpt(self):
        t = Rekam({"choices": [{"message": {"content": "ok"}}]})
        self.assertEqual(GPTProvider("kunci", "m2", t).generate(SISTEM, PESAN), "ok")
        url, h, b = t.panggilan[0]
        self.assertIn("openai.com", url)
        self.assertEqual(h["Authorization"], "Bearer kunci")
        self.assertEqual(b["messages"][0], {"role": "system", "content": SISTEM})
        self.assertEqual(len(b["messages"]), 4)

    def test_gemini_peran_dan_url(self):
        t = Rekam({"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]})
        self.assertEqual(GeminiProvider("kunci", "gem-x", t).generate(SISTEM, PESAN), "ab")
        url, h, b = t.panggilan[0]
        self.assertTrue(url.endswith("models/gem-x:generateContent"))
        self.assertEqual(h["x-goog-api-key"], "kunci")
        self.assertEqual([c["role"] for c in b["contents"]], ["user", "model", "user"])
        self.assertEqual(b["systemInstruction"]["parts"][0]["text"], SISTEM)
        self.assertNotIn("kunci", str(b))             # key tidak bocor ke body

    def test_respons_kosong_jadi_error(self):
        with self.assertRaises(ProviderError):
            GeminiProvider("k", "m", Rekam({"candidates": []})).generate(SISTEM, PESAN)
        with self.assertRaises(ProviderError):
            GPTProvider("k", "m", Rekam({})).generate(SISTEM, PESAN)

    def test_tanpa_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            p = ClaudeProvider()
            self.assertFalse(p.tersedia)
            with self.assertRaises(ProviderError):
                p.generate(SISTEM, PESAN)

    def test_key_dari_lingkungan(self):
        env = {"OPENAI_API_KEY": "o", "GOOGLE_API_KEY": "g"}
        with mock.patch.dict(os.environ, env, clear=True):
            o = buat_llm_multi()
            self.assertEqual(sorted(p.nama for p in o.aktif), ["gemini", "gpt"])
            self.assertTrue(o.tersedia)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(buat_llm_multi().tersedia)


class TestOrchestrator(unittest.TestCase):
    def test_urutan_per_alasan_dan_cadangan(self):
        o = buat_llm_multi_demo("baik")
        self.assertEqual([p.nama for p in o.urutan("multitopik")], ["claude", "gemini", "gpt"])
        self.assertEqual([p.nama for p in o.urutan("pertanyaan_kompleks")], ["gpt", "claude", "gemini"])
        self.assertEqual([p.nama for p in o.urutan("tak_dikenal")], ["claude", "gpt", "gemini"])

    def test_model_pertama_sesuai_rute(self):
        b = Chatbot(llm=buat_llm_multi_demo("baik"), log_path=None)
        r1, r2 = b.tanya(MAJEMUK), b.tanya(KOMPLEKS)
        self.assertEqual((r1.mode, r1.model), ("llm", "claude"))
        self.assertEqual((r2.mode, r2.model), ("llm", "gpt"))

    def test_failover_saat_guardrail_menolak(self):
        r = Chatbot(llm=buat_llm_multi_demo("halusinasi"), log_path=None).tanya(KOMPLEKS)
        self.assertEqual((r.mode, r.model), ("llm", "claude"))
        self.assertTrue(r.percobaan[0].startswith("gpt:guardrail:angka_tidak_ada_di_konteks"))
        self.assertEqual(r.percobaan[-1], "claude:ok")

    def test_semua_model_ditolak_jadi_fallback(self):
        o = LLMOrchestrator({n: DemoProvider(n, "halusinasi") for n in ("claude", "gpt", "gemini")})
        r = Chatbot(llm=o, log_path=None).tanya(MAJEMUK)
        self.assertEqual(r.mode, "fallback")
        self.assertEqual(len(r.percobaan), 3)

    def test_failover_saat_error_jaringan(self):
        def rusak(*a):
            raise ProviderError("HTTP 500")
        o = LLMOrchestrator({
            "claude": ClaudeProvider("k", "m", rusak),
            "gpt": DemoProvider("gpt", "baik"), "gemini": DemoProvider("gemini", "baik")})
        r = Chatbot(llm=o, log_path=None).tanya(MAJEMUK)
        self.assertEqual((r.mode, r.model), ("llm", "gemini"))   # rute multitopik: claude > gemini > gpt
        self.assertEqual(r.percobaan[0], "claude:error:ProviderError")

    def test_semua_error_turun_ke_jawaban_kb(self):
        def rusak(*a):
            raise ProviderError("HTTP 500")
        o = LLMOrchestrator({n: cls("k", "m", rusak) for n, cls in
                             (("claude", ClaudeProvider), ("gpt", GPTProvider), ("gemini", GeminiProvider))})
        r = Chatbot(llm=o, log_path=None).tanya(MAJEMUK)
        self.assertEqual(r.mode, "kb")                 # cadangan: jawaban KB apa adanya
        self.assertIn("tanpa_llm", r.alasan)

    def test_tanpa_model_tersedia(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = Chatbot(llm=buat_llm_multi(), log_path=None).tanya(MAJEMUK)
        self.assertNotEqual(r.mode, "llm")             # tidak crash, turun ke KB/saran

    def test_verifikasi_silang_menolak(self):
        # penjawab (claude) lolos guardrail, tetapi verifikator (gpt) bilang TIDAK
        o = LLMOrchestrator({"claude": DemoProvider("claude", "baik"),
                             "gpt": DemoProvider("gpt", "tanpa_sitasi")}, verifikasi=True)
        r = Chatbot(llm=o, log_path=None).tanya(MAJEMUK)
        self.assertIn("claude:verifikasi_gagal", r.percobaan)

    def test_verifikasi_silang_lolos(self):
        o = LLMOrchestrator({"claude": DemoProvider("claude", "baik"),
                             "gpt": DemoProvider("gpt", "baik")}, verifikasi=True)
        r = Chatbot(llm=o, log_path=None).tanya(MAJEMUK)
        self.assertEqual((r.mode, r.model), ("llm", "claude"))
        self.assertIn("gpt:verifikator", r.percobaan)

    def test_verifikasi_dilewati_bila_hanya_satu_model(self):
        o = LLMOrchestrator({"claude": DemoProvider("claude", "baik")}, verifikasi=True)
        r = Chatbot(llm=o, log_path=None).tanya(MAJEMUK)
        self.assertEqual(r.mode, "llm")

    def test_pertanyaan_sederhana_tidak_memanggil_model(self):
        p = DemoProvider("claude", "baik")
        Chatbot(llm=LLMOrchestrator({"claude": p}), log_path=None).tanya("Bagaimana cara mengisi KRS?")
        self.assertEqual(p.klien.messages.panggilan, 0)



class TestHTTPNyata(unittest.TestCase):
    """http_post_json diuji ke server lokal (tanpa internet)."""

    @classmethod
    def setUpClass(cls):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers["Content-Length"])
                isi = json.loads(self.rfile.read(n))
                if self.path == "/rusak":
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b"rahasia-server")
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"echo": isi, "kunci": self.headers.get("x-api-key")}).encode())

            def log_message(self, *a):
                pass

        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_sukses(self):
        from akademikbot.llm_providers import http_post_json
        d = http_post_json(self.base + "/ok", {"x-api-key": "abc"}, {"a": 1}, 5)
        self.assertEqual(d, {"echo": {"a": 1}, "kunci": "abc"})

    def test_error_http_tanpa_bocor(self):
        from akademikbot.llm_providers import http_post_json
        with self.assertRaises(ProviderError) as cm:
            http_post_json(self.base + "/rusak", {"x-api-key": "abc"}, {}, 5)
        self.assertEqual(str(cm.exception), "HTTP 500")
        self.assertNotIn("rahasia", str(cm.exception))

    def test_server_mati(self):
        from akademikbot.llm_providers import http_post_json
        with self.assertRaises(ProviderError):
            http_post_json("http://127.0.0.1:1/x", {}, {}, 2)


if __name__ == "__main__":
    unittest.main()
