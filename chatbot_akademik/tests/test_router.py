"""Anggota 4: uji router & alur LLM (memakai LLM tiruan)."""
import unittest

from akademikbot.llm_client import LLMClient
from akademikbot.router import Chatbot

from .fakes import FakeClient

JAWABAN_BAIK = ("Cuti akademik diajukan sebelum perkuliahan dimulai dengan mengisi formulir cuti "
                "dan persetujuan Dosen PA [S1].")


def bot_offline():
    return Chatbot(offline=True, log_path=None)


def bot_llm(balasan=None, error=None):
    fake = FakeClient(balasan, error)
    return Chatbot(llm=LLMClient(client=fake), log_path=None), fake


class TestRute(unittest.TestCase):
    def test_faq_sederhana_ke_kb(self):
        r = bot_offline().rute("Bagaimana cara mengisi KRS?")
        self.assertEqual((r.jalur, r.hasil[0].entri.id), ("kb", "krs-01"))

    def test_apa_saja_tidak_memaksa_llm(self):
        self.assertEqual(bot_offline().rute("Apa saja syarat cuti akademik?").jalur, "kb")

    def test_majemuk_ke_llm(self):
        r = bot_offline().rute("Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti?")
        self.assertEqual(r.jalur, "llm")
        self.assertTrue(r.multitopik)

    def test_di_luar_topik_fallback(self):
        for q in ["Berapa biaya UKT semester depan?", "Siapa presiden Indonesia pertama?", "asdf qwer"]:
            self.assertEqual(bot_offline().rute(q).jalur, "fallback", q)

    def test_sapaan_dan_terima_kasih(self):
        b = bot_offline()
        self.assertEqual(b.rute("Halo").jalur, "sapaan")
        self.assertEqual(b.rute("terima kasih banyak").jalur, "sapaan")

    def test_sapaan_disertai_pertanyaan_tetap_dijawab(self):
        self.assertEqual(bot_offline().rute("Halo, bagaimana cara cuti?").jalur, "kb")
        self.assertEqual(bot_offline().rute("terima kasih, tapi bagaimana cara cuti?").jalur, "kb")

    def test_pertanyaan_lanjutan_pendek(self):
        b = bot_offline()
        b.tanya("Bagaimana cara mengisi KRS?")
        r = b.rute("kapan dibuka?")
        self.assertIn(r.jalur, ("kb", "llm"))     # digabung dengan konteks pertanyaan sebelumnya
        self.assertEqual(r.hasil[0].entri.id, "krs-01")

    def test_kata_asing_bukan_lanjutan(self):
        b = bot_offline()
        b.tanya("Bagaimana cara mengisi KRS?")
        self.assertEqual(b.rute("siapa presiden pertama?").jalur, "fallback")

    def test_input_kosong_dan_panjang(self):
        b = bot_offline()
        self.assertEqual(b.tanya("   ").mode, "sapaan")
        self.assertIn(b.tanya("cuti " * 500).mode, ("kb", "llm", "saran", "fallback"))


class TestAlurLLM(unittest.TestCase):
    Q = "Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti?"

    def test_llm_lolos_validasi(self):
        bot, fake = bot_llm(JAWABAN_BAIK)
        # pakai pertanyaan yang jalurnya llm; konteks [S1] adalah entri teratas
        b = bot.tanya(self.Q)
        self.assertEqual(len(fake.messages.panggilan), 1)
        panggilan = fake.messages.panggilan[0]
        self.assertIn("KONTEKS:", panggilan["messages"][-1]["content"])
        self.assertIn("HANYA", panggilan["system"])
        self.assertIn(b.mode, ("llm", "fallback"))

    def test_llm_jawab_baik_dipakai(self):
        bot, _ = bot_llm()
        r = bot.rute(self.Q)
        # sesuaikan jawaban dengan konteks [S1] sebenarnya agar lolos guardrail
        h = r.hasil[0].entri
        bot.llm.client.messages.balasan = f"{h.jawaban} [S1]"
        b = bot.tanya(self.Q)
        self.assertEqual(b.mode, "llm")
        self.assertEqual(b.sumber, [h.sumber])

    def test_llm_halusinasi_ditolak(self):
        bot, _ = bot_llm("Biaya UKT adalah Rp 5.000.000 per semester [S1].")
        b = bot.tanya(self.Q)
        self.assertEqual(b.mode, "fallback")
        self.assertTrue(b.alasan.startswith("guardrail:"))

    def test_llm_tanpa_sitasi_ditolak(self):
        bot, _ = bot_llm("Silakan ajukan cuti ke bagian akademik.")
        self.assertEqual(bot.tanya(self.Q).mode, "fallback")

    def test_llm_error_turun_ke_kb(self):
        bot, _ = bot_llm(error=TimeoutError("lambat"))
        b = bot.tanya(self.Q)
        self.assertEqual(b.mode, "kb")          # majemuk -> semua jawaban KB ditampilkan
        self.assertIn("LLM error", b.alasan)

    def test_llm_tidak_ada_info(self):
        bot, _ = bot_llm("TIDAK_ADA_INFO")
        self.assertEqual(bot.tanya(self.Q).mode, "fallback")

    def test_pertanyaan_kb_tidak_memanggil_llm(self):
        bot, fake = bot_llm(JAWABAN_BAIK)
        self.assertEqual(bot.tanya("Bagaimana cara mengisi KRS?").mode, "kb")
        self.assertEqual(fake.messages.panggilan, [])

    def test_fallback_tidak_memanggil_llm(self):
        bot, fake = bot_llm(JAWABAN_BAIK)
        self.assertEqual(bot.tanya("Berapa biaya UKT semester depan?").mode, "fallback")
        self.assertEqual(fake.messages.panggilan, [])


class TestLLMClient(unittest.TestCase):
    def test_offline(self):
        c = LLMClient(enabled=False)
        self.assertFalse(c.tersedia)
        self.assertEqual(c.error, "mode offline")

    def test_tanpa_api_key(self):
        import os
        asli = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            c = LLMClient()
            self.assertFalse(c.tersedia)
        finally:
            if asli:
                os.environ["ANTHROPIC_API_KEY"] = asli



class TestSesiBaru(unittest.TestCase):
    def test_riwayat_dibatasi(self):
        from akademikbot.config import MAKS_RIWAYAT
        bot = Chatbot(offline=True, log_path=None)
        for _ in range(MAKS_RIWAYAT + 5):
            bot.tanya("Halo")
        self.assertEqual(len(bot.riwayat), MAKS_RIWAYAT)

    def test_sesi_baru_berbagi_indeks(self):
        bot = Chatbot(offline=True, log_path=None)
        b2 = bot.sesi_baru()
        self.assertIs(b2.index, bot.index)
        self.assertEqual(b2.riwayat, [])


if __name__ == "__main__":
    unittest.main()
