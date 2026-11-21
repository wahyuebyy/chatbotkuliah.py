"""Tes LLM dummy (Anggota 3): tiap mode harus berperilaku sesuai janji terhadap guardrail."""
import unittest

from akademikbot.llm_demo import MODE_DEMO, DemoClient, buat_llm_demo
from akademikbot.router import Chatbot

MAJEMUK = "Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti?"


def bot(mode):
    return Chatbot(llm=buat_llm_demo(mode), log_path=None)


class TestLLMDemo(unittest.TestCase):
    def test_mode_baik_lolos_dan_bersumber(self):
        b = bot("baik").tanya(MAJEMUK)
        self.assertEqual(b.mode, "llm")
        self.assertGreaterEqual(len(b.sumber), 2)
        self.assertIn("[S1]", b.teks)

    def test_mode_nakal_ditolak_guardrail(self):
        for mode, alasan in [("halusinasi", "angka_tidak_ada_di_konteks"),
                             ("tanpa_sitasi", "tanpa_sitasi"),
                             ("sitasi_palsu", "sitasi_tidak_valid"),
                             ("tidak_tahu", "llm_tidak_tahu")]:
            with self.subTest(mode=mode):
                b = bot(mode).tanya(MAJEMUK)
                self.assertEqual(b.mode, "fallback")
                self.assertIn(alasan, b.alasan)

    def test_pertanyaan_sederhana_tidak_memanggil_llm(self):
        c = bot("baik")
        c.tanya("Bagaimana cara mengisi KRS?")
        self.assertEqual(c.llm.client.messages.panggilan, 0)

    def test_mode_tidak_dikenal(self):
        with self.assertRaises(ValueError):
            DemoClient("ngawur")
        self.assertEqual(len(MODE_DEMO), 5)


if __name__ == "__main__":
    unittest.main()
