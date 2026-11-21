# AkademikBot - Chatbot Layanan Akademik Prodi (KB Lokal + TF-IDF & LLM)

Tugas kelompok (project): **integrasi chatbot layanan akademik Prodi dengan LLM**, memakai dua pendekatan:

| Pendekatan | Dipakai untuk | Sifat |
|---|---|---|
| Knowledge base lokal + TF-IDF (Modul 5) | Pertanyaan yang sering muncul | Cepat, pasti, sudah diverifikasi |
| LLM | Pertanyaan beragam / kompleks | **Tidak boleh menjawab dari pengetahuan sendiri**: hanya merangkum potongan KB |

TF-IDF + cosine similarity diimplementasikan **dari nol** (tanpa sklearn).

## Alur router

```
pertanyaan
  |- sapaan / terima kasih ............................ balasan singkat
  |- TF-IDF cari entri KB
       |- skor rendah / kata di luar topik ............ FALLBACK (arahkan ke admin Prodi)
       |- skor tinggi & pertanyaan sederhana .......... JAWAB LANGSUNG dari KB
       |- pertanyaan kompleks / lebih dari satu topik
       |  / skor sedang ............................... LLM + konteks KB (top-3)
                                                          |- lolos guardrail ... jawaban + sumber
                                                          |- gagal guardrail ... FALLBACK
                                                          |- LLM mati/error .... jawaban KB apa adanya
```

### Guardrail anti-halusinasi (`guardrail.py`)
System prompt saja tidak cukup, jadi tiap jawaban LLM diperiksa lagi:

1. LLM menjawab `TIDAK_ADA_INFO` -> ditolak.
2. Tidak ada sitasi `[S#]` -> ditolak.
3. Sitasi ke nomor yang tidak ada (`[S9]`) -> ditolak.
4. Ada angka yang tidak tercantum di konteks (mis. "30 SKS") -> ditolak.
5. Kata isi jawaban kurang berpijak pada konteks, atau terlalu sedikit paragraf bersitasi -> ditolak.

Kolom **Sumber** pada balasan hanya berisi sumber yang benar-benar dikutip LLM.

## Struktur proyek

```
akademikbot/
  config.py          threshold & pengaturan            (Anggota 1)
  kb_loader.py       muat + validasi KB                (Anggota 1)
  data/knowledge_base.json  isi KB (FAQ)               (Anggota 1)
  data_akademik.py   kurikulum + jadwal -> entri KB    (Anggota 1)   [v1.4]
  data/kurikulum.json  data/jadwal.csv  data/jadwal_info.json  data/info_umum.json   [v1.4]
  menu.py            tabel pilihan bertingkat          (Anggota 4)   [v1.4]
  preprocessing.py   stopword, singkatan, stemmer      (Anggota 2)
  tfidf.py           TF-IDF + cosine dari nol          (Anggota 2)
  llm_client.py      pembungkus LLM + prompt           (Anggota 3)
  guardrail.py       validasi jawaban LLM              (Anggota 3)
  router.py          keputusan jalur + eksekusi        (Anggota 4)
  cli.py             antarmuka terminal                (Anggota 4)
  web.py + static/   antarmuka web (tanpa dependensi)  (Anggota 4)
evaluasi/            set uji + skrip evaluasi          (Anggota 4)
tests/               unit test (per anggota)
main.py              titik masuk
```
Pembagian tugas lengkap ada di [PEMBAGIAN_TUGAS.md](PEMBAGIAN_TUGAS.md).

## Menjalankan

