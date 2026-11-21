"""Tes Tahap A: auto-setup, kecerdasan data akademik (waktu WIB, dosen, ruang, kalender, SKS, IPK),
generator surat, dokumen unggahan, dan mode kuis."""
import base64
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from akademikbot import setup_otomatis as so
from akademikbot.alat import hitung_target_ipk
from akademikbot.config import DATA_DIR
from akademikbot.data_akademik import DataAkademik
from akademikbot.dokumen import Dokumen, DokumenError, ekstrak_teks, potong
from akademikbot.kalender import KalenderAkademik
from akademikbot.kb_loader import KBError
from akademikbot.kuis import format_kuis, jumlah_soal, kuis_dari_kb, kuis_dari_teks, minta_kuis, parse_kuis
from akademikbot.llm_client import LLMClient
from akademikbot.router import Chatbot
from akademikbot.surat import buat_draf
from akademikbot.waktu import sekarang_wib
from akademikbot.web import RateLimiter, SesiManager, buat_handler
from tests.fakes import FakeClient

WIB = timezone(timedelta(hours=7))
SELASA = datetime(2026, 11, 17, 9, 0, tzinfo=WIB)        # 17 Nov 2026 = Selasa
DATA = DataAkademik.muat(DATA_DIR)

DOK = ("SURAT EDARAN NOMOR 12 TAHUN 2026\n\nBatas pengumpulan berkas beasiswa prestasi adalah 5 Desember 2026 "
       "pukul 16.00 WIB. Berkas dikumpulkan di sekretariat Prodi Informatika lantai dua.\n\n"
       "Mahasiswa wajib melampirkan transkrip nilai terbaru dan surat rekomendasi dosen pembimbing akademik.")


def bot(tanggal=SELASA, **kw):
    b = Chatbot(offline=True, log_path=None, **kw)
    b.sekarang = lambda: tanggal
    return b


def pdf_minimal(teks: bytes) -> bytes:
    isi = b"BT /F1 12 Tf 10 100 Td (" + teks + b") Tj ET"
    objs = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
            b"<</Length %d>>\nstream\n" % len(isi) + isi + b"\nendstream",
            b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(b"%010d 00000 n \n" % o for o in offs)
    return out + b"trailer<</Root 1 0 R/Size 6>>\nstartxref\n%d\n%%%%EOF" % x


