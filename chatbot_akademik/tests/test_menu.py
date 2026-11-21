"""Tes menu tabel pilihan, personalisasi semester, dan jalur LLM untuk data jadwal."""
import unittest
from datetime import datetime

from akademikbot.llm_demo import buat_llm_demo
from akademikbot.router import Chatbot
from akademikbot.tfidf import TfidfIndex
from akademikbot.kb_loader import Entri
from akademikbot.web import jalankan_menu


def bot(**kw):
    return Chatbot(offline=True, log_path=None, **kw)


class TestMenu(unittest.TestCase):
    def test_menu_utama_punya_lima_pilihan(self):
        lay = bot().menu.buka([]).layar
        self.assertEqual([o.no for o in lay.opsi], [1, 2, 3, 4, 5])

    def test_jadwal_hanya_menawarkan_semester_berjadwal(self):
        lay = bot().menu.buka(["jadwal"]).layar
        self.assertEqual([o.jalur[1] for o in lay.opsi], ["1", "3", "5", "7"])

    def test_pilihan_akhir_menunjuk_entri_yang_ada(self):
        b = bot()
        for jalur, kode in [(["jadwal", "3", "senin"], "jadwal-s3-senin"), (["jadwal", "3", "semua"], "jadwal-s3"),
                            (["kurikulum", "4"], "sem-4"), (["matkul", "3", "INF.62.0014"], "mk-INF.62.0014")]:
            h = b.menu.buka(jalur)
            self.assertEqual(h.entri_id, kode)
            self.assertIn(kode, b.entri_id)

    def test_semua_opsi_menu_bisa_ditelusuri_sampai_jawaban(self):
        """Tidak ada tombol mati: setiap opsi di setiap layar menuju layar lain atau entri yang ada."""
        b = bot()
        antre, dilihat = [[]], 0
        while antre:
            h = b.menu.buka(antre.pop())
            dilihat += 1
            self.assertLess(dilihat, 400)
            if h.entri_id:
                self.assertIn(h.entri_id, b.entri_id)
            elif h.layar and h.atur_semester is None:
                antre += [o.jalur for o in h.layar.opsi]

    def test_jalur_ngawur_kembali_ke_menu_utama(self):
        for j in (["xyz"], ["jadwal", "99"], ["matkul", "3", "KODE.SALAH"], ["jadwal", "3", "sabtu"], ["faq", "x"]):
            self.assertEqual(bot().menu.buka(j).layar.judul, "MENU UTAMA", j)

    def test_matkul_semester_lain_ditolak(self):
        self.assertEqual(bot().menu.buka(["matkul", "1", "INF.62.0014"]).layar.judul, "MENU UTAMA")

    def test_jawaban_menu_masuk_riwayat_dan_pertanyaan_lanjutan_nyambung(self):
        b = bot()
        r = b.jawab_entri("mk-INF.62.0014")
        self.assertEqual(r.mode, "kb")
        self.assertEqual(b.riwayat[-1][2], "kb")
        lanjut = b.rute("kalau jadwalnya?")
        self.assertEqual(lanjut.hasil[0].entri.id, "mk-INF.62.0014")

    def test_atur_semester_lewat_menu(self):
        b = bot()
        h = b.menu.buka(["semester", "3"])
        self.assertEqual(h.atur_semester, 3)
        b.atur_semester(h.atur_semester)
        self.assertEqual(b.semester, 3)
        with self.assertRaises(ValueError):
            b.atur_semester(12)

    def test_menu_web_satu_langkah(self):
        b = bot()
        d = jalankan_menu(b, "s1", ["jadwal", "3", "selasa"])
        self.assertEqual(d["tipe"], "jawaban")
        self.assertIn("Sistem Operasi", d["jawaban"])
        self.assertEqual(d["balik"]["jalur"], ["jadwal", "3"])
        d = jalankan_menu(b, "s1", ["semester", "5"])
        self.assertEqual((d["tipe"], d["semester"]), ("layar", 5))


