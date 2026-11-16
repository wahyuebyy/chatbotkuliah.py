
import re
import random
from datetime import datetime

# ==========================================================
# SMART CAMPUS - AI STUDENT ASSISTANT
# Universitas Negeri Padang (Simulasi Akademik)
# ==========================================================


# ==========================================================
# 1. DATA PROFIL MAHASISWA
# ==========================================================

mahasiswa = {
    "nama": "Rifky Ahmad Saputra",
    "nim": "25343155",
    "prodi": "Informatika",
    "departemen": "Teknik Elektronika",
    "fakultas": "Fakultas Teknik",
    "universitas": "Universitas Negeri Padang",
    "semester": 3,
    "tahun_akademik": "2026/2027"
}


# ==========================================================
# 2. DATABASE MATA KULIAH DAN KRS
# ==========================================================

mata_kuliah = [

    {
        "kode": "INF301",
        "nama": "Pemrograman Berorientasi Objek",
        "sks": 3,
        "hari": "Senin",
        "mulai": "07.00",
        "selesai": "09.40",
        "dosen": "Andi Pratama, S.Kom., M.Kom.",
        "ruangan": "Laboratorium Komputer 1"
    },

    {
        "kode": "INF302",
        "nama": "Pendidikan Agama",
        "sks": 2,
        "hari": "Senin",
        "mulai": "10.00",
        "selesai": "12.30",
        "dosen": "Ahmad Fauzi, M.Ag.",
        "ruangan": "Ruang Teori A2"
    },

    {
        "kode": "INF303",
        "nama": "Jaringan Komputer",
        "sks": 3,
        "hari": "Selasa",
        "mulai": "07.00",
        "selesai": "09.40",
        "dosen": "Budi Santoso, S.T., M.T.",
        "ruangan": "Laboratorium Jaringan"
    },

    {
        "kode": "INF304",
        "nama": "Kecerdasan Buatan",
        "sks": 3,
        "hari": "Rabu",
        "mulai": "07.00",
        "selesai": "09.40",
        "dosen": "Rina Marlina, S.Kom., M.Kom.",
        "ruangan": "Ruang Teori B1"
    },

    {
        "kode": "INF305",
        "nama": "Matematika Diskrit",
        "sks": 2,
        "hari": "Rabu",
        "mulai": "10.00",
        "selesai": "12.30",
        "dosen": "Dedi Kurniawan, M.Pd.",
        "ruangan": "Ruang Teori B2"
    },

    {
        "kode": "INF306",
        "nama": "Basis Data",
        "sks": 3,
        "hari": "Kamis",
        "mulai": "07.00",
        "selesai": "09.40",
        "dosen": "Siti Rahmawati, S.Kom., M.Kom.",
        "ruangan": "Laboratorium Komputer 2"
    },

    {
        "kode": "INF307",
        "nama": "Sistem Operasi",
        "sks": 3,
        "hari": "Jumat",
        "mulai": "07.00",
        "selesai": "09.40",
        "dosen": "Fajar Ramadhan, S.Kom., M.T.",
        "ruangan": "Ruang Teori C1"
    },

    {
        "kode": "INF308",
        "nama": "Praktikum Pemrograman",
        "sks": 1,
        "hari": "Jumat",
        "mulai": "10.00",
        "selesai": "11.40",
        "dosen": "Andi Pratama, S.Kom., M.Kom.",
        "ruangan": "Laboratorium Komputer 1"
    }
]


# ==========================================================
# 3. DATABASE JADWAL UJIAN
# ==========================================================

