"""Anggota 3: uji guardrail anti-halusinasi."""
import unittest

from akademikbot.guardrail import validasi_jawaban

K = [
    "Berapa maksimal SKS?\nBatas SKS per semester ditentukan berdasarkan IPS semester sebelumnya, umumnya 18-24 SKS.",
    "Bagaimana prosedur cuti akademik?\nCuti akademik diajukan sebelum perkuliahan dimulai dengan mengisi formulir cuti dan persetujuan Dosen PA.",
]


class TestGuardrail(unittest.TestCase):
    def test_jawaban_baik_lolos(self):
        j = ("Batas SKS ditentukan berdasarkan IPS semester sebelumnya, umumnya 18-24 SKS [S1]. "
             "Cuti akademik diajukan sebelum perkuliahan dimulai dengan mengisi formulir cuti [S2].")
        v = validasi_jawaban(j, K)
        self.assertTrue(v.lolos, v.alasan)
        self.assertEqual(v.sitasi, [1, 2])

    def test_tanpa_sitasi_ditolak(self):
        v = validasi_jawaban("Batas SKS ditentukan berdasarkan IPS semester sebelumnya.", K)
        self.assertEqual(v.alasan, "tanpa_sitasi")

    def test_sitasi_nomor_tidak_ada_ditolak(self):
        for n in (0, 3, 9):
            v = validasi_jawaban(f"Batas SKS ditentukan berdasarkan IPS semester sebelumnya [S{n}].", K)
            self.assertFalse(v.lolos)
            self.assertTrue(v.alasan.startswith("sitasi_tidak_valid"), v.alasan)

    def test_angka_karangan_ditolak(self):
        v = validasi_jawaban("Batas SKS ditentukan berdasarkan IPS semester sebelumnya, maksimal 30 SKS [S1].", K)
        self.assertFalse(v.lolos)
        self.assertTrue(v.alasan.startswith("angka_tidak_ada_di_konteks"))

    def test_angka_dari_rentang_konteks_boleh(self):
        v = validasi_jawaban("Umumnya batas SKS per semester antara 18 sampai 24 SKS menurut IPS semester sebelumnya [S1].", K)
        self.assertTrue(v.lolos, v.alasan)

    def test_penanda_daftar_bernomor_bukan_angka_karangan(self):
        j = ("Langkah cuti akademik:\n1. Isi formulir cuti sebelum perkuliahan dimulai [S2].\n"
             "2. Minta persetujuan Dosen PA untuk cuti akademik [S2].")
        v = validasi_jawaban(j, K)
        self.assertTrue(v.lolos, v.alasan)

    def test_satu_sitasi_di_akhir_paragraf_cukup(self):
        j = ("Cuti akademik diajukan sebelum perkuliahan dimulai. Pengajuan dilakukan dengan mengisi "
             "formulir cuti. Persetujuan Dosen PA diperlukan untuk cuti akademik [S2].")
        self.assertTrue(validasi_jawaban(j, K).lolos)

    def test_tidak_ada_info(self):
        self.assertEqual(validasi_jawaban("TIDAK_ADA_INFO", K).alasan, "llm_tidak_tahu")

    def test_kosong(self):
        self.assertEqual(validasi_jawaban("   ", K).alasan, "jawaban_kosong")

    def test_pengetahuan_luar_ditolak(self):
        j = ("Universitas biasanya menyediakan layanan konseling psikologi gratis, kantin sehat, "
             "serta perpustakaan digital untuk seluruh mahasiswa baru [S1].")
        v = validasi_jawaban(j, K)
        self.assertFalse(v.lolos)
        self.assertTrue(v.alasan.startswith("grounding_rendah"), v.alasan)

    def test_sitasi_kurang(self):
        j = ("Batas SKS per semester ditentukan berdasarkan IPS semester sebelumnya [S1].\n"
             "Cuti akademik diajukan sebelum perkuliahan dimulai dengan mengisi formulir cuti.\n"
             "Cuti akademik memerlukan persetujuan Dosen PA sebelum perkuliahan dimulai.")
        v = validasi_jawaban(j, K)
        self.assertEqual(v.alasan, "sitasi_kurang")


if __name__ == "__main__":
    unittest.main()
