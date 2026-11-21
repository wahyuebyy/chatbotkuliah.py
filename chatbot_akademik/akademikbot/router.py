"""
router.py  -  Otak chatbot: memutuskan pertanyaan dijawab KB lokal, LLM, atau fallback.

PENANGGUNG JAWAB: Anggota 4 (Router, CLI & Evaluasi)

Alur:
    pertanyaan -> sapaan / terima kasih?                    -> balasan singkat
               -> TF-IDF (cari entri KB)
                    skor rendah / salah topik               -> FALLBACK (arahkan ke admin Prodi)
                    skor tinggi & pertanyaan sederhana      -> JAWAB LANGSUNG dari KB
                    pertanyaan kompleks / majemuk / skor sedang
                                                            -> LLM (grounded) + guardrail
                                                               gagal validasi -> FALLBACK

Keputusan rute (`Chatbot.rute`) dipisah dari eksekusi jawaban (`Chatbot._proses`)
supaya akurasi router bisa dievaluasi tanpa memanggil LLM (lihat evaluasi/).
"""

from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import (
    CAKUPAN_MIN,
    DATA_DIR,
    FALLBACK,
    KB_PATH,
    LOG_AKTIF,
    LOG_PATH,
    MAKS_RIWAYAT,
    MAKS_KATA_PERTANYAAN_SEDERHANA,
    MAKS_PANJANG_PERTANYAAN,
    NAMA_BOT,
    NAMA_PRODI,
    THRESHOLD_MIRIP,
    THRESHOLD_SANGAT_YAKIN,
    THRESHOLD_YAKIN,
    TOP_K,
    TOPIK_RASIO_SKOR_MIN,
    TOPIK_TAMBAHAN_MIN,
)
from . import kuis as modul_kuis
from .alat import AlatAkademik
from .data_akademik import HARI, DataAkademik
from .dokumen import Dokumen
from .guardrail import validasi_jawaban
from .kb_loader import KBError, muat_kb
from .llm_client import LLMClient, teks_konteks
from .menu import MenuAkademik, pilih_saran, saran_cepat
from .preprocessing import tokenize
from .tfidf import Hasil, TfidfIndex
from .waktu import sekarang_wib

# --------------------------------------------------------------------------- #
# Pola bahasa
# --------------------------------------------------------------------------- #
SAPAAN = re.compile(
    r"^\s*(halo|hai|hi|hello|assalamualaikum|selamat (pagi|siang|sore|malam)|p)\b", re.I)
TERIMA_KASIH = re.compile(r"\b(terima ?kasih|makasih|mksh|thanks|thx)\b", re.I)

# Sinyal KUAT: pertanyaan majemuk / perlu menggabungkan info -> LLM.
KOMPLEKS_KUAT = re.compile(
    r"\b(dan juga|sekaligus|bandingkan|perbedaan|bedanya|jika .* maka|kalau .* apakah|"
    r"sebelum itu|setelah itu|kemudian|terus|serta)\b", re.I)
# Sinyal LEMAH: kata urutan/waktu yang kadang muncul di pertanyaan FAQ biasa.
# Hanya mengarahkan ke LLM bila skor KB belum sangat tinggi.
KOMPLEKS_LEMAH = re.compile(r"\b(urutan|sebelum|sesudah|setelah)\b", re.I)

# Personalisasi berdasarkan semester pengguna ("jadwal hari ini", "mata kuliah saya").
JADWAL_KATA = re.compile(r"\b(jadwal|kuliah|masuk)\b", re.I)
MATKUL_SAYA = re.compile(r"\b(mata kuliah|matkul|mk|sks)\b.*\b(saya|ku|semester ini)\b|"
                         r"\b(saya|ku)\b.*\b(mata kuliah|matkul|mk|sks)\b", re.I)
PERSONAL = re.compile(r"\b(hari ini|besok|lusa|saya|ku|semester ini|minggu ini)\b", re.I)
BUKAN_JADWAL_KULIAH = re.compile(r"\b(ujian|uts|uas|sidang|wisuda|yudisium|krs|skripsi|cuti|beasiswa|"
                                 r"pembayaran|ukt|kalender|libur|pengganti)\b", re.I)