jadwal_ujian = {

    "UTS": [
        {
            "matkul": "Pemrograman Berorientasi Objek",
            "hari": "Senin",
            "tanggal": "12 Oktober 2026",
            "jam": "07.00 - 09.00",
            "ruangan": "Laboratorium Komputer 1"
        },
        {
            "matkul": "Jaringan Komputer",
            "hari": "Selasa",
            "tanggal": "13 Oktober 2026",
            "jam": "07.00 - 09.00",
            "ruangan": "Laboratorium Jaringan"
        },
        {
            "matkul": "Kecerdasan Buatan",
            "hari": "Rabu",
            "tanggal": "14 Oktober 2026",
            "jam": "07.00 - 09.00",
            "ruangan": "Ruang Teori B1"
        }
    ],

    "UAS": [
        {
            "matkul": "Pemrograman Berorientasi Objek",
            "hari": "Senin",
            "tanggal": "14 Desember 2026",
            "jam": "07.00 - 09.00",
            "ruangan": "Laboratorium Komputer 1"
        },
        {
            "matkul": "Jaringan Komputer",
            "hari": "Selasa",
            "tanggal": "15 Desember 2026",
            "jam": "07.00 - 09.00",
            "ruangan": "Laboratorium Jaringan"
        },
        {
            "matkul": "Kecerdasan Buatan",
            "hari": "Rabu",
            "tanggal": "16 Desember 2026",
            "jam": "07.00 - 09.00",
            "ruangan": "Ruang Teori B1"
        }
    ]
}


# ==========================================================
# 4. DATABASE TUGAS PERKULIAHAN
# ==========================================================

daftar_tugas = [

    {
        "matkul": "Pemrograman Berorientasi Objek",
        "tugas": "Membuat program Java menggunakan konsep OOP",
        "deadline": "20 November 2026",
        "status": "Belum dikumpulkan"
    },

    {
        "matkul": "Jaringan Komputer",
        "tugas": "Membuat laporan praktikum routing OSPF",
        "deadline": "23 November 2026",
        "status": "Dalam pengerjaan"
    },

    {
        "matkul": "Kecerdasan Buatan",
        "tugas": "Membuat proyek chatbot menggunakan Python",
        "deadline": "27 November 2026",
        "status": "Belum dikumpulkan"
    },

    {
        "matkul": "Basis Data",
        "tugas": "Membuat rancangan database mahasiswa",
        "deadline": "30 November 2026",
        "status": "Belum dikumpulkan"
    },

    {
        "matkul": "Sistem Operasi",
        "tugas": "Praktikum perintah dasar Linux Ubuntu",
        "deadline": "3 Desember 2026",
        "status": "Dalam pengerjaan"
    }
]


# ==========================================================
# 5. DATABASE KALENDER AKADEMIK
# ==========================================================

kalender_akademik = [

    {
        "kegiatan": "Awal perkuliahan",
        "tanggal": "7 September 2026"
    },

    {
        "kegiatan": "Masa pengisian KRS",
        "tanggal": "31 Agustus - 5 September 2026"
    },

    {
        "kegiatan": "Ujian Tengah Semester",
        "tanggal": "12 - 17 Oktober 2026"
    },

    {
        "kegiatan": "Pengumpulan tugas akhir",
        "tanggal": "7 - 11 Desember 2026"
    },

    {
        "kegiatan": "Ujian Akhir Semester",
        "tanggal": "14 - 19 Desember 2026"
    },

    {
        "kegiatan": "Libur semester",
        "tanggal": "21 Desember 2026"
    }
]


# ==========================================================
# 6. KNOWLEDGE BASE CHATBOT
# ==========================================================