```bash
pip install -r requirements.txt          # hanya untuk LLM
export ANTHROPIC_API_KEY=sk-ant-...      # Windows (cmd): set ANTHROPIC_API_KEY=...

python main.py                # mode interaktif
python main.py --demo         # demo otomatis
python main.py --offline      # tanpa LLM (KB + TF-IDF saja)
python main.py --cek-kb       # validasi knowledge base
python main.py --llm-demo      # LLM DUMMY tanpa API key (lihat bagian di bawah)
python main.py --web          # antarmuka web di http://127.0.0.1:8000 (--port, --host)
python main.py --cek-data     # validasi kurikulum.json + jadwal.csv (format & jadwal bentrok)
```
Tanpa API key program tetap jalan: pertanyaan majemuk dijawab dengan menampilkan jawaban KB tiap topik.
Perintah di dalam chat: `/menu`, `/semester 3`, `/topik`, `/riwayat`, `/reset`, `/debug` (tampilkan alasan rute), `/bantuan`, `/keluar`.
Model LLM bisa diganti lewat `CHATBOT_LLM_MODEL`.

## Arsitektur multi-model (Claude, GPT, Gemini)

```
 Pengguna (CLI / Web)
        |
        v
 +------------------+   cari entri    +-----------------------------+
 |  Chatbot (A)     |---------------->|  Knowledge Base bersama     |
 |  router          |<----------------|  (TF-IDF) + riwayat sesi    |
 +------------------+   potongan [S#] +-----------------------------+
   | KB cukup yakin -> jawab langsung dari KB (tanpa LLM)
   | perlu LLM -> kirim alasan rute + konteks [S#]
   v
 +------------------------------+  urutan model menurut jenis tugas
 |  LLM Orchestrator            |  multitopik          : Claude > Gemini > GPT
 |  (llm_orchestrator.py)       |  pertanyaan kompleks : GPT > Claude > Gemini
 +------------------------------+  maksud kurang jelas : Gemini > Claude > GPT
   |         |         |
   v         v         v
 Claude     GPT      Gemini      <- llm_providers.py (REST, tanpa SDK)
   \         |         /
    +--> GUARDRAIL (tiap jawaban) --lolos--> jawaban + sumber
              | gagal / error -> model berikutnya (failover)
              | semua gagal   -> FALLBACK (error jaringan: jawaban KB apa adanya)
    (opsional) model LAIN memverifikasi jawaban terhadap konteks (verifikasi silang)
```

Tiga model tidak "mengobrol" satu sama lain; yang dibagi bersama adalah KB dan konteks `[S#]` yang sama,
dan guardrail yang sama berlaku untuk semuanya, jadi memilih model tidak mengubah aturan anti-halusinasi.

```bash
export ANTHROPIC_API_KEY=...  OPENAI_API_KEY=...  GEMINI_API_KEY=...   # isi yang dimiliki saja
python main.py --multi                 # pakai model yang punya key; model lain dilewati
CHATBOT_VERIFIKASI=1 python main.py --multi   # + verifikasi silang oleh model lain (+1 panggilan)
python main.py --demo --multi-demo     # DUMMY tanpa key: GPT dummy berhalusinasi -> pindah ke Claude
python main.py --demo --multi-demo baik        # ketiganya menjawab baik
python main.py --web --multi           # web multi-model (badge model & jejak failover tampil)
```
Atur urutan model per jenis tugas di `LLM_RUTE` (`config.py`) dan nama model lewat `CHATBOT_LLM_MODEL`,
`CHATBOT_GPT_MODEL`, `CHATBOT_GEMINI_MODEL`. **Nama model bawaan GPT/Gemini hanya tebakan awal**; cek nama
yang berlaku di dashboard penyedia. Adaptor REST GPT & Gemini diuji dengan transport palsu dan server lokal,
belum dengan API sungguhan. Mode `/debug` di CLI menampilkan jejak failover.

## Data dummy & LLM dummy
- **KB dummy**: `knowledge_base.json` kini berisi 31 entri (15 awal + 16 baru: presensi, sanggah nilai, KTM,
  e-learning, laboratorium, UKM, MBKM, TOEFL, plagiarisme, bimbingan skripsi, surat rekomendasi, lomba, konseling,
  data pribadi, kelas pengganti, syarat kerja praktik). **Semua isi/angka hanyalah contoh** (mis. "kehadiran 75%",
  "similarity 25%"), bukan aturan resmi; ganti sebelum dikumpulkan.
