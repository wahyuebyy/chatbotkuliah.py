"""Anggota 2: uji TF-IDF."""
import math
import unittest

from akademikbot.config import KB_PATH
from akademikbot.kb_loader import Entri, muat_kb
from akademikbot.tfidf import TfidfIndex


class TestTfidf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx = TfidfIndex(muat_kb(KB_PATH))

    def test_top1_benar(self):
        casing = {"cara mengisi krs": "krs-01", "maksimal sks per semester": "sks-01",
                  "prosedur cuti akademik": "cuti-01", "beasiswa": "beasiswa-01"}
        for q, id_ in casing.items():
            self.assertEqual(self.idx.cari(q)[0].entri.id, id_, q)

    def test_skor_dalam_rentang_dan_terurut(self):
        hasil = self.idx.cari("syarat skripsi dan cuti", k=5)
        skor = [h.skor for h in hasil]
        self.assertEqual(skor, sorted(skor, reverse=True))
        self.assertTrue(all(0 < s <= 1.0 + 1e-9 for s in skor))

    def test_query_kosong_atau_asing(self):
        self.assertEqual(self.idx.cari(""), [])
        self.assertEqual(self.idx.cari("zzzz qqqq"), [])

    def test_kata_asing_menurunkan_cakupan(self):
        murni = self.idx.cari("cuti akademik")[0].cakupan
        campur = self.idx.cari("cuti akademik presiden")[0].cakupan
        self.assertAlmostEqual(murni, 1.0)
        self.assertLess(campur, murni)

    def test_cosine_diri_sendiri_satu(self):
        v = self.idx.vecs[0]
        self.assertAlmostEqual(self.idx._cosine(v, v), 1.0)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in v.values())), 1.0)

    def test_idf_kata_langka_lebih_besar(self):
        e = [Entri("a", "k", "kucing makan ikan", [], ["hewan"], "x", "s"),
             Entri("b", "k", "kucing tidur", [], ["hewan"], "x", "s")]
        idx = TfidfIndex(e)
        self.assertGreater(idx.idf["ikan"], idx.idf["kucing"])

    def test_indeks_kosong_ditolak(self):
        with self.assertRaises(ValueError):
            TfidfIndex([])


if __name__ == "__main__":
    unittest.main()