class TestPersonalisasi(unittest.TestCase):
    def _bot(self, semester=3, tanggal=datetime(2026, 11, 17)):      # 17 Nov 2026 = Selasa
        b = bot()
        b.sekarang = lambda: tanggal
        if semester:
            b.atur_semester(semester)
        return b

    def test_jadwal_hari_ini_memakai_semester_dan_hari(self):
        r = self._bot().tanya("jadwal hari ini")
        self.assertIn("hari Selasa", r.teks)
        self.assertIn("Sistem Operasi", r.teks)

    def test_besok_dan_hari_eksplisit(self):
        self.assertIn("hari Rabu", self._bot().tanya("besok kuliah apa").teks)
        self.assertIn("hari Jumat", self._bot().tanya("jadwal hari jumat").teks)

    def test_akhir_pekan_tidak_ada_kuliah(self):
        r = self._bot(tanggal=datetime(2026, 11, 14)).tanya("jadwal hari ini")     # Sabtu
        self.assertIn("Tidak ada jadwal kuliah semester 3 pada hari Sabtu", r.teks)

    def test_tanpa_semester_diminta_mengatur_dulu(self):
        r = self._bot(semester=None).tanya("jadwal hari ini")
        self.assertEqual(r.mode, "saran")
        self.assertIn("/semester", r.teks)

    def test_mata_kuliah_saya(self):
        self.assertIn("Mata kuliah semester 3", self._bot().tanya("mata kuliah saya").teks)

    def test_semester_eksplisit_menang_atas_semester_pengguna(self):
        self.assertIn("semester 5", self._bot().tanya("jadwal kuliah saya semester 5").teks)

    def test_pertanyaan_bukan_jadwal_kuliah_tidak_dialihkan(self):
        b = self._bot()
        for q in ("kapan jadwal UTS saya", "jadwal sidang skripsi saya", "bagaimana cara mengisi KRS?"):
            self.assertEqual(b._sesuaikan(q), (q, None), q)

    def test_nama_matkul_disebut_tidak_ditimpa(self):
        b = self._bot()
        self.assertEqual(b._sesuaikan("jadwal sistem operasi saya")[0], "jadwal sistem operasi saya")


class TestLLMDenganData(unittest.TestCase):
    def test_jawaban_llm_berisi_jadwal_lolos_guardrail(self):
        b = Chatbot(llm=buat_llm_demo("baik"), log_path=None)
        r = b.tanya("Siapa dosen Sistem Operasi dan jadwal semester 3 hari Selasa?")
        self.assertEqual(r.mode, "llm", r.alasan)
        self.assertIn("Dosen Contoh 4", r.teks)
        self.assertTrue(r.sumber)

    def test_llm_halusinasi_angka_ditolak(self):
        b = Chatbot(llm=buat_llm_demo("halusinasi"), log_path=None)
        r = b.tanya("Siapa dosen Sistem Operasi dan jadwal semester 3 hari Selasa?")
        self.assertEqual(r.mode, "fallback")


class TestTfidfPerKorpus(unittest.TestCase):
    def _e(self, i, kata):
        return Entri(id=i, kategori="x", pertanyaan=kata, variasi=[kata], kata_kunci=[kata], jawaban="j" * 50)

    def test_idf_korpus_utama_tidak_berubah_oleh_korpus_tambahan(self):
        faq = [self._e("a", "cuti akademik"), self._e("b", "beasiswa prestasi"), self._e("c", "legalisir ijazah")]
        data = [self._e(f"d{i}", "jadwal semester kuliah") for i in range(20)]
        sendiri = TfidfIndex(faq)
        gabung = TfidfIndex(faq + data, [0] * 3 + [1] * 20)
        for t in ("cuti", "beasiswa", "legalisir"):
            self.assertAlmostEqual(sendiri.idf[t], gabung.idf[t])
        self.assertAlmostEqual(sendiri.cari("cuti akademik")[0].skor, gabung.cari("cuti akademik")[0].skor)

    def test_panjang_grup_harus_sama(self):
        with self.assertRaises(ValueError):
            TfidfIndex([self._e("a", "cuti")], [0, 1])


if __name__ == "__main__":
    unittest.main()
