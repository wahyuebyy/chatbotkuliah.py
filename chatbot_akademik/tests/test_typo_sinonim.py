"""Tes koreksi typo & sinonim (Anggota 2)."""
import unittest

from akademikbot.config import KB_PATH
from akademikbot.kb_loader import muat_kb
from akademikbot.preprocessing import tokenize
from akademikbot.tfidf import TfidfIndex


class TestTypoSinonim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx = TfidfIndex(muat_kb(KB_PATH))

    def test_sinonim_perpanjangan(self):
        self.assertIn("batas", tokenize("perpanjangan studi"))

    def test_typo_dikoreksi(self):
        self.assertIn("skripsi", self.idx.tokens("syarat skrispi"))
        self.assertEqual(self.idx.cari("benasiswa")[0].entri.id, "beasiswa-01")

    def test_kata_pendek_tidak_dikoreksi(self):
        self.assertEqual(self.idx.tokens("ukt"), ["ukt"])

    def test_kata_asing_tetap_asing(self):
        self.assertTrue(self.idx.ada_kata_asing("siapa presiden pertama"))

    def test_koreksi_bisa_dimatikan(self):
        self.idx.koreksi_typo_aktif = False
        try:
            self.assertNotIn("skripsi", self.idx.tokens("skrispi"))
        finally:
            self.idx.koreksi_typo_aktif = True


if __name__ == "__main__":
    unittest.main()
