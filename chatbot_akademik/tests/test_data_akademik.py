"""Tes data terstruktur (kurikulum.json, jadwal.csv) dan entri KB yang dibangkitkan."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from akademikbot.config import DATA_DIR
from akademikbot.data_akademik import DataAkademik
from akademikbot.kb_loader import KBError


def salin_data() -> Path:
    tmp = Path(tempfile.mkdtemp())
    for f in DATA_DIR.iterdir():
        shutil.copy(f, tmp / f.name)
    return tmp


class TestDataBawaan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = DataAkademik.muat(DATA_DIR)

    def test_kurikulum_lengkap(self):
        self.assertEqual(self.d.semester_kurikulum(), list(range(1, 9)))
        self.assertEqual(len(self.d.matkul), 55)

    def test_sks_sesuai_jumlah_tercetak_dan_komponennya(self):
        for s in self.d.kurikulum["semester"]:
            mk = self.d.matkul_semester(int(s["no"]))
            self.assertEqual(sum(m.sks for m in mk), s["sks_tercetak"], f"semester {s['no']}")
            for m in mk:
                self.assertEqual(m.sks, m.t + m.p + m.l, m.kode)

    def test_tidak_ada_nilai_pribadi(self):
        """Kolom nilai (huruf mutu mahasiswa) tidak boleh ikut masuk ke KB bersama."""
        for s in self.d.kurikulum["semester"]:
            for m in s["matkul"]:
                self.assertFalse({"nilai", "grade", "mutu"} & set(m), m["kode"])

    def test_jadwal_bawaan_tidak_bentrok(self):
        self.assertEqual(self.d.periksa(), [])

    def test_id_entri_unik(self):
        ids = [e.id for e in self.d.entri_kb()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_entri_semester_4_memisah_wajib_dan_pilihan(self):
        e = next(x for x in self.d.entri_kb() if x.id == "sem-4")
        self.assertIn("Total SKS wajib 22; SKS pilihan 6", e.jawaban)
        self.assertIn("28 SKS", e.jawaban)

    def test_entri_matkul_memuat_jadwal_dan_label_dummy(self):
        e = next(x for x in self.d.entri_kb() if x.id == "mk-INF.62.0014")
        self.assertIn("Sistem Operasi", e.jawaban)
        self.assertIn("Selasa 10.00-11.40", e.jawaban)
        self.assertIn("DATA CONTOH", e.jawaban)

    def test_semester_tanpa_jadwal_dijawab_belum_tersedia(self):
        e = next(x for x in self.d.entri_kb() if x.id == "jadwal-s2")
        self.assertIn("belum tersedia", e.jawaban)

    def test_label_dummy_hilang_bila_dummy_false(self):
        tmp = salin_data()
        info = json.loads((tmp / "jadwal_info.json").read_text(encoding="utf-8"))
        info["dummy"] = False
        (tmp / "jadwal_info.json").write_text(json.dumps(info), encoding="utf-8")
        e = next(x for x in DataAkademik.muat(tmp).entri_kb() if x.id == "jadwal-s3")
        self.assertNotIn("DATA CONTOH", e.jawaban)


class TestValidasiCSV(unittest.TestCase):
    HEADER = "kode,kelas,hari,mulai,selesai,ruang,dosen,jenis\n"

    def _muat(self, baris: str):
        tmp = salin_data()
        (tmp / "jadwal.csv").write_text(self.HEADER + baris, encoding="utf-8")
        return DataAkademik.muat(tmp)

    def test_kode_tidak_dikenal(self):
        with self.assertRaisesRegex(KBError, "tidak ada di kurikulum"):
            self._muat("XXX.1,A,Senin,07.30,09.00,R1,Dosen,Teori\n")

    def test_hari_salah(self):
        with self.assertRaisesRegex(KBError, "hari"):
            self._muat("INF.62.0014,A,Seninn,07.30,09.00,R1,Dosen,Teori\n")

    def test_jam_salah_dan_urutan_jam(self):
        with self.assertRaisesRegex(KBError, "format jam"):
            self._muat("INF.62.0014,A,Senin,7-30,09.00,R1,Dosen,Teori\n")
        with self.assertRaisesRegex(KBError, "setelah jam mulai"):
            self._muat("INF.62.0014,A,Senin,09.00,08.00,R1,Dosen,Teori\n")

    def test_kolom_hilang(self):
        tmp = salin_data()
        (tmp / "jadwal.csv").write_text("kode,hari\nINF.62.0014,Senin\n", encoding="utf-8")
        with self.assertRaisesRegex(KBError, "kolom wajib hilang"):
            DataAkademik.muat(tmp)

    def test_format_jam_titik_dua_diterima(self):
        d = self._muat("INF.62.0014,A,senin,7:30,9:10,R1,Dosen X,Teori\n")
        self.assertEqual((d.jadwal[0].hari, d.jadwal[0].mulai, d.jadwal[0].selesai), ("Senin", "07.30", "09.10"))

    def test_deteksi_bentrok_ruang_dosen_dan_kelas(self):
        d = self._muat("INF.62.0014,A,Senin,08.00,10.00,R1,Dosen X,Teori\n"
                       "INF.62.0013,A,Senin,09.00,11.00,R1,Dosen X,Teori\n")
        teks = " ".join(d.periksa())
        self.assertIn("Ruang bentrok", teks)
        self.assertIn("Dosen bentrok", teks)
        self.assertIn("Jadwal mahasiswa bentrok", teks)

    def test_tanpa_bentrok_bila_hari_atau_jam_berbeda(self):
        d = self._muat("INF.62.0014,A,Senin,08.00,10.00,R1,Dosen X,Teori\n"
                       "INF.62.0013,A,Senin,10.00,11.00,R1,Dosen X,Teori\n")
        self.assertEqual(d.periksa(), [])

    def test_tanpa_kurikulum_fitur_mati(self):
        self.assertIsNone(DataAkademik.muat(Path(tempfile.mkdtemp())))


if __name__ == "__main__":
    unittest.main()