knowledge_base = {

    "jadwal": {
        "keywords": ["jadwal kuliah", "jadwal kelas"],
        "responses": [
            "Silakan sebutkan hari yang ingin kamu lihat.",
            "Saya bisa menampilkan jadwal kuliah dari Senin sampai Jumat."
        ]
    },

    "tugas": {
        "keywords": ["tugas kuliah", "informasi tugas", "deadline tugas"],
        "responses": [
            "Saya bisa membantu menampilkan daftar tugas dan deadline.",
            "Jangan lupa menyelesaikan tugas sebelum batas pengumpulan."
        ]
    },

    "praktikum": {
        "keywords": ["praktikum", "laporan praktikum"],
        "responses": [
            "Praktikum merupakan kegiatan pembelajaran untuk menerapkan teori secara langsung.",
            "Pastikan laporan praktikum memiliki tujuan, teori, alat dan bahan, langkah kerja, hasil, dan kesimpulan."
        ]
    },

    "uts": {
        "keywords": ["uts", "ujian tengah semester"],
        "responses": [
            "UTS merupakan evaluasi pembelajaran yang dilakukan pada pertengahan semester."
        ]
    },

    "uas": {
        "keywords": ["uas", "ujian akhir semester"],
        "responses": [
            "UAS merupakan evaluasi pembelajaran pada akhir semester."
        ]
    },

    "beasiswa": {
        "keywords": ["beasiswa", "bantuan pendidikan"],
        "responses": [
            "Informasi beasiswa dapat diperoleh melalui bagian kemahasiswaan kampus."
        ]
    },

    "organisasi": {
        "keywords": ["organisasi mahasiswa", "ukm", "himpunan mahasiswa"],
        "responses": [
            "Organisasi mahasiswa dapat meningkatkan kemampuan komunikasi, kepemimpinan, dan kerja sama."
        ]
    },

    "perpustakaan": {
        "keywords": ["perpustakaan", "peminjaman buku"],
        "responses": [
            "Perpustakaan kampus dapat digunakan untuk mencari buku dan referensi akademik."
        ]
    }
}


# ==========================================================
# 7. RIWAYAT PERCAKAPAN
# ==========================================================

riwayat = []


# ==========================================================
# 8. FUNGSI NORMALISASI TEKS
# ==========================================================

def normalisasi(teks):

    teks = teks.lower()

    teks = re.sub(r"[^a-z0-9\s]", " ", teks)

    teks = re.sub(r"\s+", " ", teks).strip()

    return teks


# ==========================================================
# 9. FUNGSI MENGHITUNG TOTAL SKS
# ==========================================================

def total_sks():

    return sum(data["sks"] for data in mata_kuliah)


# ==========================================================
# 10. FUNGSI MENAMPILKAN PROFIL MAHASISWA
# ==========================================================

def tampilkan_profil():

    print("\n" + "=" * 55)
    print("              PROFIL MAHASISWA")
    print("=" * 55)

    print("Nama              :", mahasiswa["nama"])
    print("NIM               :", mahasiswa["nim"])
    print("Program Studi     :", mahasiswa["prodi"])
    print("Departemen        :", mahasiswa["departemen"])
    print("Fakultas          :", mahasiswa["fakultas"])
    print("Universitas       :", mahasiswa["universitas"])
    print("Semester          :", mahasiswa["semester"])
    print("Tahun Akademik    :", mahasiswa["tahun_akademik"])

    print("=" * 55)


# ==========================================================
# 11. FUNGSI MENAMPILKAN KRS
# ==========================================================

def tampilkan_krs():

    print("\n" + "=" * 75)
    print("                 KARTU RENCANA STUDI")
    print("=" * 75)

    print("Nama         :", mahasiswa["nama"])
    print("NIM          :", mahasiswa["nim"])
    print("Prodi        :", mahasiswa["prodi"])
    print("Semester     :", mahasiswa["semester"])
    print("Tahun Akademik:", mahasiswa["tahun_akademik"])

    print("-" * 75)

    print(f"{'KODE':<10} {'MATA KULIAH':<38} {'SKS':<5}")

    print("-" * 75)

    for data in mata_kuliah:

        print(
            f"{data['kode']:<10} "
            f"{data['nama']:<38} "
            f"{data['sks']:<5}"
        )

    print("-" * 75)

    print("TOTAL SKS:", total_sks())

    print("=" * 75)


# ==========================================================
# 12. FUNGSI MENAMPILKAN JADWAL HARIAN
# ==========================================================