HARI_RE = re.compile(r"\b(senin|selasa|rabu|kamis|jumat|jum'at|sabtu|minggu)\b", re.I)
SEMESTER_EKSPLISIT = re.compile(r"\b(semester|sem|smt)\s*(ke[-\s]?)?[1-8]\b", re.I)

# Pertanyaan lanjutan pendek setelah memilih sesuatu di menu ("kalau jadwalnya?", "dosennya siapa?").
# Pertanyaan yang jelas menyebut dokumen/materi yang diunggah pengguna.
DOK_RE = re.compile(r"\b(dokumen|berkas|file|pdf|surat edaran|edaran|unggahan|diunggah|materi|lampiran|"
                    r"isi surat|ringkas(?:kan)?)\b", re.I)
KATEGORI_DATA = ("Jadwal Kuliah", "Kurikulum", "Mata Kuliah")

LANJUTAN = re.compile(r"\b(\w+nya|kalau|lalu|terus|dan)\b", re.I)

TEKS_SAPAAN = (f"Halo! Saya {NAMA_BOT}, asisten layanan akademik {NAMA_PRODI}. "
               "Tanyakan seputar KRS, cuti, skripsi, beasiswa, dan lainnya.")
TEKS_TERIMA_KASIH = "Sama-sama! Kalau ada pertanyaan akademik lain, silakan tanya ya."
TEKS_KOSONG = "Silakan ketik pertanyaan Anda seputar layanan akademik."


# --------------------------------------------------------------------------- #
# Struktur data
# --------------------------------------------------------------------------- #
@dataclass
class Rute:
    """Keputusan router (sebelum jawaban dibuat)."""
    jalur: str                    # sapaan | kb | llm | fallback
    hasil: list[Hasil] = field(default_factory=list)   # entri KB yang dipakai
    alasan: str = ""              # penjelasan singkat, untuk debug & evaluasi
    teks: str = ""                # khusus sapaan
    multitopik: bool = False


@dataclass
class Balasan:
    teks: str
    mode: str                     # kb | llm | fallback | sapaan | saran | alat
    skor: float = 0.0
    sumber: list[str] = field(default_factory=list)
    waktu_ms: float = 0.0
    alasan: str = ""
    model: str = ""               # model LLM yang menjawab (mode multi-model)
    percobaan: list[str] = field(default_factory=list)   # jejak failover antar model
    kuis: list[dict] = field(default_factory=list)       # soal kuis interaktif (mode kuis)
    opsi_cepat: list[str] = field(default_factory=list)  # pertanyaan lanjutan yang bisa dipilih (1/2/3)
    dipilih: str = ""             # bila pengguna mengetik angka: pertanyaan lengkap yang dipilih


def pertanyaan_kompleks_teks(q: str) -> bool:
    """Sinyal kompleks dari bentuk teks saja (panjang, banyak '?', kata penghubung)."""
    return (len(q.split()) > MAKS_KATA_PERTANYAAN_SEDERHANA
            or q.count("?") > 1
            or bool(KOMPLEKS_KUAT.search(q)))