- **LLM dummy** (`llm_demo.py`): tiruan klien Anthropic yang merangkum konteks `[S#]` dengan aturan sederhana.
  `python main.py --demo --llm-demo` memperlihatkan jalur LLM lengkap tanpa API key, juga bisa dipakai di web
  (`--web --llm-demo`). Mode lain memperlihatkan guardrail bekerja saat LLM "nakal":
  `--llm-demo halusinasi | tanpa_sitasi | sitasi_palsu | tidak_tahu` (semuanya berakhir di FALLBACK).
  Contoh keluaran semua mode: `evaluasi/contoh_output_llm_dummy.md` (dibuat ulang dengan `python evaluasi/contoh_llm.py`).
  LLM dummy bukan model sungguhan, jadi tidak membuktikan kualitas jawaban LLM asli.

## Antarmuka web
`python main.py --web` menjalankan server bawaan Python (tanpa Flask). Tiap pengunjung punya sesi sendiri
(riwayat terpisah), indeks TF-IDF dipakai bersama. Endpoint: `GET /api/health`, `GET /api/topik`,
`POST /api/chat` (`{"pesan": "...", "sesi": "..."}`), `POST /api/reset`.
Perlindungan dasar: bind ke `127.0.0.1` secara default, batas ukuran body, rate limit 30 chat/menit/IP,
batas jumlah & umur sesi, header keamanan, dan teks selalu dirender dengan `textContent` (anti-XSS).
Jika dibuka ke jaringan (`--host 0.0.0.0`), letakkan di belakang reverse proxy dengan HTTPS dan autentikasi.

## Pengujian

```bash
python -m unittest discover -s tests -t .      # unit test (tanpa API key; LLM memakai objek tiruan)
python evaluasi/jalankan_evaluasi.py           # akurasi router
python evaluasi/jalankan_evaluasi.py --simpan  # simpan laporan ke evaluasi/hasil_evaluasi.md
python evaluasi/jalankan_evaluasi.py --sweep   # bandingkan kombinasi threshold
```

Hasil evaluasi terakhir (97 kasus; 52 di antaranya *held-out*, tidak dipakai saat tuning):
akurasi jalur router **99,0%**, akurasi held-out **98,1%**, akurasi entri KB **98,5%** (86 unit test lolos pada v1.3; 125 pada v1.4).
Satu kasus meleset: "kapan boleh mulai magang" diarahkan ke LLM (entri yang dipilih benar, tetapi skornya sedang).
Detail per kasus ada di `evaluasi/hasil_evaluasi.md`. Catatan jujur: set uji ini kecil dan ditulis oleh
tim yang sama, jadi 100% belum berarti sempurna; tambahkan pertanyaan nyata dari mahasiswa untuk uji yang lebih keras.

## Pembaruan v1.1
- **Sinonim** (`SINONIM` di `preprocessing.py`): "perpanjangan" -> `batas`, "libur" -> `cuti`, dst.
  Memperbaiki kegagalan lama pada pertanyaan "cuti akademik dan perpanjangan studi".
- **Koreksi typo** (`tfidf.py`, `difflib`): "skrispi" -> "skripsi", "benasiswa" -> "beasiswa".
  Hanya untuk kata >= 5 huruf di luar kosakata KB; atur `TYPO_CUTOFF` / `TYPO_PANJANG_MIN` di `config.py`.
- **Antarmuka web** + sesi per pengguna (`Chatbot.sesi_baru()` berbagi indeks & LLM).
- Riwayat sesi dibatasi (`MAKS_RIWAYAT`); log bisa dimatikan dengan `CHATBOT_LOG=0`.
- `.env.example` berisi daftar variabel lingkungan.

## Pembaruan v1.4 - data kuliah UNP, menu tabel pilihan, personalisasi semester

Chatbot kini bisa menjawab **jadwal kuliah, daftar mata kuliah per semester, SKS, dosen, dan ruang**, dan
pengguna bisa memilih dari **tabel bernomor tanpa mengetik**.

