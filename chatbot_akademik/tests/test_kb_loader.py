"""Anggota 1: uji loader & validasi knowledge base."""
import json
import tempfile
import unittest
from pathlib import Path

from akademikbot.config import KB_PATH
from akademikbot.kb_loader import KBError, muat_kb, periksa_kualitas


def tulis(data) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    f.write(data if isinstance(data, str) else json.dumps(data))
    f.close()
    return Path(f.name)


E = {"id": "a", "pertanyaan": "q", "jawaban": "j"}


class TestKB(unittest.TestCase):
    def test_kb_asli_valid_dan_id_unik(self):
        entri = muat_kb(KB_PATH)
        self.assertGreaterEqual(len(entri), 10)
        self.assertEqual(len({e.id for e in entri}), len(entri))
        self.assertEqual(periksa_kualitas(entri), [])

    def test_file_tidak_ada(self):
        with self.assertRaises(KBError):
            muat_kb(Path("tidak_ada.json"))

    def test_json_rusak(self):
        with self.assertRaises(KBError):
            muat_kb(tulis("{rusak"))

    def test_field_wajib_hilang(self):
        with self.assertRaises(KBError):
            muat_kb(tulis({"entri": [{"id": "a", "pertanyaan": "q"}]}))

    def test_id_ganda(self):
        with self.assertRaises(KBError):
            muat_kb(tulis({"entri": [E, dict(E)]}))

    def test_kb_kosong(self):
        with self.assertRaises(KBError):
            muat_kb(tulis({"entri": []}))

    def test_peringatan_kualitas(self):
        self.assertTrue(periksa_kualitas(muat_kb(tulis({"entri": [E]}))))


if __name__ == "__main__":
    unittest.main()