# --------------------------------------------------------------------------- #
# Fitur 1: auto-setup
# --------------------------------------------------------------------------- #
class TestAutoSetup(unittest.TestCase):
    def test_kunci_valid_menolak_placeholder(self):
        for v in (None, "", "   ", "sk-ant-...", "isi_key_anda", "pendek"):
            self.assertFalse(so.kunci_valid(v), v)
        self.assertTrue(so.kunci_valid("sk-ant-api03-abcdefghijk"))

    def test_env_dibuat_dari_contoh_bila_belum_ada(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".env.example").write_text("# contoh\n", encoding="utf-8")
            self.assertEqual(so.siapkan_env(Path(d)), "dibuat")
            self.assertTrue((Path(d) / ".env").exists())
            (Path(d) / ".env").write_text("A=1\n", encoding="utf-8")
            self.assertEqual(so.siapkan_env(Path(d)), "ada")
            self.assertEqual((Path(d) / ".env").read_text(encoding="utf-8"), "A=1\n")   # tidak ditimpa

    def test_env_tanpa_contoh_tidak_error(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(so.siapkan_env(Path(d)), "tidak-ada-contoh")

    def _env(self, **kv):
        bersih = {k: "" for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")}
        return mock.patch.dict(os.environ, {**bersih, **kv})

    def test_mode_offline_tanpa_api_key(self):
        with self._env():
            self.assertEqual(so.tentukan_mode(cek_internet=False)[0], False)

    def test_mode_offline_bila_internet_mati(self):
        with self._env(ANTHROPIC_API_KEY="sk-ant-api03-abcdefghijk"), \
                mock.patch.object(so, "ada_internet", return_value=False):
            pakai, alasan = so.tentukan_mode()
            self.assertFalse(pakai)
            self.assertIn("internet", alasan)

    def test_mode_multi_bila_key_dan_internet_ada(self):
        with self._env(OPENAI_API_KEY="sk-proj-abcdefghijklmn"), mock.patch.object(so, "ada_internet", return_value=True):
            pakai, alasan = so.tentukan_mode()
            self.assertTrue(pakai)
            self.assertIn("gpt", alasan)

    def test_placeholder_dari_env_example_dianggap_kosong(self):
        with self._env(ANTHROPIC_API_KEY="sk-ant-..."):
            self.assertEqual(so.kunci_tersedia(), [])

    def test_paket_kurang_membaca_requirements(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "requirements.txt").write_text(
                "# komentar\npaket-tidak-ada-xyz>=1.0\nunittest\n"
                "tzdata-palsu; platform_system == \"Windows\"\n", encoding="utf-8")
            kurang = so.paket_kurang(Path(d))
            self.assertIn("paket-tidak-ada-xyz>=1.0", kurang)
            self.assertNotIn("unittest", kurang)

    def test_cli_tanpa_argumen_memilih_offline_web(self):
        import argparse
        from akademikbot import cli
        ns = argparse.Namespace(offline=False, multi=False, web=False, buka_browser=False)
        with mock.patch.object(cli, "siapkan_env", return_value="ada"), \
                mock.patch.object(cli, "tentukan_mode", return_value=(False, "API key belum diisi")):
            r = cli._terapkan_mode_otomatis(ns)
        self.assertEqual((r.web, r.offline, r.multi, r.buka_browser), (True, True, False, True))
        ns = argparse.Namespace(offline=False, multi=False, web=False, buka_browser=False)
        with mock.patch.object(cli, "siapkan_env", return_value="ada"), \
                mock.patch.object(cli, "tentukan_mode", return_value=(True, "API key: claude")):
            r = cli._terapkan_mode_otomatis(ns)
        self.assertEqual((r.web, r.offline, r.multi), (True, False, True))

    def test_batch_file_ada_dan_memanggil_mode_otomatis(self):
        isi = (Path(__file__).resolve().parent.parent / "jalankan_web.bat").read_text(encoding="utf-8")
        self.assertIn("main.py --auto", isi)
        self.assertIn("setup_otomatis --pasang", isi)


# --------------------------------------------------------------------------- #
# Fitur 2: kecerdasan data
# --------------------------------------------------------------------------- #
class TestWaktuDanJadwal(unittest.TestCase):
    def test_sekarang_wib_utc_plus_7(self):
        self.assertEqual(sekarang_wib().utcoffset(), timedelta(hours=7))

    def test_jadwal_hari_ini_besok_lusa_zona_wib(self):
        b = bot()
        b.atur_semester(3)
        self.assertIn("hari Selasa", b.tanya("jadwal hari ini").teks)
        self.assertIn("hari Rabu", b.tanya("besok kuliah apa").teks)
        self.assertIn("hari Kamis", b.tanya("jadwal lusa").teks)

    def test_bot_memakai_waktu_wib_secara_bawaan(self):
        self.assertIs(Chatbot(offline=True, log_path=None).sekarang, sekarang_wib)


class TestKalender(unittest.TestCase):
    K = KalenderAkademik.dari_daftar([
        {"id": "krs", "nama": "Revisi KRS", "mulai": "2026-11-25", "kata_kunci": ["revisi krs", "krs"]},
        {"id": "uts", "nama": "Minggu UTS", "mulai": "2026-11-16", "akhir": "2026-11-20", "kata_kunci": ["uts"]},
        {"id": "uas", "nama": "Minggu UAS", "mulai": "2026-11-10", "akhir": "2026-11-14", "kata_kunci": ["uas"]},
    ], dummy=True)

    def test_status_akan_berlangsung_lewat(self):
        hari = date(2026, 11, 18)
        st = {s.acara.id: s for s in self.K.semua(hari)}
        self.assertEqual((st["krs"].status, st["krs"].hari), ("akan", 7))
        self.assertEqual((st["uts"].status, st["uts"].hari), ("berlangsung", 2))
        self.assertEqual((st["uas"].status, st["uas"].hari), ("lewat", 4))
        self.assertEqual(self.K.status(self.K.acara[2], date(2026, 11, 24)).hari, 1)

    def test_urutan_dan_banner(self):
        urut = [s.acara.id for s in self.K.semua(date(2026, 11, 18))]
        self.assertEqual(urut, ["uts", "krs", "uas"])
        self.assertEqual([s.acara.id for s in self.K.banner(date(2026, 11, 18), 14)], ["uts", "krs"])
        self.assertEqual(self.K.banner(date(2026, 11, 18), 3, maks=5)[0].acara.id, "uts")
        self.assertEqual(len(self.K.banner(date(2027, 3, 1))), 0)

    def test_teks_hitung_mundur(self):
        s = self.K.status(self.K.acara[2], date(2026, 11, 21))
        self.assertEqual(s.ringkas(), "⏳ Revisi KRS tinggal 4 hari lagi")
        self.assertIn("DATA CONTOH", self.K.jawab("revisi krs", date(2026, 11, 21)))

    def test_cocok_kata_utuh_dan_frasa_spesifik(self):
        self.assertEqual([a.id for a in self.K.cocok("kapan revisi krs")], ["krs"])
        self.assertEqual(self.K.cocok("apa itu kuas"), [])

    def test_data_salah_ditolak(self):
        with self.assertRaises(KBError):
            KalenderAkademik.dari_daftar([{"id": "a", "nama": "A", "mulai": "31-12-2026"}])
        with self.assertRaises(KBError):
            KalenderAkademik.dari_daftar([{"id": "a", "nama": "A", "mulai": "2026-12-10", "akhir": "2026-12-01"}])

    def test_chatbot_menjawab_hitung_mundur_dengan_tanggal_wib(self):
        r = bot(datetime(2026, 11, 21, 23, 30, tzinfo=WIB)).tanya("berapa hari lagi UAS?")
        self.assertEqual(r.mode, "alat")
        self.assertIn("tinggal 23 hari lagi", r.teks)

    def test_banner_data_asli(self):
        kal = DATA.kalender
        self.assertIsNotNone(kal)
        self.assertTrue(kal.banner(date(2026, 12, 1)))


class TestDosenDanRuang(unittest.TestCase):
    def test_jadwal_dosen_berdasarkan_nama(self):
        r = bot().tanya("kapan Dosen Contoh 3 mengajar?")
        self.assertEqual(r.mode, "alat")
        self.assertIn("Jadwal mengajar Dosen Contoh 3", r.teks)
        self.assertIn("Pemrograman Berorientasi Objek", r.teks)
        self.assertNotIn("Dosen Contoh 13", r.teks)          # angka harus persis

    def test_jadwal_dosen_dengan_sapaan_pak_bu(self):
        self.assertIn("Dosen Contoh 9", bot().tanya("jadwal mengajar Bu Contoh 9").teks)

    def test_dosen_tidak_ada_memberi_saran_bukan_halusinasi(self):
        r = bot().tanya("Kapan jadwal mengajar Pak Budi?")
        self.assertEqual(r.mode, "alat")
        self.assertIn("tidak ditemukan", r.teks)
        self.assertIn("Dosen Contoh 1", r.teks)

    def test_pertanyaan_kb_tentang_dosen_tidak_dibajak(self):
        r = bot().tanya("Bagaimana jika jadwal kuliah berubah atau dosen berhalangan hadir?")
        self.assertNotEqual(r.mode, "alat")

    def test_cari_dosen_awalan_dan_gelar(self):
        d = DataAkademik(kurikulum={"semester": []})
        from akademikbot.data_akademik import Sesi
        d.matkul = {}
        d.jadwal = [Sesi("X", "A", "Senin", "08.00", "09.00", "R1", "Dr. Budi Santoso, S.Kom., M.T.", "Teori")]
        self.assertEqual(d.cari_dosen(["budi"]), ["Dr. Budi Santoso, S.Kom., M.T."])
        self.assertEqual(d.cari_dosen(["bud", "santoso"]), ["Dr. Budi Santoso, S.Kom., M.T."])
        self.assertEqual(d.cari_dosen(["sinta"]), [])

    def test_ruang_kosong_selasa_10(self):
        r = bot().tanya("Ruangan apa yang kosong hari Selasa jam 10.00?")
        self.assertEqual(r.mode, "alat")
        kosong, terpakai = r.teks.split("Sedang dipakai:")
        self.assertIn("R.A101", kosong)
        self.assertNotIn("R.A102", kosong)                    # Kalkulus 10.00-12.30
        self.assertIn("R.A102", terpakai)
        self.assertIn("R.B201", terpakai)                     # Sistem Operasi 10.00-11.40

    def test_batas_jam_selesai_tidak_dianggap_terpakai(self):
        kosong, _ = DATA.ruang_status("Selasa", 11 * 60 + 40, 11 * 60 + 41)    # tepat saat SO selesai
        self.assertIn("R.B201", kosong)

    def test_ruang_kosong_lab_dan_akhir_pekan(self):
        r = bot().tanya("lab kosong hari senin jam 07.30-09.00")
        self.assertNotIn("R.A101", r.teks.split("Sedang dipakai")[0])
        self.assertIn("Lab Komputer 1", r.teks)
        self.assertIn("semua ruangan kosong", bot().tanya("ruangan kosong hari sabtu").teks)

    def test_ruang_kosong_tanpa_jam_memakai_jam_sekarang(self):
        r = bot(datetime(2026, 11, 17, 10, 0, tzinfo=WIB)).tanya("ruangan kosong sekarang")
        self.assertIn("pukul 10.00", bot().tanya("ruangan kosong hari selasa pukul 10").teks)
        self.assertIn("sekarang (10.00 WIB)", r.teks)


class TestSimulasiSKS(unittest.TestCase):
    def test_contoh_pengguna(self):
        r = bot().tanya("cek sks: Algoritma, Basis Data, Sistem Operasi")
        self.assertEqual(r.mode, "alat")
        self.assertIn("Algoritma Pemrograman", r.teks)
        self.assertIn("Sistem Basis Data", r.teks)
        self.assertIn("Total: 9 SKS", r.teks)

    def test_peringatan_melebihi_24_sks(self):
        nama = [m.nama for m in DATA.matkul.values() if m.sks == 3][:9]          # 27 SKS
        r = bot().tanya("cek sks: " + ", ".join(nama))
        self.assertIn("MELEBIHI batas maksimal 24 SKS (kelebihan 3 SKS)", r.teks)
        r = bot().tanya("cek sks: " + ", ".join(nama[:8]))
        self.assertNotIn("MELEBIHI", r.teks)                  # tepat 24 SKS masih boleh

    def test_prasyarat_belum_lulus_dan_diambil_bersamaan(self):
        r = bot().tanya("cek sks: Struktur Data, Algoritma Pemrograman")
        self.assertIn("harus lulus lebih dulu", r.teks)
        r = bot().tanya("cek sks: Struktur Data")
        self.assertIn("belum tercantum lulus", r.teks)
        r = bot().tanya("cek sks: Struktur Data | lulus: Algoritma Pemrograman")
        self.assertIn("Tidak ada prasyarat yang terlanggar", r.teks)

    def test_nama_mengandung_dan_tidak_terpecah(self):
        r = bot().tanya("cek sks: Organisasi dan Arsitektur Komputer, Interaksi Manusia dan Komputer")
        self.assertIn("Organisasi dan Arsitektur Komputer", r.teks)
        self.assertIn("Interaksi Manusia dan Komputer", r.teks)
        self.assertIn("(2 mata kuliah)", r.teks)

    def test_tidak_dikenali_dan_ambigu(self):
        r = bot().tanya("cek sks: Mata Kuliah Karangan, Bahasa")
        self.assertIn("Tidak dikenali", r.teks)
        self.assertIn("cocok dengan beberapa mata kuliah", r.teks)

    def test_tanpa_daftar_diberi_contoh(self):
        self.assertIn("Contoh", bot().tanya("cek sks").teks)

    def test_data_prasyarat_valid(self):
        self.assertTrue(DATA.ada_prasyarat)
        self.assertTrue(all(DATA.matkul[p].semester < m.semester for m in DATA.matkul.values() for p in m.prasyarat))
        self.assertIn("Prasyarat", DATA.entri_kb()[[e.id for e in DATA.entri_kb()].index("mk-INF.62.0007")].jawaban)


class TestKalkulatorIPK(unittest.TestCase):
    def test_contoh_pengguna(self):
        t = hitung_target_ipk("IPK sekarang 3.40 dari 80 SKS, ambil 20 SKS, target IPK 3.50")
        self.assertIn("IPS minimal semester ini: 3.90", t)

    def test_koma_desimal_dan_urutan_lain(self):
        t = hitung_target_ipk("ipk saya 3,8 dari 100 sks, semester ini ambil 20 sks, target ipk 3.82")
        self.assertIn("IPK sekarang 3.80", t)
        self.assertIn("IPS minimal semester ini: 3.92", t)      # (3.82*120 - 3.8*100) / 20

    def test_target_tak_mungkin(self):
        t = hitung_target_ipk("ipk 3.9 dari 100 sks ambil 10 sks target ipk 4.0")
        self.assertIn("belum bisa dicapai", t)
        self.assertIn("3.91", t)

    def test_target_sudah_aman(self):
        self.assertIn("sudah aman", hitung_target_ipk("ipk 3.9 dari 100 sks ambil 20 sks target ipk 3.0"))

    def test_data_tidak_lengkap_atau_tidak_valid(self):
        self.assertIn("Data belum lengkap", hitung_target_ipk("target ipk 3.5"))
        self.assertIn("tidak valid", hitung_target_ipk("ipk 5.2 dari 80 sks ambil 20 sks target ipk 3.5"))
        self.assertIsNone(hitung_target_ipk("Bagaimana cara menghitung IPK dan IPS?"))

    def test_lewat_chatbot(self):
        r = bot().tanya("IPK sekarang 3.40 dari 80 SKS, ambil 20 SKS, target IPK 3.50")
        self.assertEqual((r.mode, r.alasan), ("alat", "alat:ipk"))


# --------------------------------------------------------------------------- #
# Fitur 3: surat, dokumen, kuis
# --------------------------------------------------------------------------- #
class TestSurat(unittest.TestCase):
    def test_email_izin(self):
        t = buat_draf("buatkan email izin tidak masuk kuliah")
        for k in ("Subjek:", "[Nama]", "[NIM]", "[Mata Kuliah]", "[Nama Dosen]"):
            self.assertIn(k, t)

    def test_wa_bimbingan_skripsi(self):
        t = buat_draf("draft WA bimbingan skripsi")
        self.assertIn("Draf WhatsApp", t)
        self.assertNotIn("Subjek:", t)
        self.assertIn("[Judul Skripsi]" if "[Judul Skripsi]" in t else "[Topik Bimbingan]", t)

    def test_mata_kuliah_terisi_dan_alasan_sakit(self):
        t = buat_draf("buatkan email izin sakit kuliah Sistem Operasi", "Sistem Operasi")
        self.assertIn("Sistem Operasi", t)
        self.assertNotIn("[Mata Kuliah]", t)
        self.assertIn("sedang sakit", t)

    def test_jenis_tak_dikenal_menawarkan_daftar_dan_bukan_permintaan_dilewati(self):
        self.assertIn("izin tidak masuk kuliah", buat_draf("buatkan surat lamaran kerja"))
        self.assertIsNone(buat_draf("Bagaimana cara meminta surat keterangan aktif kuliah atau legalisir?"))
        self.assertIsNone(buat_draf("bagaimana cara mengisi KRS?"))

    def test_lewat_chatbot_dengan_nama_matkul(self):
        r = bot().tanya("buatkan email izin tidak masuk kuliah Sistem Operasi")
        self.assertEqual((r.mode, r.alasan), ("alat", "alat:surat"))
        self.assertIn("Sistem Operasi", r.teks)


class TestDokumen(unittest.TestCase):
    def test_ekstrak_txt_dan_validasi(self):
        self.assertIn("beasiswa", ekstrak_teks("a.txt", DOK.encode()))
        for nama, data in (("a.docx", b"x" * 100), ("a.txt", b""), ("a.txt", b"pendek")):
            with self.assertRaises(DokumenError):
                ekstrak_teks(nama, data)
        with self.assertRaises(DokumenError):
            ekstrak_teks("besar.txt", b"a" * (2 * 1024 * 1024 + 1))

    def test_ekstrak_pdf(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("pypdf tidak terpasang")
        self.assertIn("5 Desember 2026", ekstrak_teks("e.pdf", pdf_minimal(b"Batas berkas adalah 5 Desember 2026 ya.")))
        with self.assertRaises(DokumenError):
            ekstrak_teks("rusak.pdf", b"%PDF-1.4 bukan pdf sungguhan")

    def test_potong_dan_karakter_kontrol(self):
        for p in potong("kalimat. " * 400):
            self.assertLessEqual(len(p), 700)
        self.assertNotIn("\x00", ekstrak_teks("a.txt", ("isi dokumen cukup panjang \x00 ya " * 3).encode()))

    def test_tanya_dokumen_tanpa_llm_menampilkan_bagian_relevan(self):
        b = bot()
        b.muat_dokumen("edaran.txt", DOK.encode())
        r = b.tanya("kapan batas pengumpulan berkas beasiswa menurut surat edaran?")      # tidak dibajak kalender
        self.assertEqual((r.mode, r.alasan), ("alat", "dokumen:tanpa_llm"))
        self.assertIn("5 Desember 2026", r.teks)
        self.assertEqual(r.sumber, ["Dokumen unggahan: edaran.txt"])

    def test_tanya_dokumen_dengan_llm_lolos_guardrail_dan_bersitasi(self):
        cl = FakeClient("Batas pengumpulan berkas beasiswa prestasi adalah 5 Desember 2026 pukul 16.00 WIB [S1].")
        b = bot(llm=LLMClient(client=cl))
        b.muat_dokumen("edaran.txt", DOK.encode())
        r = b.tanya("kapan batas pengumpulan berkas beasiswa menurut surat edaran?")
        self.assertEqual((r.mode, r.alasan), ("llm", "dokumen"))
        self.assertEqual(r.sumber, ["Dokumen unggahan: edaran.txt"])
        kirim = json.dumps(cl.messages.panggilan[0]["messages"])
        self.assertIn("Dokumen Unggahan", kirim)
        self.assertIn("TIDAK DIPERCAYA", cl.messages.panggilan[0]["system"])      # aturan anti-injeksi

    def test_jawaban_llm_berangka_palsu_ditolak(self):
        cl = FakeClient("Batas pengumpulan berkas beasiswa prestasi adalah 99 Januari 2030 [S1].")
        b = bot(llm=LLMClient(client=cl))
        b.muat_dokumen("edaran.txt", DOK.encode())
        self.assertEqual(b.tanya("kapan batas pengumpulan berkas beasiswa menurut surat edaran?").mode, "fallback")

    def test_pertanyaan_kb_tetap_dijawab_kb_walau_ada_dokumen(self):
        b = bot()
        b.muat_dokumen("edaran.txt", DOK.encode())
        self.assertEqual(b.tanya("Bagaimana cara mengisi KRS?").mode, "kb")

    def test_dokumen_per_sesi_dan_bisa_dilepas(self):
        b1 = bot()
        b1.muat_dokumen("e.txt", DOK.encode())
        self.assertIsNone(b1.sesi_baru().dokumen)
        b1.hapus_dokumen()
        self.assertIsNone(b1.dokumen)


class TestKuis(unittest.TestCase):
    def test_deteksi_permintaan_dan_jumlah(self):
        for q in ("buatkan 3 soal latihan Sistem Operasi", "kuis seputar KRS", "latihan soal basis data"):
            self.assertTrue(minta_kuis(q), q)
        self.assertFalse(minta_kuis("bagaimana jika nilai ujian saya D?"))
        self.assertEqual((jumlah_soal("buatkan 5 soal"), jumlah_soal("kuis krs"), jumlah_soal("99 soal")), (5, 3, 8))

    def test_parse_kuis_valid_dan_cacat(self):
        ok = json.dumps([{"soal": "Apa itu proses?", "opsi": ["A. a", "b", "c", "d"], "jawaban": "C", "pembahasan": "p"},
                         {"soal": "", "opsi": ["a", "b"], "jawaban": "A"},
                         {"soal": "x", "opsi": ["a", "a"], "jawaban": "A"},
                         {"soal": "y", "opsi": ["a", "b"], "jawaban": "Z"}])
        k = parse_kuis("```json\n" + ok + "\n```", 5)
        self.assertEqual(len(k), 1)
        self.assertEqual((k[0]["jawaban"], k[0]["opsi"][0]), (2, "a"))
        self.assertEqual(parse_kuis("bukan json", 3), [])

    def test_kuis_dari_kb_punya_satu_jawaban_benar(self):
        import random
        faq = [e for e in bot().menu.faq if e.kategori not in ("Jadwal Kuliah", "Kurikulum", "Mata Kuliah")]
        for s in kuis_dari_kb(faq, 3, random.Random(1)):
            self.assertEqual(len(set(s["opsi"])), 4)
            self.assertIn(s["opsi"][s["jawaban"]][:20], s["pembahasan"])
        self.assertIn("Kunci jawaban", format_kuis(kuis_dari_kb(faq, 2, random.Random(1))))

    def test_kuis_dari_teks_dokumen(self):
        import random
        teks = " ".join(f"Mahasiswa angkatan {2000 + i} wajib menyerahkan {i + 2} berkas persyaratan beasiswa kepada sekretariat." for i in range(8))
        k = kuis_dari_teks(teks, 3, random.Random(2))
        self.assertEqual(len(k), 3)
        self.assertTrue(all("_____" in s["soal"] and len(s["opsi"]) == 4 for s in k))

    def test_kuis_kb_offline_lewat_chatbot(self):
        r = bot().tanya("kuis seputar KRS")
        self.assertEqual((r.mode, r.alasan), ("alat", "kuis"))
        self.assertEqual(len(r.kuis), 3)
        self.assertIn("knowledge base", r.teks)

    def test_kuis_matkul_offline_butuh_llm(self):
        r = bot().tanya("buatkan 3 soal latihan Sistem Operasi")
        self.assertEqual(r.alasan, "kuis:butuh_llm")
        self.assertEqual(r.kuis, [])

    def test_kuis_matkul_dengan_llm(self):
        soal = json.dumps([{"soal": "Apa fungsi scheduler?", "opsi": ["a", "b", "c", "d"], "jawaban": "B", "pembahasan": "x"}])
        b = bot(llm=LLMClient(client=FakeClient(soal)))
        r = b.tanya("buatkan 1 soal latihan Sistem Operasi")
        self.assertEqual((r.mode, r.alasan, r.kuis[0]["jawaban"]), ("alat", "kuis", 1))
        self.assertIn("dibuat AI", r.teks)

    def test_kuis_dokumen_offline_dan_llm_rusak_jatuh_ke_offline(self):
        teks = " ".join(f"Mahasiswa angkatan {2000 + i} wajib menyerahkan {i + 2} berkas persyaratan beasiswa kepada sekretariat." for i in range(8))
        b = bot(llm=LLMClient(client=FakeClient("ini bukan json")))
        b.muat_dokumen("e.txt", teks.encode())
        r = b.tanya("buatkan 2 soal latihan dari dokumen")
        self.assertEqual(len(r.kuis), 2)
        self.assertIn("tanpa LLM", r.teks)


# --------------------------------------------------------------------------- #
# Web: dokumen, banner, payload kuis
# --------------------------------------------------------------------------- #
class TestWebTahapA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dasar = Chatbot(offline=True, log_path=None)
        dasar.sekarang = lambda: datetime(2026, 11, 21, 9, 0, tzinfo=WIB)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), buat_handler(
            SesiManager(dasar), RateLimiter(maks=500), feedback_path=None))
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

    def _upload(self, nama, isi: bytes, sesi=None):
        return self._post("/api/dokumen", {"sesi": sesi, "nama": nama, "data": base64.b64encode(isi).decode()})

    def test_banner_endpoint(self):
        with urllib.request.urlopen(self.url + "/api/banner") as r:
            d = json.loads(r.read())
        self.assertTrue(d["dummy"])
        self.assertIn("tinggal 13 hari lagi", d["banner"][0]["teks"])

    def test_upload_tanya_dan_hapus_dokumen(self):
        kode, d = self._upload("edaran.txt", DOK.encode())
        self.assertEqual((kode, d["nama"]), (200, "edaran.txt"))
        sid = d["sesi"]
        kode, j = self._post("/api/chat", {"pesan": "kapan batas berkas beasiswa menurut surat edaran?", "sesi": sid})
        self.assertEqual(j["alasan"], "dokumen:tanpa_llm")
        self.assertEqual(j["dokumen"], "edaran.txt")
        self.assertEqual(self._post("/api/dokumen/hapus", {"sesi": sid})[0], 200)
        self.assertIsNone(self._post("/api/chat", {"pesan": "halo", "sesi": sid})[1]["dokumen"])

    def test_upload_pdf(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("pypdf tidak terpasang")
        kode, d = self._upload("edaran.pdf", pdf_minimal(b"Batas berkas beasiswa adalah 5 Desember 2026 ya."))
        self.assertEqual(kode, 200)

    def test_upload_tidak_valid(self):
        self.assertEqual(self._upload("a.exe", b"x" * 100)[0], 400)
        self.assertEqual(self._upload("kosong.txt", b"")[0], 400)
        self.assertEqual(self._post("/api/dokumen", {"nama": "a.txt", "data": "***bukan base64***"})[0], 400)
        self.assertEqual(self._post("/api/dokumen", {"nama": "a.txt"})[0], 400)
        kode, d = self._upload("besar.txt", b"a" * (2 * 1024 * 1024 + 10))
        self.assertEqual(kode, 400)

    def test_chat_kuis_memuat_array_soal(self):
        kode, j = self._post("/api/chat", {"pesan": "kuis seputar KRS"})
        self.assertEqual(kode, 200)
        self.assertEqual(len(j["kuis"]), 3)
        self.assertEqual(j["mode"], "alat")
        self.assertEqual(set(j["kuis"][0]), {"soal", "opsi", "jawaban", "pembahasan"})

    def test_halaman_memuat_fitur_tahap_a(self):
        with urllib.request.urlopen(self.url + "/") as r:
            html = r.read().decode("utf-8")
        for kata in ("Unggah dokumen", "/api/dokumen", "/api/banner", "kuisKartu", "Alat akademik"):
            self.assertIn(kata, html)


if __name__ == "__main__":
    unittest.main()