### Data (folder `akademikbot/data/`)
| Berkas | Isi | Status |
|---|---|---|
| `kurikulum.json` | 55 mata kuliah, 8 semester, Kurikulum 2025 Informatika (S1) UNP | **asli** (dari dokumen "Daftar Matakuliah"; kolom nilai pribadi sengaja tidak dimasukkan) |
| `jadwal.csv` | jadwal kuliah semester 1, 3, 5, 7 (39 sesi) | **DUMMY** - ganti dengan jadwal resmi |
| `jadwal_info.json` | tahun ajaran + penanda `"dummy": true` | ubah ke `false` setelah data asli diisi |
| `info_umum.json` | jam kuliah, lokasi gedung/lab, perubahan jadwal | **DUMMY** (format sama dengan `knowledge_base.json`) |

**Mengganti jadwal dengan data asli** (cukup edit `jadwal.csv` di Excel/Notepad, simpan sebagai CSV UTF-8):
```
kode,kelas,hari,mulai,selesai,ruang,dosen,jenis
INF.62.0014,A,Selasa,10.00,11.40,R.B201,Nama Dosen Asli,Teori
INF.62.0014,A,Kamis,13.00,15.30,Lab Komputer 2,Nama Dosen Asli,Praktik
```
`kode` harus ada di `kurikulum.json`; `hari` Senin-Minggu; jam `HH.MM` (titik dua juga diterima);
`jenis` Teori/Praktik/Lapangan. Lalu jalankan `python main.py --cek-data`: perintah ini memeriksa format
dan melaporkan **jadwal bentrok** (ruang, dosen, atau kelas yang sama pada jam beririsan). Semester genap
cukup ditambahkan barisnya, entri KB dibangkitkan otomatis. Setelah data asli terisi, set `"dummy": false`
di `jadwal_info.json` agar label "DATA CONTOH" hilang dari jawaban.

### Cara kerja (tanpa mengubah aturan anti-halusinasi)
`data_akademik.py` mengubah data terstruktur menjadi **entri KB** (92 entri: ringkasan kurikulum, daftar
tiap semester, tiap mata kuliah, jadwal per semester dan per hari). Total SKS dan daftar per hari
**dihitung di kode**, bukan oleh LLM. Jadi TF-IDF, router, LLM, guardrail, dan sitasi `[S#]` bekerja sama
seperti entri FAQ biasa, dan guardrail tetap menolak angka/jam yang tidak ada di konteks. Aturan 7 di
`SYSTEM_PROMPT` meminta LLM menyalin nama, jam, ruang, dan dosen persis dari konteks.

Perubahan pendukung yang perlu diketahui (dan dijelaskan saat ditanya dosen):
- **IDF per korpus** (`tfidf.py`, parameter `grup`): ratusan entri jadwal yang semuanya memuat kata
  "jadwal/sks/semester" akan menurunkan bobot kata itu untuk FAQ. Maka IDF FAQ dan IDF data dihitung
  terpisah, lalu hasil diurutkan bersama. Skor korpus data diskalakan oleh *cakupan* kata pertanyaan,
  dan kata yang asing bagi korpus data ikut masuk norma, supaya "lembar bimbingan tugas akhir" tidak
  salah dijawab oleh mata kuliah *Tugas Akhir*.
- **Nomor semester** (`preprocessing.py`): tokenizer membuang angka satu digit, jadi "semester 3" diubah
  menjadi token `semester semester3` agar jadwal semester 3 dan 5 bisa dibedakan.

### Menu tabel pilihan
`/menu` di CLI atau tombol **Menu** di web membuka tabel bernomor bertingkat:

