# Contoh keluaran LLM DUMMY + guardrail

> LLM dummy adalah tiruan berbasis aturan, bukan model sungguhan. Dibuat oleh `evaluasi/contoh_llm.py`.

## Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti?

### mode `baik` -> hasil: **llm**
- alasan: `multitopik`
- sumber: Panduan Akademik - Bab Evaluasi Hasil Belajar; Pedoman Tugas Akhir Prodi; Panduan Akademik - Bab Status Mahasiswa

```
Apa yang harus dilakukan jika tidak bisa mengikuti ujian: [S1]
Mahasiswa yang berhalangan karena alasan yang sah (misalnya sakit dengan surat dokter) dapat mengajukan ujian susulan kepada dosen pengampu dan Prodi dengan melampirkan bukti pendukung paling lambat sesuai batas waktu yang ditetapkan. [S1]
Apa syarat mengajukan skripsi atau tugas akhir: [S2]
Syarat umum: telah menempuh jumlah SKS minimum yang ditetapkan prodi, tidak ada nilai E pada mata kuliah wajib inti, dan telah lulus mata kuliah metodologi penelitian. Mahasiswa mengajukan judul dan proposal, kemudian prodi menetapkan dosen pembimbing. [S2]
Bagaimana prosedur cuti akademik: [S3]
Cuti akademik diajukan sebelum perkuliahan semester berjalan dimulai: isi formulir cuti, minta persetujuan Dosen PA dan Ketua Prodi, lalu serahkan ke bagian akademik fakultas. Masa cuti umumnya tidak dihitung dalam masa studi, namun ada batas maksimal total cuti selama studi. [S3]
```

### mode `halusinasi` -> hasil: **fallback**
- alasan: `guardrail:angka_tidak_ada_di_konteks:['000', '2', '2.500.000', '500']`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `tanpa_sitasi` -> hasil: **fallback**
- alasan: `guardrail:tanpa_sitasi`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `sitasi_palsu` -> hasil: **fallback**
- alasan: `guardrail:sitasi_tidak_valid:[9]`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `tidak_tahu` -> hasil: **fallback**
- alasan: `guardrail:llm_tidak_tahu`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

## Kalau dosen tidak hadir dan presensi saya kurang dari batas, apakah masih boleh ikut UAS?

### mode `baik` -> hasil: **llm**
- alasan: `pertanyaan_kompleks`
- sumber: Panduan Akademik - Bab Perkuliahan; Panduan Akademik - Bab Evaluasi Hasil Belajar

```
Berapa batas minimal kehadiran agar boleh mengikuti UAS: [S1]
Mahasiswa wajib hadir minimal 75% dari total pertemuan tatap muka tiap mata kuliah agar boleh mengikuti UAS. Ketidakhadiran karena sakit atau tugas kampus dapat dicatat sebagai izin bila disertai surat resmi yang diserahkan ke dosen pengampu. [S1]
Apa yang harus dilakukan jika tidak bisa mengikuti ujian: [S2]
Mahasiswa yang berhalangan karena alasan yang sah (misalnya sakit dengan surat dokter) dapat mengajukan ujian susulan kepada dosen pengampu dan Prodi dengan melampirkan bukti pendukung paling lambat sesuai batas waktu yang ditetapkan. [S2]
Apa yang terjadi jika dosen tidak hadir atau kuliah dibatalkan: [S3]
Jika dosen berhalangan, pertemuan diganti pada jadwal pengganti yang diumumkan melalui e-learning atau perwakilan kelas. Pertemuan yang dibatalkan tidak mengurangi jumlah pertemuan wajib dalam satu semester. [S3]
```

### mode `halusinasi` -> hasil: **fallback**
- alasan: `guardrail:angka_tidak_ada_di_konteks:['000', '2', '2.500.000', '500']`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `tanpa_sitasi` -> hasil: **fallback**
- alasan: `guardrail:tanpa_sitasi`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `sitasi_palsu` -> hasil: **fallback**
- alasan: `guardrail:sitasi_tidak_valid:[9]`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `tidak_tahu` -> hasil: **fallback**
- alasan: `guardrail:llm_tidak_tahu`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

## Saya mau kerja praktik, apa syarat SKS-nya dan bagaimana bimbingan skripsi nanti?

### mode `baik` -> hasil: **llm**
- alasan: `multitopik`
- sumber: Pedoman Kerja Praktik Prodi; Pedoman Tugas Akhir Prodi

```
Berapa SKS minimal sebelum boleh mengambil kerja praktik: [S1]
Kerja praktik dapat diambil setelah mahasiswa menempuh minimal 100 SKS tanpa nilai E pada mata kuliah wajib. Mahasiswa mengajukan tempat dan proposal kerja praktik kepada koordinator kerja praktik Prodi. [S1]
Bagaimana prosedur kerja praktik atau magang: [S2]
Mahasiswa yang memenuhi syarat SKS minimum mengajukan permohonan kerja praktik beserta instansi tujuan kepada Prodi. Setelah disetujui dan dosen pembimbing ditetapkan, mahasiswa melaksanakan kerja praktik, menyusun laporan, lalu mempresentasikannya sesuai jadwal dari Prodi. [S2]
Apa syarat mengajukan skripsi atau tugas akhir: [S3]
Syarat umum: telah menempuh jumlah SKS minimum yang ditetapkan prodi, tidak ada nilai E pada mata kuliah wajib inti, dan telah lulus mata kuliah metodologi penelitian. Mahasiswa mengajukan judul dan proposal, kemudian prodi menetapkan dosen pembimbing. [S3]
```

### mode `halusinasi` -> hasil: **fallback**
- alasan: `guardrail:angka_tidak_ada_di_konteks:['000', '2', '2.500.000', '500']`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `tanpa_sitasi` -> hasil: **fallback**
- alasan: `guardrail:tanpa_sitasi`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `sitasi_palsu` -> hasil: **fallback**
- alasan: `guardrail:sitasi_tidak_valid:[9]`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```

### mode `tidak_tahu` -> hasil: **fallback**
- alasan: `guardrail:llm_tidak_tahu`
- sumber: -

```
Maaf, saya belum menemukan informasi yang terverifikasi untuk pertanyaan itu. Silakan hubungi sekretariat/admin Prodi agar mendapat jawaban yang akurat.
```