def jadwal_harian(hari):

    hasil = [
        data for data in mata_kuliah
        if data["hari"].lower() == hari.lower()
    ]

    print(f"\n========== JADWAL HARI {hari.upper()} ==========")

    if not hasil:

        print("Tidak ada jadwal perkuliahan.")

        return

    for data in hasil:

        print("\nMata Kuliah :", data["nama"])
        print("Kode        :", data["kode"])
        print("SKS         :", data["sks"])
        print("Jam         :", data["mulai"], "-", data["selesai"])
        print("Dosen       :", data["dosen"])
        print("Ruangan     :", data["ruangan"])

        print("-" * 45)


# ==========================================================
# 13. FUNGSI MENAMPILKAN SELURUH JADWAL
# ==========================================================

def seluruh_jadwal():

    hari_list = [
        "Senin", "Selasa", "Rabu", "Kamis", "Jumat"
    ]

    for hari in hari_list:

        jadwal_harian(hari)


# ==========================================================
# 14. FUNGSI PENCARIAN MATA KULIAH
# ==========================================================

def cari_matkul(kata):

    kata = normalisasi(kata)

    hasil = []

    for data in mata_kuliah:

        nama = normalisasi(data["nama"])
        kode = normalisasi(data["kode"])

        if kata in nama or kata == kode:
            hasil.append(data)

    return hasil


def tampilkan_matkul(kata):

    hasil = cari_matkul(kata)

    if not hasil:

        print("\nMata kuliah tidak ditemukan.")

        return

    for data in hasil:

        print("\n========== INFORMASI MATA KULIAH ==========")

        print("Kode        :", data["kode"])
        print("Nama        :", data["nama"])
        print("SKS         :", data["sks"])
        print("Hari        :", data["hari"])
        print("Jam         :", data["mulai"], "-", data["selesai"])
        print("Dosen       :", data["dosen"])
        print("Ruangan     :", data["ruangan"])

        print("=" * 45)


# ==========================================================
# 15. FUNGSI PENCARIAN DOSEN
# ==========================================================

def cari_dosen(kata):

    hasil = cari_matkul(kata)

    if not hasil:

        print("\nMata kuliah tidak ditemukan.")
        print("Masukkan nama atau kode mata kuliah.")

        return

    for data in hasil:

        print("\n========== INFORMASI DOSEN ==========")

        print("Mata Kuliah :", data["nama"])
        print("Nama Dosen  :", data["dosen"])
        print("Hari        :", data["hari"])
        print("Jam         :", data["mulai"], "-", data["selesai"])
        print("Ruangan     :", data["ruangan"])

        print("=" * 45)


# ==========================================================
# 16. FUNGSI MENAMPILKAN JADWAL UJIAN
# ==========================================================

def tampilkan_ujian(jenis):

    print(f"\n========== JADWAL {jenis} ==========")

    for data in jadwal_ujian[jenis]:

        print("\nMata Kuliah :", data["matkul"])
        print("Hari        :", data["hari"])
        print("Tanggal     :", data["tanggal"])
        print("Jam         :", data["jam"])
        print("Ruangan     :", data["ruangan"])

        print("-" * 40)


# ==========================================================
# 17. FUNGSI MENAMPILKAN DAFTAR TUGAS
# ==========================================================

def tampilkan_tugas():

    print("\n========== DAFTAR TUGAS MAHASISWA ==========")

    for nomor, data in enumerate(daftar_tugas, 1):

        print(f"\nTugas ke-{nomor}")
        print("Mata Kuliah :", data["matkul"])
        print("Tugas       :", data["tugas"])
        print("Deadline    :", data["deadline"])
        print("Status      :", data["status"])

        print("-" * 45)


# ==========================================================
# 18. FUNGSI KALENDER AKADEMIK
# ==========================================================

