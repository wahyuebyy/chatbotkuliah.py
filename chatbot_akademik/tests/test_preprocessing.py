"""Anggota 2: uji preprocessing."""
import unittest

from akademikbot.preprocessing import normalisasi, stem, tokenize


class TestStem(unittest.TestCase):
    def test_turunan_ke_kata_dasar(self):
        for kata, dasar in [("mengisi", "isi"), ("pengisian", "isi"), ("diisi", "isi"),
                            ("pengajuan", "aju"), ("mengajukan", "aju"),
                            ("perkuliahan", "kuliah"), ("penilaian", "nilai"),
                            ("pembimbing", "bimbing"), ("pendaftaran", "daftar")]:
            self.assertEqual(stem(kata), dasar, kata)

    def test_kata_dasar_tidak_dirusak(self):
        for kata in ["nilai", "kuliah", "ujian", "sekretariat", "prodi", "krs", "ipk"]:
            self.assertEqual(stem(kata), kata)


class TestTokenize(unittest.TestCase):
    def test_stopword_dan_tanda_baca_dibuang(self):
        self.assertEqual(tokenize("Bagaimana cara mengisi KRS?"), ["isi", "krs"])

    def test_singkatan_chat_dinormalisasi(self):
        self.assertEqual(tokenize("gmn cara cuti?"), ["cuti"])
        self.assertIn("tugas", tokenize("ta"))
        self.assertIn("akhir", tokenize("ta"))
        self.assertIn("semester", normalisasi("sem depan"))

    def test_kosong(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("?!..."), [])


if __name__ == "__main__":
    unittest.main()
