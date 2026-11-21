# Hasil Evaluasi Router AkademikBot

- Jumlah kasus uji: **115**
- Akurasi jalur router: **98.3%**
- Akurasi entri KB (jalur kb): **97.6%**
- Akurasi held-out (52 kasus di luar tuning): **98.1%**

## Confusion matrix

| harapan \ prediksi | kb | llm | fallback | sapaan |
|---|---|---|---|---|
| kb | 80 | 2 | 0 | 0 |
| llm | 0 | 13 | 0 | 0 |
| fallback | 0 | 0 | 16 | 0 |
| sapaan | 0 | 0 | 0 | 4 |

## Detail per kasus

| Pertanyaan | Harapan | Prediksi | Entri | Skor | Alasan | OK |
|---|---|---|---|---|---|---|
| Bagaimana cara mengisi KRS? | kb | kb | krs-01 | 0.54 | skor_tinggi | ya |
| kapan pengisian KRS dibuka | kb | kb | krs-01 | 0.57 | skor_tinggi | ya |
| gimana registrasi mata kuliah online | kb | kb | krs-01 | 0.53 | skor_tinggi | ya |
| langkah-langkah mengisi KRS | kb | kb | krs-01 | 0.54 | skor_tinggi | ya |
| berapa sks maksimal per semester | kb | kb | sks-01 | 0.66 | skor_tinggi | ya |
| maksimal sks yang boleh diambil | kb | kb | sks-01 | 0.62 | skor_tinggi | ya |
| bagaimana prosedur cuti akademik | kb | kb | cuti-01 | 0.61 | skor_tinggi | ya |
| gmn cara cuti kuliah? | kb | kb | cuti-01 | 0.49 | skor_tinggi | ya |
| Apa saja syarat cuti akademik? | kb | kb | cuti-01 | 0.57 | skor_tinggi | ya |
| Halo, bagaimana cara cuti? | kb | kb | cuti-01 | 0.49 | skor_tinggi | ya |
| terima kasih, tapi bagaimana cara cuti? | kb | kb | cuti-01 | 0.49 | skor_tinggi | ya |
| syarat mengajukan skripsi | kb | kb | skripsi-01 | 0.59 | skor_tinggi | ya |
| kapan boleh ambil skripsi | kb | kb | skripsi-01 | 0.47 | skor_tinggi | ya |
| ujian susulan kalau sakit | kb | kb | ujian-01 | 0.66 | skor_tinggi | ya |
| cara menghitung IPK | kb | kb | nilai-01 | 0.53 | skor_tinggi | ya |
| bagaimana cara daftar beasiswa | kb | kb | beasiswa-01 | 0.63 | skor_tinggi | ya |
| cara minta surat keterangan aktif kuliah | kb | kb | legalisir-01 | 0.68 | skor_tinggi | ya |
| siapa dosen PA saya | kb | kb | pa-01 | 0.51 | skor_tinggi | ya |
| kontak sekretariat prodi | kb | kb | kontak-01 | 0.69 | skor_tinggi | ya |
| kapan jadwal UTS | kb | kb | kalender-01 | 0.47 | skor_tinggi | ya |
| prosedur kerja praktik | kb | kb | magang-01 | 0.70 | skor_tinggi | ya |
| syarat daftar sidang dan wisuda | kb | kb | sidang-01 | 0.69 | skor_tinggi | ya |
| nilai E bisa mengulang? | kb | kb | mengulang-01 | 0.63 | skor_tinggi | ya |
| batas maksimal masa studi | kb | kb | batasstudi-01 | 0.69 | skor_tinggi | ya |
| Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti? | llm | llm | ujian-01 | 0.33 | multitopik | ya |
| Bandingkan cuti akademik dengan tidak mengisi KRS, apa bedanya? | llm | llm | krs-01 | 0.46 | multitopik | ya |
| Kalau saya cuti, apakah SKS semester depan dan beasiswa saya terpengaruh? | llm | llm | cuti-01 | 0.34 | pertanyaan_kompleks | ya |
| Apakah nilai E mempengaruhi syarat skripsi dan IPK saya? | llm | llm | nilai-01 | 0.39 | multitopik | ya |
| Saya mau ambil magang sekaligus skripsi semester ini, boleh? | llm | llm | skripsi-01 | 0.35 | pertanyaan_kompleks | ya |
| Cara mengisi KRS dan tugas dosen PA apa saja? | llm | llm | pa-01 | 0.54 | multitopik | ya |
| Setelah lulus sidang, apa yang harus diurus untuk wisuda dan surat keterangan lulus? | llm | llm | sidang-01 | 0.51 | multitopik | ya |
| Berapa biaya UKT semester depan? | fallback | fallback | - | 0.00 | salah_topik | ya |
| Siapa presiden Indonesia pertama? | fallback | fallback | - | 0.00 | salah_topik | ya |
| resep nasi goreng enak | fallback | fallback | - | 0.00 | salah_topik | ya |
| cara install python di windows | fallback | fallback | - | 0.00 | skor_rendah | ya |
| Berapa gaji dosen? | fallback | fallback | - | 0.00 | salah_topik | ya |
| bagaimana cara pindah prodi? | fallback | fallback | - | 0.00 | salah_topik | ya |
| jam buka perpustakaan | fallback | fallback | - | 0.00 | salah_topik | ya |
| asdfgh qwerty | fallback | fallback | - | 0.00 | skor_rendah | ya |
| Halo | sapaan | sapaan | - | 0.00 | sapaan | ya |
| Selamat pagi | sapaan | sapaan | - | 0.00 | sapaan | ya |
| terima kasih banyak | sapaan | sapaan | - | 0.00 | terima_kasih | ya |
| Makasih ya | sapaan | sapaan | - | 0.00 | terima_kasih | ya |
| tata cara registrasi KRS online | kb | kb | krs-01 | 0.54 | skor_tinggi | ya |
| berapa batas SKS yang bisa saya ambil | kb | kb | sks-01 | 0.49 | skor_tinggi | ya |
| mau ajukan cuti kuliah semester depan | kb | kb | cuti-01 | 0.54 | skor_tinggi | ya |
| persyaratan proposal tugas akhir | kb | kb | skripsi-01 | 0.73 | skor_tinggi | ya |
| tidak hadir UAS karena sakit bagaimana | kb | kb | ujian-01 | 0.64 | skor_tinggi | ya |
| rumus IPS dan IPK | kb | kb | nilai-01 | 0.64 | skor_tinggi | ya |
| info pendaftaran beasiswa | kb | kb | beasiswa-01 | 0.66 | skor_tinggi | ya |
| kapan wisuda dan berkas yang disiapkan | kb | kb | sidang-01 | 0.59 | skor_tinggi | ya |
| bagaimana cara bayar SPP lewat bank | fallback | fallback | - | 0.00 | salah_topik | ya |
| rekomendasi laptop untuk kuliah | fallback | fallback | - | 0.00 | salah_topik | ya |
| kapan libur lebaran nasional | fallback | fallback | - | 0.00 | salah_topik | ya |
| Apa beda cuti akademik dan perpanjangan studi, dan apakah keduanya mempengaruhi beasiswa? | llm | llm | cuti-01 | 0.36 | multitopik | ya |
| syarat skrispi apa saja | kb | kb | skripsi-01 | 0.54 | skor_tinggi | ya |
| gmn cra mendaftar benasiswa | kb | kb | beasiswa-01 | 0.63 | skor_tinggi | ya |
| prosedur wisdua dan yudisium | kb | kb | sidang-01 | 0.61 | skor_tinggi | ya |
| bagaimana cara bayar spp | fallback | fallback | - | 0.00 | skor_rendah | ya |
| jadwal parkir kampus | fallback | fallback | - | 0.00 | salah_topik | ya |
| berapa persen kehadiran minimal supaya bisa ikut UAS | kb | kb | presensi-01 | 0.68 | skor_tinggi | ya |
| kalau saya sering absen masih boleh ujian akhir ga | kb | kb | presensi-01 | 0.58 | skor_tinggi | ya |
| nilai saya salah, gimana cara komplain ke dosen | kb | kb | sanggah-01 | 0.58 | skor_tinggi | ya |
| prosedur sanggah nilai akhir | kb | kb | sanggah-01 | 0.51 | skor_tinggi | ya |
| ktm saya hilang harus bagaimana | kb | kb | ktm-01 | 0.59 | skor_tinggi | ya |
| cara cetak ulang kartu mahasiswa yang rusak | kb | kb | ktm-01 | 0.74 | skor_tinggi | ya |
| lupa password e-learning gimana reset nya | kb | kb | elearning-01 | 0.58 | skor_tinggi | ya |
| tidak bisa login akun sistem akademik | kb | kb | elearning-01 | 0.53 | skor_tinggi | ya |
| aturan praktikum di laboratorium | kb | kb | lab-01 | 0.68 | skor_tinggi | ya |
| kalau tidak ikut praktikum bagaimana | kb | kb | lab-01 | 0.48 | skor_tinggi | ya |
| cara daftar ukm kampus | kb | kb | ukm-01 | 0.54 | skor_tinggi | ya |
| mau ikut himpunan mahasiswa | kb | kb | ukm-01 | 0.50 | skor_tinggi | ya |
| bagaimana ikut program MBKM | kb | kb | mbkm-01 | 0.48 | skor_tinggi | ya |
| konversi sks kegiatan merdeka belajar | kb | kb | mbkm-01 | 0.62 | skor_tinggi | ya |
| apakah wajib punya sertifikat TOEFL untuk yudisium | kb | kb | toefl-01 | 0.57 | skor_tinggi | ya |
| skor bahasa inggris minimal untuk lulus | kb | kb | toefl-01 | 0.73 | skor_tinggi | ya |
| batas plagiarisme skripsi berapa persen | kb | kb | plagiat-01 | 0.57 | skor_tinggi | ya |
| cek similarity turnitin tugas akhir | kb | kb | plagiat-01 | 0.61 | skor_tinggi | ya |
| minimal berapa kali bimbingan skripsi | kb | kb | bimbingan-01 | 0.64 | skor_tinggi | ya |
| lembar bimbingan tugas akhir | kb | kb | bimbingan-01 | 0.60 | skor_tinggi | ya |
| cara minta surat rekomendasi dosen | kb | kb | rekomendasi-01 | 0.72 | skor_tinggi | ya |
| format permohonan surat rekomendasi untuk beasiswa | kb | kb | rekomendasi-01 | 0.78 | skor_tinggi | ya |
| daftar lomba mewakili kampus dapat dana | kb | kb | prestasi-01 | 0.72 | skor_tinggi | ya |
| pendanaan mengikuti kompetisi mahasiswa | kb | kb | prestasi-01 | 0.55 | skor_tinggi | ya |
| ada layanan konseling untuk mahasiswa? | kb | kb | konseling-01 | 0.65 | skor_tinggi | ya |
| saya butuh konsultasi psikologi | kb | kb | konseling-01 | 0.50 | skor_tinggi | ya |
| nama saya salah tulis di data mahasiswa | kb | kb | datadiri-01 | 0.58 | skor_tinggi | ya |
| cara ganti alamat dan nomor telepon di sistem akademik | kb | kb | datadiri-01 | 0.53 | skor_tinggi | ya |
| dosen tidak hadir apa ada kelas pengganti | kb | kb | kelas-01 | 0.67 | skor_tinggi | ya |
| kuliah dibatalkan, jadwal penggantinya bagaimana | kb | kb | kelas-01 | 0.60 | skor_tinggi | ya |
| minimal berapa sks untuk ambil kerja praktik | kb | kb | magangsyarat-01 | 0.80 | skor_tinggi | ya |
| kapan boleh mulai magang | kb | llm | magangsyarat-01 | 0.36 | skor_sedang | TIDAK |
| Kalau dosen tidak hadir dan presensi saya kurang dari batas, apakah masih boleh ikut UAS? | llm | llm | presensi-01 | 0.74 | pertanyaan_kompleks | ya |
| Saya mau kerja praktik, apa syarat SKS-nya dan bagaimana bimbingan skripsi nanti? | llm | llm | magangsyarat-01 | 0.62 | multitopik | ya |
| Bagaimana cara ikut MBKM dan apakah perlu sertifikat TOEFL untuk yudisium? | llm | llm | toefl-01 | 0.47 | multitopik | ya |
| berapa biaya wifi kampus | fallback | fallback | - | 0.00 | salah_topik | ya |
| siapa rektor universitas sekarang | fallback | fallback | - | 0.00 | skor_rendah | ya |
| jadwal kuliah semester 3 | kb | kb | jadwal-s3 | 0.84 | skor_tinggi | ya |
| jadwal hari senin semester 3 | kb | kb | jadwal-s3-senin | 0.96 | skor_tinggi | ya |
| jadwal selasa semester 5 | kb | kb | jadwal-s5-selasa | 0.89 | skor_tinggi | ya |
| kuliah apa hari kamis semester 1 | kb | kb | jadwal-s1-kamis | 0.95 | skor_tinggi | ya |
| mata kuliah apa saja di semester 5 | kb | kb | sem-5 | 0.66 | skor_tinggi | ya |
| daftar matkul semester 8 | kb | kb | sem-8 | 0.86 | skor_tinggi | ya |
| berapa sks sistem operasi | kb | kb | mk-INF.62.0014 | 0.86 | skor_tinggi | ya |
| dosen pengampu jaringan komputer | kb | kb | mk-INF.62.0015 | 0.85 | skor_tinggi | ya |
| kode mata kuliah kriptografi | kb | kb | mk-INF.62.0028 | 0.81 | skor_tinggi | ya |
| bahasa jepang berapa sks | kb | kb | mk-UNP.60.0008 | 0.83 | skor_tinggi | ya |
| ruang kuliah pemrograman web | kb | kb | mk-INF.62.0011 | 0.87 | skor_tinggi | ya |
| sistem operasi semester berapa | kb | kb | mk-INF.62.0014 | 0.85 | skor_tinggi | ya |
| jam kuliah pertama | kb | kb | jamkuliah-01 | 0.49 | skor_tinggi | ya |
| total sks tiap semester | kb | kb | kurikulum-ringkasan | 0.49 | skor_tinggi | ya |
| dimana lab jaringan | kb | llm | gedung-01 | 0.35 | skor_sedang | TIDAK |
| Bandingkan beban SKS semester 4 dan semester 6 | llm | llm | sks-01 | 0.55 | multitopik | ya |
| Siapa dosen Sistem Operasi dan jadwal semester 3 hari Selasa? | llm | llm | jadwal-s3-selasa | 0.46 | multitopik | ya |
| cuaca hari ini di padang | fallback | fallback | - | 0.00 | skor_rendah | ya |