def tampilkan_kalender():

    print("\n========== KALENDER AKADEMIK ==========")

    for data in kalender_akademik:

        print("\nKegiatan :", data["kegiatan"])
        print("Tanggal  :", data["tanggal"])

        print("-" * 40)


# ==========================================================
# 19. FUNGSI RIWAYAT PERCAKAPAN
# ==========================================================

def tampilkan_riwayat():

    print("\n========== RIWAYAT PERCAKAPAN ==========")

    if not riwayat:

        print("Belum ada riwayat percakapan.")

        return

    for nomor, data in enumerate(riwayat, 1):

        print(f"\nPercakapan {nomor}")
        print("Waktu     :", data["waktu"])
        print("Mahasiswa :", data["pertanyaan"])
        print("Chatbot   :", data["jawaban"])

        print("-" * 45)


# ==========================================================
# 20. FUNGSI MENDETEKSI INTENT
# ==========================================================

def deteksi_intent(teks):

    teks = normalisasi(teks)

    skor_tertinggi = 0
    intent_terpilih = None

    for intent, data in knowledge_base.items():

        skor = 0

        for keyword in data["keywords"]:

            keyword = normalisasi(keyword)

            pola = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pola, teks):

                skor += len(keyword.split())

        if skor > skor_tertinggi:

            skor_tertinggi = skor
            intent_terpilih = intent

    return intent_terpilih


# ==========================================================
# 21. FUNGSI MEMPROSES PERTANYAAN AKADEMIK
# ==========================================================

def proses_akademik(teks):

    teks = normalisasi(teks)

    # Profil mahasiswa
    if "profil" in teks or "identitas mahasiswa" in teks:
        tampilkan_profil()
        return "Berikut informasi profil mahasiswa."

    # KRS
    if "krs" in teks or "kartu rencana studi" in teks:
        tampilkan_krs()
        return "Berikut daftar KRS mahasiswa."

    # Total SKS
    if "total sks" in teks or "berapa sks" in teks:
        print("\nTotal SKS:", total_sks(), "SKS")
        return "Total SKS berhasil dihitung."

    # Jadwal berdasarkan hari
    hari_list = [
        "senin", "selasa", "rabu",
        "kamis", "jumat", "sabtu", "minggu"
    ]

    if "jadwal" in teks or "kuliah hari" in teks:

        for hari in hari_list:

            if hari in teks:

                jadwal_harian(hari)
                return "Berikut jadwal perkuliahan hari " + hari + "."

        seluruh_jadwal()
        return "Berikut seluruh jadwal perkuliahan."

    # Jadwal UTS
    if "uts" in teks or "ujian tengah semester" in teks:

        tampilkan_ujian("UTS")
        return "Berikut jadwal UTS."

    # Jadwal UAS
    if "uas" in teks or "ujian akhir semester" in teks:

        tampilkan_ujian("UAS")
        return "Berikut jadwal UAS."

    # Pencarian dosen
    if "dosen" in teks:

        kata = teks.replace("siapa dosen", "")
        kata = kata.replace("nama dosen", "")
        kata = kata.replace("dosen", "")
        kata = kata.replace("mata kuliah", "")
        kata = kata.replace("untuk", "").strip()

        cari_dosen(kata)

        return "Pencarian informasi dosen selesai."

    # Pencarian mata kuliah
    if "mata kuliah" in teks or "matkul" in teks:

        kata = teks.replace("mata kuliah", "")
        kata = kata.replace("matkul", "")
        kata = kata.replace("apa", "")
        kata = kata.replace("informasi", "").strip()

        tampilkan_matkul(kata)

        return "Pencarian mata kuliah selesai."

    # Tugas
    if "tugas" in teks or "deadline" in teks:

        tampilkan_tugas()

        return "Berikut daftar tugas perkuliahan."

    # Kalender akademik
    if "kalender akademik" in teks:

        tampilkan_kalender()

        return "Berikut kalender akademik."

    # Riwayat
    if "riwayat" in teks:

        tampilkan_riwayat()

        return "Berikut riwayat percakapan."

    return None