```
MENU UTAMA                                   1 Jadwal kuliah          -> semester -> hari
 1 Jadwal kuliah                             2 Mata kuliah per semester
 2 Mata kuliah per semester                  3 Cari mata kuliah       -> semester -> mata kuliah
 3 Cari mata kuliah                          4 Info & layanan akademik (FAQ per kategori)
 4 Info & layanan akademik                   5 Atur semester saya
 5 Atur semester saya
```
Di CLI ketik nomor, `0` kembali, `q` keluar; mengetik kalimat biasa di tengah menu langsung diproses
sebagai chat. Pilihan akhir menunjuk satu entri KB (jawaban + sumber yang sama dengan chat) dan masuk
riwayat sesi, sehingga lanjutan seperti "kalau dosennya siapa?" tetap nyambung. API web:
`GET /api/menu` dan `POST /api/menu {"jalur": ["jadwal","3","senin"]}` (tanpa status di server; klien
cukup mengirim jalur yang dipilih).

### AI menyesuaikan dengan pengguna
Setelah semester diatur (`/semester 3` atau menu 5), pertanyaan personal dipahami otomatis:
"jadwal hari ini", "besok kuliah apa", "jadwal hari jumat", "jadwal saya", "mata kuliah saya". Router
menulis ulang menjadi pertanyaan eksplisit ("Jadwal kuliah semester 3 hari Selasa?") memakai tanggal hari
ini, lalu jalur biasa (KB -> LLM -> guardrail) berjalan. Akhir pekan dijawab "tidak ada jadwal"; bila
semester belum diatur, bot meminta pengguna mengaturnya. Pertanyaan majemuk
("siapa dosen Sistem Operasi dan jadwal semester 3 hari Selasa?") otomatis ke LLM dengan konteks tiap
topik. Penulisan ulang dilakukan di kode, bukan LLM, sehingga LLM tidak bisa mengarang jadwal.

### LLM dummy
`llm_demo.py` kini memahami jawaban berbaris banyak (jadwal/daftar), jadi
`python main.py --demo --llm-demo` dan `--multi-demo` memperlihatkan jalur LLM untuk data jadwal tanpa
API key. Mode `halusinasi` tetap ditolak guardrail (mis. jam/biaya karangan).

### Hasil pengujian v1.4
125 unit test lolos. Evaluasi router: 115 kasus (18 kasus baru tentang data kuliah), akurasi jalur
**98,3%**; dua kasus meleset: "kapan boleh mulai magang" (lama) dan "dimana lab jaringan" (entri benar,
tetapi skor 0,35 sehingga diarahkan ke LLM, bukan jawaban langsung). Kasus data kuliah ditulis oleh
pengembang yang sama, jadi belum bisa disebut uji independen; tambahkan pertanyaan nyata dari teman.

### Keterbatasan data
- Jadwal dan `info_umum.json` hanya contoh; belum ada pembeda kelas A/B pada menu (kolom `kelas` sudah
  dibaca dan ditampilkan, tetapi menu belum menyaringnya).
- Jumlah SKS semester 4 dan 6 pada dokumen kurikulum menghitung semua mata kuliah pilihan; jawaban bot
  menampilkan SKS wajib, SKS pilihan, dan jumlah pada daftar secara terpisah, tanpa menyimpulkan berapa
  mata kuliah pilihan yang wajib diambil (itu aturan prodi yang belum ada di data).

## Mengganti data

> **Isi `knowledge_base.json` saat ini hanya CONTOH.** Ganti `jawaban` dan `sumber` dengan informasi resmi
> Prodi yang sudah diverifikasi sebelum dikumpulkan/dipakai.

Tiap entri: `id` (unik), `kategori`, `pertanyaan`, `variasi`, `kata_kunci`, `jawaban`, `sumber`.
Semakin banyak variasi dan kata kunci, semakin akurat TF-IDF. Jalankan `python main.py --cek-kb`
setelah mengedit, lalu tambahkan kasus uji baru di `evaluasi/test_cases.json`.

## Keterbatasan
- Stemmer bersifat heuristik (dibantu kamus kata dasar kecil di `preprocessing.py`).
- Jalur LLM diuji dengan LLM tiruan; uji dengan API key sungguhan perlu dilakukan sebelum demo.
- Log percakapan (`logs/chat_log.jsonl`) berisi pertanyaan pengguna dan sudah di-`.gitignore`; matikan dengan `CHATBOT_LOG=0`.
- Koreksi typo berbasis kemiripan string bisa keliru pada kata yang kebetulan mirip dengan kosakata KB; naikkan `TYPO_CUTOFF` bila perlu.

## Pembaruan Tahap 1 (UX & otomatisasi)

| Fitur | Cara pakai |
|---|---|
| `.env` otomatis | Salin `.env.example` -> `.env`, isi key, lalu `pip install -r requirements.txt`. `config.muat_env()` memuatnya otomatis; variabel yang sudah diatur di terminal tidak ditimpa. |
| `jalankan_web.bat` | Klik dua kali (Windows): menjalankan `py main.py --multi --web` dan membuka http://127.0.0.1:8000. |
| Pilihan cepat 1/2/3 | `SARAN_CEPAT` + `saran_cepat()` di `menu.py` (dipakai bersama). CLI: ketik `1`/`2`/`3` setelah jawaban. Web: tombol Quick Reply atau ketik angka; JSON chat memuat `opsi_cepat` dan `dipilih`. |
| Umpan balik 👍/👎 | `POST /feedback` (alias `/api/feedback`). Rating 👎 disimpan ke `logs/feedback_negatif.jsonl` (`CHATBOT_FEEDBACK_PATH`, mati bila `CHATBOT_LOG=0`). |
| Unduh ringkasan chat | Tombol "Unduh Ringkasan Chat" di web (.md / .txt), dibuat di browser. |

Tes: `python -m unittest discover -s tests -t .` (termasuk `tests/test_tahap1.py`).

## Pembaruan Tahap A (all-in-one, data cerdas, asisten mahasiswa)

**Sekali klik:** `jalankan_web.bat` (Windows) atau `python main.py` tanpa argumen -> `--auto`:
`.env` dibuat dari `.env.example` bila belum ada; bila ada API key valid **dan** internet -> `--multi --web`,
selain itu `--offline --web` tanpa pesan error. Port bentrok -> otomatis port berikutnya; browser dibuka otomatis;
paket di `requirements.txt` yang belum ada dipasang (`python -m akademikbot.setup_otomatis --pasang`).
Chat terminal seperti dulu: `python main.py --cli`.

| Fitur | Contoh pertanyaan | Modul |
|---|---|---|
| Jadwal waktu nyata (WIB) | "jadwal hari ini / besok / lusa" (setelah `/semester 3`) | `waktu.py`, `router._sesuaikan` |
| Jadwal dosen | "kapan Dosen Contoh 3 mengajar?" | `alat.py` |
| Ruangan kosong | "ruangan kosong hari Selasa jam 10.00", "lab kosong senin 07.30-09.00" | `alat.py` |
| Hitung mundur kalender + banner web | "berapa hari lagi UAS?" | `kalender.py` (data: `info_umum.json`) |
| Cek SKS & prasyarat | "cek sks: Algoritma, Basis Data, Sistem Operasi \| lulus: ..." | `alat.py`, `kurikulum.json` |
| Kalkulator target IPK | "IPK sekarang 3.40 dari 80 SKS, ambil 20 SKS, target IPK 3.50" | `alat.py` |
| Draf surat/email/WA | "buatkan email izin tidak masuk kuliah" | `surat.py` |
| Unggah dokumen TXT/PDF | tombol "Unggah dokumen" (web) / `/dokumen berkas.pdf` (CLI) | `dokumen.py` |
| Kuis latihan | "buatkan 3 soal latihan Sistem Operasi", "kuis seputar KRS" | `kuis.py` |

Catatan data: **kalender akademik** (`info_umum.json`), **prasyarat** (`kurikulum.json`) dan **jadwal/dosen** masih DATA CONTOH;
ganti dengan data resmi lalu ubah penanda `kalender_dummy` / `prasyarat_dummy` / `jadwal_info.json -> dummy` menjadi `false`.
Jawaban alat bermode `alat` (dihitung di kode, bukan LLM). Soal kuis materi mata kuliah butuh LLM dan diberi label "dibuat AI".
