"""
tfidf.py  -  TF-IDF + cosine similarity yang diimplementasikan dari nol (Modul 5).

PENANGGUNG JAWAB: Anggota 2 (NLP & TF-IDF)

Tanpa library ML (sklearn dsb). Rumus:
    tf   = 1 + ln(count)                (sublinear tf)
    idf  = ln((1 + N) / (1 + df)) + 1   (smoothed idf)
    bobot = tf * idf, lalu dinormalisasi L2
    skor  = cosine(query, dokumen) = dot product vektor ternormalisasi
"""

from __future__ import annotations

import difflib
import math
from collections import Counter
from dataclasses import dataclass

from .config import TOP_K, TYPO_CUTOFF, TYPO_PANJANG_MIN
from .kb_loader import Entri
from .preprocessing import tokenize


@dataclass
class Hasil:
    entri: Entri
    skor: float             # cosine similarity (0..1)
    cakupan: float = 0.0    # porsi (berbobot idf) kata pertanyaan yang ditemukan di entri
    idx: int = -1           # posisi entri di indeks


class TfidfIndex:
    """Indeks TF-IDF untuk daftar entri KB."""

    def __init__(self, entri: list[Entri], grup: list[int] | None = None):
        """`grup` (opsional) = label korpus tiap entri (0 = FAQ, 1 = data terstruktur, dst.).
        IDF dihitung PER KORPUS: ratusan entri jadwal yang semuanya memuat kata 'jadwal'/'sks'/'semester'
        tidak boleh menurunkan bobot kata-kata itu pada FAQ. Satu entri tetap dibandingkan lewat cosine
        di ruang IDF korpusnya sendiri, lalu semua hasil diurutkan bersama. Tanpa `grup` = satu korpus."""
        if not entri:
            raise ValueError("Daftar entri KB kosong.")
        if grup is not None and len(grup) != len(entri):
            raise ValueError("panjang `grup` harus sama dengan jumlah entri")
        self.entri = entri
        self.docs = [tokenize(e.teks_indeks()) for e in entri]
        self.grup = list(grup) if grup is not None else [0] * len(entri)
        self.idf_grup: dict[int, dict[str, float]] = {}
        for g in sorted(set(self.grup)):
            ids = [i for i, x in enumerate(self.grup) if x == g]
            df: Counter = Counter()
            for i in ids:
                df.update(set(self.docs[i]))
            self.idf_grup[g] = {t: math.log((1 + len(ids)) / (1 + f)) + 1.0 for t, f in df.items()}
        # IDF gabungan (untuk cakupan, kata asing, typo): korpus berindeks terkecil (FAQ) diutamakan.
        self.idf: dict[str, float] = {}
        for g in sorted(self.idf_grup, reverse=True):
            self.idf.update(self.idf_grup[g])
        self.idf_max = max(self.idf_grup[min(self.idf_grup)].values())
        self.vecs = [self._vektor(d, self.idf_grup[g]) for d, g in zip(self.docs, self.grup)]
        self.sets = [set(d) for d in self.docs]
        self._vocab = sorted(self.idf)
        self._cache_typo: dict[str, str] = {}
        self.koreksi_typo_aktif = True

    # -- tokenisasi + koreksi typo ----------------------------------------- #
    def _koreksi(self, token: str) -> str:
        """Perbaiki salah ketik ringan ('benasiswa' -> 'beasiswa') hanya untuk kata di luar
        kosakata KB. Kata pendek tidak disentuh agar singkatan/kata asing tidak salah dikoreksi."""
        if (not self.koreksi_typo_aktif or token in self.idf
                or len(token) < TYPO_PANJANG_MIN or not token.isalpha()):
            return token
        if token not in self._cache_typo:
            cocok = difflib.get_close_matches(token, self._vocab, n=1, cutoff=TYPO_CUTOFF)
            self._cache_typo[token] = cocok[0] if cocok else token
        return self._cache_typo[token]

    def tokens(self, teks: str) -> list[str]:
        """tokenize() + koreksi typo berbasis kosakata KB."""
        return [self._koreksi(t) for t in tokenize(teks)]

    # -- util ------------------------------------------------------------- #
    def _vektor(self, tokens: list[str], idf: dict[str, float] | None = None,
                penalti_asing: bool = False) -> dict[str, float]:
        """Vektor TF-IDF ternormalisasi L2. `penalti_asing=True`: kata yang tidak dikenal korpus ikut
        dihitung dalam norma (tidak dibuang), sehingga pertanyaan yang separuh katanya asing bagi korpus
        itu (mis. 'lembar bimbingan tugas akhir' terhadap korpus jadwal) tidak mendapat cosine palsu tinggi."""
        idf = self.idf if idf is None else idf
        tf = Counter(tokens)
        v = {t: (1 + math.log(c)) * idf[t] for t, c in tf.items() if t in idf}
        asing = sum(((1 + math.log(c)) * self._bobot(t)) ** 2
                    for t, c in tf.items() if t not in idf) if penalti_asing else 0.0
        norm = math.sqrt(sum(x * x for x in v.values()) + asing) or 1.0
        return {t: x / norm for t, x in v.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(t, 0.0) for t, x in a.items())

    def _bobot(self, token: str) -> float:
        # Kata di luar kosakata KB (mis. "ukt", "presiden") = kata asing -> idf maksimum,
        # sehingga menurunkan cakupan dan mencegah salah-topik.
        return self.idf.get(token, self.idf_max)

    def ada_kata_asing(self, query: str) -> bool:
        """True bila ada kata pertanyaan yang tidak dikenal KB sama sekali (di luar topik)."""
        return any(t not in self.idf for t in set(self.tokens(query)))

    def jumlah_token_cocok(self, query: str, hasil: Hasil) -> int:
        """Berapa kata pertanyaan (berbeda) yang muncul di entri ini."""
        return len(set(self.tokens(query)) & self.sets[hasil.idx])

    # -- cakupan ---------------------------------------------------------- #
    def cakupan_gabungan(self, query: str, hasil: list[Hasil]) -> float:
        """Cakupan kata pertanyaan oleh GABUNGAN beberapa entri (pertanyaan majemuk)."""
        tokens = set(self.tokens(query))
        if not tokens or not hasil:
            return 0.0
        gabung = set().union(*(self.sets[h.idx] for h in hasil))
        total = sum(self._bobot(t) for t in tokens)
        return sum(self.idf[t] for t in tokens if t in gabung) / total

    def cakupan_tambahan(self, query: str, utama: Hasil, lain: Hasil) -> float:
        """Porsi kata pertanyaan yang HANYA dibawa oleh entri `lain` (bukan oleh `utama`).
        Nilai tinggi = pertanyaan menyentuh topik kedua yang berbeda."""
        tokens = set(self.tokens(query))
        if not tokens:
            return 0.0
        total = sum(self._bobot(t) for t in tokens)
        s_utama, s_lain = self.sets[utama.idx], self.sets[lain.idx]
        unik = [t for t in tokens if t in s_lain and t not in s_utama]
        return sum(self.idf[t] for t in unik) / total

    # -- pencarian -------------------------------------------------------- #
    def cari(self, query: str, k: int = TOP_K) -> list[Hasil]:
        """Kembalikan hingga k entri teratas dengan skor cosine > 0."""
        tokens = self.tokens(query)
        utama = min(self.idf_grup)
        qs = {g: self._vektor(tokens, idf, penalti_asing=(g != utama))
              for g, idf in self.idf_grup.items()}
        if not any(qs.values()):
            return []
        uniq = set(tokens)
        total = sum(self._bobot(t) for t in uniq)
        hasil: list[Hasil] = []
        for i, (e, v, st) in enumerate(zip(self.entri, self.vecs, self.sets)):
            cocok = sum(self.idf[t] for t in uniq if t in st)
            cakupan = cocok / total if total else 0.0
            skor = self._cosine(qs[self.grup[i]], v)
            if self.grup[i] != utama:
                # Cosine antar-korpus tidak sebanding; skor korpus data diskalakan dengan cakupan kata
                # pertanyaan supaya entri yang hanya cocok di sebagian kata tidak mengalahkan FAQ.
                skor *= cakupan
            hasil.append(Hasil(e, skor, cakupan, i))
        hasil.sort(key=lambda h: h.skor, reverse=True)
        return [h for h in hasil[:k] if h.skor > 0]