# ==========================================================
# 22. FUNGSI UTAMA CHATBOT
# ==========================================================

def chatbot_response(input_user):

    teks = normalisasi(input_user)

    # Sapaan
    if teks in ["halo", "hai", "hello", "assalamualaikum"]:

        return random.choice([
            "Halo! Selamat datang di Smart Campus Assistant.",
            "Hai mahasiswa! Ada informasi kampus yang ingin kamu cari?",
            "Halo! Saya siap membantu kebutuhan akademikmu."
        ])

    # Identitas chatbot
    if teks in ["siapa kamu", "kamu siapa", "nama kamu"]:

        return (
            "Saya adalah Smart Campus Assistant, "
            "chatbot asisten akademik yang membantu mahasiswa "
            "mendapatkan informasi perkuliahan."
        )

    # Bantuan
    if teks in ["bantuan", "help", "menu", "fitur"]:

        return (
            "FITUR SMART CAMPUS:\n"
            "1. Profil mahasiswa\n"
            "2. Kartu Rencana Studi (KRS)\n"
            "3. Jadwal kuliah\n"
            "4. Informasi dosen\n"
            "5. Informasi mata kuliah\n"
            "6. Total SKS\n"
            "7. Jadwal UTS dan UAS\n"
            "8. Daftar tugas\n"
            "9. Kalender akademik\n"
            "10. Riwayat percakapan\n\n"
            "Silakan ketik pertanyaan yang ingin kamu ajukan."
        )

    # Terima kasih
    if teks in ["terima kasih", "makasih", "thanks"]:

        return "Sama-sama! Semoga perkuliahanmu berjalan lancar."

    # Memproses informasi akademik
    hasil = proses_akademik(teks)

    if hasil is not None:

        return hasil

    # Mendeteksi intent umum
    intent = deteksi_intent(teks)

    if intent is not None:

        return random.choice(
            knowledge_base[intent]["responses"]
        )

    # Respons jika tidak dikenali
    return (
        "Maaf, saya belum memahami pertanyaan tersebut.\n"
        "Silakan gunakan kata kunci yang berkaitan dengan "
        "perkuliahan atau ketik 'bantuan' untuk melihat fitur."
    )


# ==========================================================
# 23. PROGRAM UTAMA
# ==========================================================

def main():

    print("\n" + "=" * 60)

    print("          SMART CAMPUS - AI STUDENT ASSISTANT")

    print("=" * 60)

    print("Selamat datang di Smart Campus Assistant!")

    print("NIM  :", mahasiswa["nim"])
    print("Prodi:", mahasiswa["prodi"])

    print("\nSaya siap membantu kebutuhan akademikmu.")

    print("\nKetik 'bantuan' untuk melihat daftar fitur.")
    print("Ketik 'keluar' untuk mengakhiri percakapan.")

    print("=" * 60)

    while True:

        input_user = input("\nMahasiswa : ").strip()

        if input_user == "":

            print("Chatbot   : Silakan masukkan pertanyaan.")

            continue

        teks = normalisasi(input_user)

        # Keluar dari program
        if teks in ["keluar", "exit", "bye", "quit"]:

            print("\nChatbot   : Terima kasih telah menggunakan")
            print("            Smart Campus Assistant!")

            print("            Semoga sukses dalam perkuliahan.")

            print("=" * 60)

            break

        # Memproses pertanyaan
        jawaban = chatbot_response(input_user)

        print("\nChatbot   :", jawaban)

        # Menyimpan riwayat
        riwayat.append({

            "waktu": datetime.now().strftime("%H:%M:%S"),

            "pertanyaan": input_user,

            "jawaban": jawaban

        })


# ==========================================================
# 24. MENJALANKAN PROGRAM
# ==========================================================

if __name__ == "__main__":

    main()