# --------------------------------------------------------------------------- #
# Chatbot
# --------------------------------------------------------------------------- #
class Chatbot:
    def __init__(self, kb_path: Path = KB_PATH, offline: bool = False,
                 llm: Optional[LLMClient] = None, log_path: Optional[Path] = LOG_PATH,
                 index: Optional[TfidfIndex] = None, data_dir: Optional[Path] = DATA_DIR,
                 data: Optional[DataAkademik] = None, menu: Optional[MenuAkademik] = None):
        # `index`, `llm`, `data`, `menu` boleh dibagi antar-sesi (web) supaya KB tidak dimuat ulang per pengguna.
        if index is None:
            entri = muat_kb(kb_path)
            faq = list(entri)
            data = DataAkademik.muat(data_dir) if data_dir else None
            if data:
                faq += data.entri_umum                 # info_umum.json = FAQ biasa (korpus 0)
                tambahan = data.entri_kb()             # dibangkitkan dari kurikulum/jadwal (korpus 1)
                ada = {e.id for e in faq}
                dobel = [e.id for e in tambahan if e.id in ada]
                if dobel:
                    raise KBError(f"ID ganda antara KB dan data terstruktur: {dobel[:3]}")
                grup = [0] * len(faq) + [1] * len(tambahan)
                entri = faq + tambahan
            else:
                grup = None
            index = TfidfIndex(entri, grup)
            menu = MenuAkademik(data, faq)
        self.index = index
        self.data = data
        self.menu = menu if menu is not None else MenuAkademik(data, list(index.entri))
        self.entri_id = {e.id: e for e in index.entri}
        self.llm = llm if llm is not None else LLMClient(enabled=not offline)
        self.log_path = log_path if LOG_AKTIF else None
        self._terakhir_menu: Optional[str] = None  # pertanyaan entri yang baru dipilih lewat menu
        self._opsi_cepat: list[str] = []           # opsi 1/2/3 dari balasan terakhir (bila ada)
        self.semester: Optional[int] = None        # semester pengguna (diatur lewat menu / '/semester N')
        self.sekarang = sekarang_wib               # waktu WIB; dapat diganti saat pengujian
        self.alat = AlatAkademik(data)             # jadwal dosen, ruang kosong, kalender, SKS, IPK, surat
        self.dokumen: Optional[Dokumen] = None     # dokumen unggahan sementara (per sesi)
        # (pertanyaan, jawaban, mode) -- hanya kb/llm yang dikirim ke LLM sebagai riwayat
        self.riwayat: list[tuple[str, str, str]] = []

    # -- API publik ---------------------------------------------------------- #
    def tanya(self, q: str) -> Balasan:
        q = " ".join(q.split())[:MAKS_PANJANG_PERTANYAAN]
        t0 = time.perf_counter()
        # Ketikan "1"/"2"/"3" setelah balasan yang menawarkan pilihan cepat = memilih opsi itu.
        dipilih = pilih_saran(q, self._opsi_cepat)
        if dipilih:
            q = dipilih
        if not q:
            b = Balasan(TEKS_KOSONG, "sapaan")
        else:
            langsung = self._alat(q)               # alat berbasis kode didahulukan
            if langsung is None:
                q, langsung = self._sesuaikan(q)
            b = langsung or self._proses(q)
            self._terakhir_menu = None
        b.dipilih = dipilih or ""
        # Pilihan cepat hanya untuk jawaban nyata (kb/llm); sapaan, saran & fallback tidak menawarkan.
        b.opsi_cepat = saran_cepat(q) if q and b.mode in ("kb", "llm") else []
        self._opsi_cepat = b.opsi_cepat
        b.waktu_ms = (time.perf_counter() - t0) * 1000
        if q:
            self._catat(q, b)
        return b

    # -- dokumen unggahan -------------------------------------------------------- #
    def muat_dokumen(self, nama: str, isi: bytes) -> dict:
        """Pasang dokumen (txt/pdf) sebagai konteks sesi ini. Melempar DokumenError bila tak bisa dipakai."""
        self.dokumen = Dokumen.dari_berkas(nama, isi)
        return self.dokumen.ringkas()

    def hapus_dokumen(self) -> None:
        self.dokumen = None

    # -- alat & kuis --------------------------------------------------------------- #
    def _alat(self, q: str) -> Optional[Balasan]:
        if modul_kuis.minta_kuis(q):
            return self._kuis(q)
        if self.dokumen is not None and DOK_RE.search(q):
            return None                              # pertanyaan tentang dokumen unggahan: jangan dibajak alat
        h = self.alat.coba(q, self.sekarang())
        return Balasan(h.teks, "alat", 1.0, h.sumber, alasan=h.alasan) if h else None

    def _llm_bisa_selesaikan(self) -> bool:
        return self.llm.tersedia and hasattr(self.llm, "selesaikan")

    def _kuis(self, q: str) -> Balasan:
        n, topik = modul_kuis.jumlah_soal(q), modul_kuis.topik_dari(q)
        mk = self.data.matkul_cocok(q) if self.data else []
        rng = random.Random()
        soal: list[dict] = []
        model, sumber, catatan, judul = "", [], "", ""
        if self.dokumen and (DOK_RE.search(q) or not mk):
            judul = f"dari dokumen \"{self.dokumen.nama}\""
            sumber = [f"Dokumen unggahan: {self.dokumen.nama}"]
            hits = self.dokumen.cari(topik, k=5) if topik else []
            konteks = "\n\n".join(h.entri.jawaban for h in hits) if hits else self.dokumen.teks[:6000]
            if self._llm_bisa_selesaikan():
                try:
                    soal = modul_kuis.kuis_llm(self.llm, n, topik, konteks)
                    model = self.llm.model
                    catatan = f"Soal dibuat AI ({model}) dari isi dokumen; periksa kembali dengan dokumennya."
                except Exception:
                    soal = []
            if not soal:
                soal = modul_kuis.kuis_dari_teks(self.dokumen.teks, n, rng)
                catatan = "Soal isian dibuat otomatis dari kalimat dokumen (tanpa LLM)."
        elif mk:
            judul = f"mata kuliah {mk[0].nama}"
            if not self._llm_bisa_selesaikan():
                return Balasan(
                    f"Soal latihan materi {mk[0].nama} butuh LLM (API key) karena materi kuliah tidak ada di "
                    "knowledge base. Saat ini mode offline. Alternatif: unggah materi kuliahnya (PDF/TXT) lalu "
                    "minta kuis, atau minta \"kuis seputar KRS\" untuk latihan dari knowledge base Prodi.",
                    "alat", alasan="kuis:butuh_llm")
            try:
                soal = modul_kuis.kuis_llm(self.llm, n, topik=mk[0].nama)
                model = self.llm.model
                catatan = (f"Soal dibuat AI ({model}) dari pengetahuan umum sebagai alat latihan; bukan "
                           "kebijakan resmi. Cocokkan dengan materi dosen.")
            except Exception:
                soal = []
        else:
            judul = "seputar layanan akademik" + (f" ({topik})" if topik else "")
            faq = [e for e in self.menu.faq if e.kategori not in KATEGORI_DATA]
            utama: list = []
            if topik:
                ids = {e.id for e in faq}
                utama = [h.entri for h in self.index.cari(topik, k=8)
                         if h.entri.id in ids and h.skor >= THRESHOLD_MIRIP]
            soal = modul_kuis.kuis_dari_kb(faq, n, rng, utama=utama)
            sumber = list(dict.fromkeys(s["pembahasan"].rsplit("Sumber: ", 1)[-1].rstrip(")") for s in soal))
            catatan = "Soal diambil dari knowledge base resmi Prodi. Pilih jawaban yang paling sesuai."
        if not soal:
            return Balasan("Maaf, saya belum berhasil membuat soal untuk permintaan itu. Coba sebutkan topiknya "
                           "lebih jelas, atau unggah dokumen materinya.", "alat", alasan="kuis:gagal")
        teks = f"Berikut {len(soal)} soal latihan {judul}.\n{catatan}"
        return Balasan(teks, "alat", 1.0, sumber, alasan="kuis", model=model, kuis=soal)

    # -- menu & personalisasi --------------------------------------------------- #
    def atur_semester(self, n: Optional[int]) -> None:
        if n is not None and (self.data is None or n not in self.data.semester_kurikulum()):
            raise ValueError(f"semester tidak valid: {n}")
        self.semester = n

    def jawab_entri(self, entri_id: str, alasan: str = "menu", dengan_opsi: bool = False) -> Balasan:
        """Jawaban langsung dari satu entri KB (dipakai menu). Masuk riwayat seperti chat biasa.

        `dengan_opsi=True` (web) menyertakan pilihan cepat; di menu CLI angka sudah dipakai untuk
        memilih baris tabel, jadi default-nya False dan pilihan cepat lama dihapus."""
        t0 = time.perf_counter()
        e = self.entri_id[entri_id]
        b = Balasan(e.jawaban, "kb", 1.0, [e.sumber], alasan=alasan)
        b.opsi_cepat = saran_cepat(e.pertanyaan) if dengan_opsi else []
        self._opsi_cepat = b.opsi_cepat
        self._terakhir_menu = e.pertanyaan
        b.waktu_ms = (time.perf_counter() - t0) * 1000
        self._catat(e.pertanyaan, b)
        return b

    def _catat(self, q: str, b: Balasan) -> None:
        self.riwayat.append((q, b.teks, b.mode))
        del self.riwayat[:-MAKS_RIWAYAT]   # batasi memori sesi panjang
        self._log(q, b)

    def _sesuaikan(self, q: str) -> tuple[str, Optional[Balasan]]:
        """Pahami pertanyaan 'personal' memakai semester pengguna & tanggal hari ini, lalu tulis ulang
        menjadi pertanyaan eksplisit yang dikenali KB ("jadwal hari ini" -> "jadwal kuliah semester 3
        hari Senin"). Penulisan ulang dilakukan di kode, bukan oleh LLM, sehingga jawabannya tetap
        berasal dari KB dan lolos guardrail. Mengembalikan (pertanyaan, balasan_langsung | None)."""
        if self.data is None or SEMESTER_EKSPLISIT.search(q) or BUKAN_JADWAL_KULIAH.search(q):
            return q, None
        hari_kata = HARI_RE.search(q)
        relatif = re.search(r"\b(hari ini|besok|lusa)\b", q, re.I)
        tanpa_mk = re.sub(r"\bmata kuliah\b", " ", q, flags=re.I)   # 'kuliah' dalam 'mata kuliah' bukan jadwal
        jadwal = bool(JADWAL_KATA.search(tanpa_mk)) and bool(PERSONAL.search(q) or hari_kata)
        daftar_mk = bool(MATKUL_SAYA.search(q))
        if not (jadwal or daftar_mk) or self.data.matkul_cocok(q):
            return q, None
        if self.semester is None:
            teks = ("Semester Anda belum diatur, jadi saya belum tahu jadwal yang dimaksud. "
                    "Ketik /semester 3 (ganti angkanya) atau pilih lewat /menu -> Atur semester saya, "
                    "atau sebutkan semesternya, mis. 'jadwal kuliah semester 3'.")
            return q, Balasan(teks, "saran", alasan="sesuaikan:semester_belum_diatur")
        n = self.semester
        if daftar_mk and not jadwal:
            return f"Mata kuliah apa saja di semester {n}?", None
        if relatif:
            geser = {"hari ini": 0, "besok": 1, "lusa": 2}[relatif.group(1).lower()]
            idx = (self.sekarang().weekday() + geser) % 7
            hari = HARI[idx]
        elif hari_kata:
            hari = hari_kata.group(1).capitalize().replace("Jum'at", "Jumat")
        else:
            return f"Jadwal kuliah semester {n}?", None
        if hari in ("Sabtu", "Minggu"):
            sumber = [self.entri_id[f"jadwal-s{n}"].sumber] if f"jadwal-s{n}" in self.entri_id else []
            return q, Balasan(f"Tidak ada jadwal kuliah semester {n} pada hari {hari} di data.", "kb", 1.0,
                              sumber, alasan=f"sesuaikan:akhir_pekan|semester={n}")
        if f"jadwal-s{n}-{hari.lower()}" not in self.entri_id:
            return q, Balasan(f"Data jadwal semester {n} belum tersedia (jadwal.csv belum memuat semester ini).",
                              "fallback", alasan=f"sesuaikan:semester_tanpa_jadwal|semester={n}")
        return f"Jadwal kuliah semester {n} hari {hari}?", None

    def rute(self, q: str) -> Rute:
        """Putuskan jalur jawaban TANPA memanggil LLM (murni, mudah diuji)."""
        if self._hanya_terima_kasih(q):
            return Rute("sapaan", alasan="terima_kasih", teks=TEKS_TERIMA_KASIH)
        if SAPAAN.match(q) and (not tokenize(q)
                                or (len(q.split()) <= 3 and not self.index.cari(q))):
            return Rute("sapaan", alasan="sapaan", teks=TEKS_SAPAAN)

        # Ucapan terima kasih di tengah pertanyaan ("makasih, tapi gimana cuti?") dibuang.
        q = " ".join(TERIMA_KASIH.sub(" ", q).split())
        q_eval = q
        mentah = self.index.cari(q, k=TOP_K + 1)

        # Lanjutan langsung setelah memilih dari menu: gabung dengan topik yang baru dipilih.
        if self._terakhir_menu and len(q.split()) <= 4 and LANJUTAN.search(q):
            q_eval = self._terakhir_menu + " " + q
            mentah = self.index.cari(q_eval, k=TOP_K + 1)

        # Pertanyaan lanjutan pendek ("kalau syaratnya?") -> gabung dengan pertanyaan KB sebelumnya.
        # Hanya jika SEMUA katanya dikenal KB; "siapa presiden pertama?" bukan pertanyaan lanjutan.
        if ((not mentah or mentah[0].skor < THRESHOLD_MIRIP) and len(q.split()) <= 4
                and tokenize(q) and not self.index.ada_kata_asing(q)):
            sebelumnya = [p for p, _, m in self.riwayat if m in ("kb", "llm")]
            if sebelumnya:
                q_eval = sebelumnya[-1] + " " + q
                mentah = self.index.cari(q_eval, k=TOP_K + 1)

        relevan = [h for h in mentah if h.skor >= THRESHOLD_MIRIP]
        if not relevan:
            return Rute("fallback", alasan="skor_rendah")

        # Apakah pertanyaan menyentuh lebih dari satu topik KB?
        utama = relevan[0]
        # Topik utama harus punya dasar kuat (>= 2 kata cocok atau cakupan tinggi); kalau tidak,
        # ini pertanyaan di luar topik yang kebetulan berbagi satu kata dengan beberapa entri.
        utama_kuat = (utama.cakupan >= CAKUPAN_MIN
                      or self.index.jumlah_token_cocok(q_eval, utama) >= 2)
        topik_lain = [h for h in relevan[1:]
                      if utama_kuat
                      and h.skor >= TOPIK_RASIO_SKOR_MIN * utama.skor
                      and self.index.cakupan_tambahan(q_eval, utama, h) >= TOPIK_TAMBAHAN_MIN]
        multitopik = bool(topik_lain)
        kuat = pertanyaan_kompleks_teks(q) or multitopik
        lemah = bool(KOMPLEKS_LEMAH.search(q))

        if kuat:
            kandidat = relevan[:TOP_K]
            if self.index.cakupan_gabungan(q_eval, kandidat) < CAKUPAN_MIN:
                return Rute("fallback", alasan="salah_topik_majemuk")
            alasan = "multitopik" if multitopik else "pertanyaan_kompleks"
            return Rute("llm", kandidat, alasan, multitopik=multitopik)

        tunggal = [h for h in relevan if h.cakupan >= CAKUPAN_MIN]
        if not tunggal:
            return Rute("fallback", alasan="salah_topik")
        top = tunggal[0]

        if top.skor >= THRESHOLD_SANGAT_YAKIN or (top.skor >= THRESHOLD_YAKIN and not lemah):
            return Rute("kb", [top], "skor_tinggi")
        return Rute("llm", tunggal[:TOP_K], "skor_sedang_lemah" if lemah else "skor_sedang")

    # -- eksekusi ------------------------------------------------------------ #
    def _jawab_dokumen(self, q: str, hits: list[Hasil]) -> Balasan:
        """Tanya-jawab dari dokumen unggahan: potongan dokumen jadi konteks [S#] bagi LLM + guardrail."""
        top = hits[0]
        sumber = [top.entri.sumber]
        if self.llm.tersedia:
            b = self._jawab_llm(q, Rute("llm", hits, "dokumen"))
            if b.mode in ("llm", "fallback"):
                return b
        teks = ("LLM tidak aktif, jadi saya tampilkan bagian dokumen yang paling relevan:\n\n"
                + top.entri.jawaban)
        return Balasan(teks, "alat", top.skor, sumber, alasan="dokumen:tanpa_llm")

    def _proses(self, q: str) -> Balasan:
        r = self.rute(q)
        if r.jalur == "sapaan":
            return Balasan(r.teks, "sapaan", alasan=r.alasan)
        if self.dokumen is not None:
            eksplisit = bool(DOK_RE.search(q))
            if eksplisit or r.jalur == "fallback":
                hits = [h for h in self.dokumen.cari(q) if h.skor >= THRESHOLD_MIRIP]
                if not hits and eksplisit:           # "ringkas dokumen ini": pakai bagian awal
                    hits = [Hasil(e, 0.0) for e in self.dokumen.index.entri[:TOP_K]]  # type: ignore[union-attr]
                if hits:
                    return self._jawab_dokumen(q, hits)
        if r.jalur == "fallback":
            return Balasan(FALLBACK, "fallback", alasan=r.alasan)
        if r.jalur == "kb":
            top = r.hasil[0]
            return Balasan(top.entri.jawaban, "kb", top.skor, [top.entri.sumber], alasan=r.alasan)
        return self._jawab_llm(q, r)

    def _jawab_llm(self, q: str, r: Rute) -> Balasan:
        top = r.hasil[0]
        if not self.llm.tersedia:
            return self._tanpa_llm(r, self.llm.error or "LLM tidak tersedia")

        riwayat_llm = [(p, j) for p, j, m in self.riwayat if m in ("kb", "llm")]

        if hasattr(self.llm, "jawab_tervalidasi"):         # orchestrator multi-model
            j = self.llm.jawab_tervalidasi(q, r.hasil, riwayat_llm, r.alasan)
            if j.semua_error:
                return self._tanpa_llm(r, f"semua model gagal ({'; '.join(j.percobaan) or j.alasan})")
            jejak = "|".join(j.percobaan)
            if not j.lolos:
                return Balasan(FALLBACK, "fallback", top.skor, percobaan=j.percobaan,
                               alasan=f"guardrail:{j.alasan}|{jejak}")
            sumber = list(dict.fromkeys(r.hasil[n - 1].entri.sumber for n in j.sitasi))
            return Balasan(j.teks, "llm", top.skor, sumber, alasan=f"{r.alasan}|{jejak}",
                           model=j.model, percobaan=j.percobaan)

        try:
            teks = self.llm.jawab(q, r.hasil, riwayat_llm)
        except Exception as exc:  # jaringan / kuota / dsb. -> turun ke jalur tanpa LLM
            return self._tanpa_llm(r, f"LLM error: {type(exc).__name__}")

        v = validasi_jawaban(teks, teks_konteks(r.hasil))
        if not v.lolos:
            # Jawaban tanpa dasar konteks ditolak (anti-halusinasi)
            return Balasan(FALLBACK, "fallback", top.skor, alasan=f"guardrail:{v.alasan}")

        sumber = list(dict.fromkeys(r.hasil[n - 1].entri.sumber for n in v.sitasi))
        return Balasan(teks, "llm", top.skor, sumber, alasan=r.alasan)

    def _tanpa_llm(self, r: Rute, alasan_llm: str) -> Balasan:
        """Cadangan bila LLM mati/error: tetap berikan jawaban terverifikasi dari KB."""
        top = r.hasil[0]
        if r.multitopik:
            # Pertanyaan majemuk: tampilkan jawaban tiap topik apa adanya.
            bagian = [f"{h.entri.pertanyaan}\n{h.entri.jawaban}" for h in r.hasil]
            sumber = list(dict.fromkeys(h.entri.sumber for h in r.hasil))
            teks = "Pertanyaan Anda mencakup beberapa topik. Berikut jawaban resminya:\n\n" \
                   + "\n\n".join(bagian)
            return Balasan(teks, "kb", top.skor, sumber, alasan=f"{r.alasan}|tanpa_llm:{alasan_llm}")
        if top.skor >= THRESHOLD_YAKIN:
            return Balasan(top.entri.jawaban, "kb", top.skor, [top.entri.sumber],
                           alasan=f"{r.alasan}|tanpa_llm:{alasan_llm}")
        saran = "\n".join(f"  - {h.entri.pertanyaan}" for h in r.hasil)
        teks = (f"Saya belum yakin dengan maksud Anda ({alasan_llm}). "
                f"Apakah salah satu topik ini yang Anda maksud?\n{saran}")
        return Balasan(teks, "saran", top.skor, alasan=f"{r.alasan}|tanpa_llm:{alasan_llm}")

    def sesi_baru(self) -> "Chatbot":
        """Chatbot baru dengan riwayat kosong yang memakai indeks & LLM yang sama."""
        bot = Chatbot(llm=self.llm, log_path=self.log_path, index=self.index,
                      data=self.data, menu=self.menu)
        bot.sekarang = self.sekarang
        return bot

    # -- util ---------------------------------------------------------------- #
    def _hanya_terima_kasih(self, q: str) -> bool:
        """True bila pesan hanya ucapan terima kasih (bukan 'terima kasih, tapi bagaimana cuti?')."""
        if not TERIMA_KASIH.search(q) or "?" in q:
            return False
        sisa = TERIMA_KASIH.sub(" ", q)
        return len(tokenize(sisa)) <= 2 and not self.index.cari(sisa)

    def _log(self, q: str, b: Balasan) -> None:
        if self.log_path is None:
            return
        try:
            Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "waktu": datetime.now().isoformat(timespec="seconds"),
                    "pertanyaan": q, "mode": b.mode, "alasan": b.alasan,
                    "skor": round(b.skor, 3), "ms": round(b.waktu_ms, 1),
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass
