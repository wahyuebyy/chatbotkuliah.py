"""
surat.py  -  Generator draf surat / email / WhatsApp akademik (tanpa LLM; template tetap, siap salin).

Placeholder yang harus diisi pengguna ditulis dalam kurung siku: [Nama], [NIM], [Mata Kuliah], dst.
Bila nama mata kuliah disebut di permintaan (mis. "email izin Sistem Operasi"), [Mata Kuliah] diisi otomatis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Permintaan membuat draf: kata kerja pembuat + objek pesan. ("cara membuat surat" = pertanyaan prosedur, bukan draf)
PERMINTAAN = re.compile(
    r"\b(buatkan|buat|bikinkan|bikin|tuliskan|tulis|susunkan|susun|draf|draft|template|contoh)\b"
    r".*\b(email|e-mail|surel|surat|wa|whatsapp|chat|pesan)\b", re.I)

KANAL_WA = re.compile(r"\b(wa|whatsapp|chat|pesan singkat|pesan)\b", re.I)
KANAL_SURAT = re.compile(r"\bsurat\b", re.I)


@dataclass
class Jenis:
    kunci: str
    judul: str
    kata: tuple[str, ...]
    subjek: str
    isi: str          # badan formal (email & surat)
    wa: str           # versi singkat WhatsApp


JENIS: list[Jenis] = [
    Jenis("ujian-susulan", "permohonan ujian susulan",
          ("susulan", "tidak bisa ikut ujian", "tidak ikut ujian", "tidak dapat mengikuti ujian", "izin ujian"),
          "Permohonan Ujian Susulan [Mata Kuliah] - [Nama] ([NIM])",
          "Yth. Bapak/Ibu [Nama Dosen],\n\nSaya yang bertanda tangan di bawah ini:\nNama   : [Nama]\nNIM    : [NIM]\nProdi  : Informatika\n\n"
          "memohon izin untuk mengikuti ujian susulan mata kuliah [Mata Kuliah] karena tidak dapat mengikuti "
          "ujian pada [Tanggal] disebabkan [Alasan]. Bukti pendukung (surat dokter/keterangan lain) saya lampirkan.\n\n"
          "Atas perhatian dan kebijaksanaan Bapak/Ibu, saya ucapkan terima kasih.",
          "Assalamualaikum, selamat [pagi/siang/sore] Bapak/Ibu [Nama Dosen]. Saya [Nama] ([NIM]) mahasiswa mata kuliah "
          "[Mata Kuliah]. Mohon izin mengajukan ujian susulan karena tidak dapat mengikuti ujian pada [Tanggal] "
          "disebabkan [Alasan]. Bukti pendukung saya lampirkan. Terima kasih, Bapak/Ibu."),
    Jenis("izin", "izin tidak masuk kuliah",
          ("izin", "tidak masuk", "absen", "berhalangan", "tidak hadir", "sakit"),
          "Izin Tidak Mengikuti Perkuliahan [Mata Kuliah] - [Nama] ([NIM])",
          "Yth. Bapak/Ibu [Nama Dosen],\n\nSaya yang bertanda tangan di bawah ini:\nNama   : [Nama]\nNIM    : [NIM]\nProdi  : Informatika\n\n"
          "memohon izin tidak dapat mengikuti perkuliahan [Mata Kuliah] pada [Tanggal] karena [Alasan]. "
          "Saya akan mempelajari materi yang tertinggal dan mengerjakan tugas yang diberikan.\n\n"
          "Atas pengertian Bapak/Ibu, saya ucapkan terima kasih.",
          "Assalamualaikum, selamat [pagi/siang/sore] Bapak/Ibu [Nama Dosen]. Saya [Nama] ([NIM]) dari kelas "
          "[Mata Kuliah]. Mohon izin tidak dapat mengikuti perkuliahan pada [Tanggal] karena [Alasan]. "
          "Saya akan mengejar materi dan tugas yang tertinggal. Terima kasih atas pengertiannya, Bapak/Ibu."),
    Jenis("bimbingan", "bimbingan skripsi / tugas akhir",
          ("bimbingan", "skripsi", "tugas akhir", "pembimbing", "konsultasi"),
          "Permohonan Jadwal Bimbingan Skripsi - [Nama] ([NIM])",
          "Yth. Bapak/Ibu [Nama Dosen],\n\nSaya [Nama] (NIM [NIM]), mahasiswa Prodi Informatika, mahasiswa bimbingan "
          "Bapak/Ibu dengan judul skripsi \"[Judul Skripsi]\". Saya bermaksud berkonsultasi mengenai [Topik Bimbingan] "
          "dan mohon kesediaan Bapak/Ibu untuk menjadwalkan bimbingan pada [Hari/Tanggal] pukul [Jam] "
          "(atau waktu lain yang Bapak/Ibu tentukan). Draf terbaru saya lampirkan pada email ini.\n\n"
          "Terima kasih atas bimbingan dan waktu Bapak/Ibu.",
          "Assalamualaikum, selamat [pagi/siang/sore] Bapak/Ibu [Nama Dosen]. Saya [Nama] ([NIM]), mahasiswa bimbingan "
          "skripsi Bapak/Ibu. Mohon izin menjadwalkan bimbingan mengenai [Topik Bimbingan] pada [Hari/Tanggal] "
          "pukul [Jam], atau waktu lain yang Bapak/Ibu berkenan. Draf terbaru akan saya kirimkan. Terima kasih, Bapak/Ibu."),
    Jenis("cuti", "permohonan cuti akademik", ("cuti",),
          "Permohonan Cuti Akademik Semester [Semester] - [Nama] ([NIM])",
          "Yth. Ketua Program Studi Informatika,\n\nSaya yang bertanda tangan di bawah ini:\nNama   : [Nama]\nNIM    : [NIM]\n"
          "Semester: [Semester]\n\nmengajukan permohonan cuti akademik pada semester [Semester Cuti] dengan alasan [Alasan]. "
          "Saya telah memahami ketentuan cuti akademik yang berlaku dan melampirkan dokumen persyaratan.\n\n"
          "Demikian permohonan ini saya sampaikan. Atas persetujuan Bapak/Ibu, saya ucapkan terima kasih.",
          "Selamat [pagi/siang/sore], Bapak/Ibu admin Prodi. Saya [Nama] ([NIM]) semester [Semester]. Saya ingin menanyakan "
          "dan mengajukan cuti akademik semester [Semester Cuti] karena [Alasan]. Mohon info prosedur dan berkas yang "
          "diperlukan. Terima kasih."),
    Jenis("aktif", "surat keterangan aktif kuliah",
          ("keterangan aktif", "aktif kuliah", "legalisir", "surat keterangan"),
          "Permohonan Surat Keterangan Aktif Kuliah - [Nama] ([NIM])",
          "Yth. Bapak/Ibu Admin Program Studi Informatika,\n\nSaya [Nama], NIM [NIM], semester [Semester], memohon "
          "diterbitkannya surat keterangan aktif kuliah untuk keperluan [Keperluan]. Saya siap melengkapi berkas "
          "yang diperlukan.\n\nTerima kasih atas bantuan Bapak/Ibu.",
          "Selamat [pagi/siang/sore], Bapak/Ibu admin Prodi. Saya [Nama] ([NIM]) semester [Semester]. Mohon info prosedur "
          "pengajuan surat keterangan aktif kuliah untuk keperluan [Keperluan]. Terima kasih."),
    Jenis("sanggah-nilai", "sanggahan / klarifikasi nilai", ("sanggah", "nilai", "komplain"),
          "Permohonan Klarifikasi Nilai [Mata Kuliah] - [Nama] ([NIM])",
          "Yth. Bapak/Ibu [Nama Dosen],\n\nSaya [Nama] (NIM [NIM]), mahasiswa mata kuliah [Mata Kuliah], memohon klarifikasi atas nilai "
          "yang saya terima ([Nilai]). Menurut perhitungan saya, [Alasan/Dasar Keberatan]. Mohon kesediaan Bapak/Ibu "
          "meninjau kembali atau memberi kesempatan berdiskusi pada [Hari/Tanggal].\n\nTerima kasih atas perhatian Bapak/Ibu.",
          "Assalamualaikum, selamat [pagi/siang/sore] Bapak/Ibu [Nama Dosen]. Saya [Nama] ([NIM]) mahasiswa [Mata Kuliah]. "
          "Mohon izin berdiskusi tentang nilai saya ([Nilai]) karena [Alasan/Dasar Keberatan]. Kapan Bapak/Ibu "
          "berkenan? Terima kasih."),
    Jenis("rekomendasi", "permohonan surat rekomendasi", ("rekomendasi",),
          "Permohonan Surat Rekomendasi - [Nama] ([NIM])",
          "Yth. Bapak/Ibu [Nama Dosen],\n\nSaya [Nama] (NIM [NIM]), mahasiswa Prodi Informatika yang pernah mengikuti "
          "mata kuliah [Mata Kuliah] pada Bapak/Ibu. Saya memohon kesediaan Bapak/Ibu menuliskan surat rekomendasi untuk "
          "[Tujuan: beasiswa/magang/studi lanjut] dengan batas pengumpulan [Tanggal]. Data pendukung (CV, transkrip) saya lampirkan.\n\n"
          "Terima kasih atas kesediaan Bapak/Ibu.",
          "Assalamualaikum, selamat [pagi/siang/sore] Bapak/Ibu [Nama Dosen]. Saya [Nama] ([NIM]), mahasiswa [Mata Kuliah]. "
          "Mohon kesediaan Bapak/Ibu menulis surat rekomendasi untuk [Tujuan] (batas [Tanggal]). CV & transkrip akan saya "
          "kirim. Terima kasih."),
]

PENUTUP_FORMAL = "\n\nHormat saya,\n[Nama]\nNIM [NIM]\nProgram Studi Informatika\nKontak: [No. HP/Email]"
CATATAN = "Ganti semua teks dalam [kurung siku] sebelum dikirim, dan hapus bagian yang tidak relevan."


def kenali_jenis(q: str) -> Optional[Jenis]:
    """Jenis dengan kata kunci terpanjang yang cocok (frasa spesifik menang atas kata umum)."""
    t = q.lower()
    terbaik, panjang = None, 0
    for j in JENIS:
        p = max((len(k) for k in j.kata if k in t), default=0)
        if p > panjang:
            terbaik, panjang = j, p
    return terbaik


def kenali_kanal(q: str) -> str:
    if re.search(r"\b(email|e-mail|surel)\b", q, re.I):
        return "email"
    if KANAL_WA.search(q) and not KANAL_SURAT.search(q):
        return "wa"
    if KANAL_SURAT.search(q):
        return "surat"
    return "email"


def daftar_jenis() -> str:
    return "\n".join(f"- {j.judul}" for j in JENIS)


def buat_draf(q: str, matkul: Optional[str] = None) -> Optional[str]:
    """Teks draf siap salin; None bila `q` bukan permintaan draf. Jenis tak dikenal -> daftar pilihan."""
    if not PERMINTAAN.search(q):
        return None
    j = kenali_jenis(q)
    if j is None:
        return ("Saya bisa membuatkan draf (email / WhatsApp / surat) untuk:\n" + daftar_jenis()
                + "\n\nContoh: \"buatkan email izin tidak masuk kuliah\" atau \"draft WA bimbingan skripsi\".")
    kanal = kenali_kanal(q)
    sakit = bool(re.search(r"\bsakit\b", q, re.I))
    if kanal == "wa":
        isi = j.wa
        kepala = f"Draf WhatsApp - {j.judul} (siap salin):"
    elif kanal == "surat":
        isi = f"[Kota], [Tanggal]\n\nKepada Yth.\nBapak/Ibu [Nama Dosen/Pejabat]\nProgram Studi Informatika\n\n" \
              f"Perihal: {j.subjek.split(' - ')[0]}\n\n{j.isi}{PENUTUP_FORMAL}"
        kepala = f"Draf surat - {j.judul} (siap salin):"
    else:
        isi = f"Subjek: {j.subjek}\n\n{j.isi}{PENUTUP_FORMAL}"
        kepala = f"Draf email - {j.judul} (siap salin):"
    if matkul:
        isi = isi.replace("[Mata Kuliah]", matkul)
    if sakit and j.kunci in ("izin", "ujian-susulan"):
        isi = isi.replace("[Alasan]", "sedang sakit (surat keterangan dokter terlampir)")
    return f"{kepala}\n\n{'-' * 40}\n{isi}\n{'-' * 40}\n{CATATAN}"
