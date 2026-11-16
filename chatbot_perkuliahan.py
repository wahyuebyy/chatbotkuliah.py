
import random
import re
from datetime import datetime

# ==================================================
# 1. DATABASE PENGETAHUAN CHATBOT
# ==================================================

knowledge_base = {

    "jadwal_kuliah": {
        "nama": "Jadwal Kuliah",
        "keywords": [
            "jadwal kuliah", "jadwal kelas",
            "jadwal hari ini", "jam kuliah",
            "kapan kuliah", "hari kuliah"
        ],
        "responses": [
            "Jadwal kuliah dapat dilihat melalui portal akademik kampus atau KRS.",
            "Untuk mengetahui jadwal perkuliahan, silakan periksa sistem informasi akademik kampus.",
            "Pastikan kamu selalu memeriksa jadwal kuliah agar tidak terlambat mengikuti kelas."
        ]
    },

    "materi_kuliah": {
        "nama": "Materi Perkuliahan",
        "keywords": [
            "materi kuliah", "materi pembelajaran",
            "bahan ajar", "modul kuliah",
            "materi dosen", "belajar materi"
        ],
        "responses": [
            "Materi perkuliahan biasanya diberikan oleh dosen melalui LMS atau grup kelas.",
            "Kamu bisa meminta materi kepada dosen atau teman sekelas jika belum mendapatkannya.",
            "Sebaiknya pelajari materi sebelum perkuliahan dimulai agar lebih mudah memahami penjelasan dosen."
        ]
    },

    "tugas": {
        "nama": "Tugas Mahasiswa",
        "keywords": [
            "tugas kuliah", "tugas mahasiswa",
            "deadline tugas", "pengumpulan tugas",
            "cara mengerjakan tugas", "tugas belum selesai",
            "tugas kelompok"
        ],
        "responses": [
            "Kerjakan tugas sesuai instruksi dosen dan jangan menunda sampai mendekati deadline.",
            "Pastikan format dan ketentuan tugas sudah sesuai sebelum dikumpulkan.",
            "Jika tugas kelompok, sebaiknya bagi pekerjaan secara adil kepada seluruh anggota."
        ]
    },

    "uts": {
        "nama": "Ujian Tengah Semester",
        "keywords": [
            "uts", "ujian tengah semester",
            "persiapan uts", "jadwal uts",
            "materi uts"
        ],
        "responses": [
            "UTS merupakan ujian yang dilaksanakan pada pertengahan semester.",
            "Persiapkan UTS dengan mempelajari kembali materi yang telah diberikan dosen.",
            "Jangan lupa memeriksa jadwal dan ketentuan pelaksanaan UTS dari kampus."
        ]
    },

    "uas": {
        "nama": "Ujian Akhir Semester",
        "keywords": [
            "uas", "ujian akhir semester",
            "persiapan uas", "jadwal uas",
            "materi uas"
        ],
        "responses": [
            "UAS merupakan evaluasi pembelajaran yang dilaksanakan pada akhir semester.",
            "Pelajari kembali materi dari awal semester agar lebih siap menghadapi UAS.",
            "Pastikan tidak ada administrasi atau persyaratan ujian yang belum diselesaikan."
        ]
    },

    "praktikum": {
        "nama": "Praktikum",
        "keywords": [
            "praktikum", "laporan praktikum",
            "percobaan praktikum", "hasil praktikum",
            "praktikum laboratorium"
        ],
        "responses": [
            "Sebelum praktikum, pastikan kamu memahami tujuan dan prosedur percobaan.",
            "Laporan praktikum biasanya berisi tujuan, alat dan bahan, teori, langkah kerja, hasil, analisis, dan kesimpulan.",
            "Jangan lupa mendokumentasikan setiap percobaan sebagai bukti pelaksanaan praktikum."
        ]
    },

    "krs": {
        "nama": "Kartu Rencana Studi",
        "keywords": [
            "krs", "kartu rencana studi",
            "pengisian krs", "ambil mata kuliah",
            "mata kuliah semester"
        ],
        "responses": [
            "KRS adalah Kartu Rencana Studi yang berisi daftar mata kuliah yang akan diambil mahasiswa dalam satu semester.",
            "Pengisian KRS dilakukan sesuai periode akademik yang ditentukan oleh kampus.",
            "Pastikan mata kuliah yang dipilih sesuai dengan ketentuan program studi."
        ]
    },

    "sks": {
        "nama": "Satuan Kredit Semester",
        "keywords": [
            "sks", "satuan kredit semester",
            "jumlah sks", "beban sks",
            "pengertian sks"
        ],
        "responses": [
            "SKS merupakan satuan kredit semester yang digunakan untuk mengukur beban belajar mahasiswa.",
            "Jumlah SKS yang dapat diambil mahasiswa mengikuti ketentuan akademik dan hasil studi sebelumnya.",
            "SKS membantu menentukan beban perkuliahan yang harus diselesaikan mahasiswa."
        ]
    },

    "dosen": {
        "nama": "Informasi Dosen",
        "keywords": [
            "dosen", "menghubungi dosen",
            "chat dosen", "izin kepada dosen",
            "bertanya kepada dosen", "dosen pembimbing"
        ],
        "responses": [
            "Saat menghubungi dosen, gunakan bahasa yang sopan, jelas, dan formal.",
            "Awali pesan dengan salam, perkenalkan diri, lalu sampaikan tujuan dengan singkat.",
            "Perhatikan waktu ketika menghubungi dosen dan hindari mengirim pesan berulang kali."
        ]
    },

    "beasiswa": {
        "nama": "Informasi Beasiswa",
        "keywords": [
            "beasiswa", "bantuan pendidikan",
            "bantuan kuliah", "beasiswa mahasiswa",
            "persyaratan beasiswa"
        ],
        "responses": [
            "Informasi beasiswa dapat diperoleh melalui bagian kemahasiswaan atau situs resmi kampus.",
            "Setiap beasiswa memiliki persyaratan akademik dan administrasi yang berbeda.",
            "Siapkan dokumen yang diperlukan dan perhatikan batas waktu pendaftaran beasiswa."
        ]
    },

    "organisasi": {
        "nama": "Organisasi Mahasiswa",
        "keywords": [
            "organisasi", "ukm",
            "himpunan mahasiswa", "kegiatan kampus",
            "ekstrakurikuler kampus"
        ],
        "responses": [
            "Organisasi mahasiswa dapat membantu mengembangkan kemampuan komunikasi, kepemimpinan, dan kerja sama.",
            "Kamu dapat mengikuti UKM atau himpunan mahasiswa sesuai minat dan kemampuan.",
            "Mengikuti organisasi merupakan salah satu cara untuk menambah pengalaman selama kuliah."
        ]
    },

    "absensi": {
        "nama": "Kehadiran dan Absensi",
        "keywords": [
            "absensi", "kehadiran",
            "tidak masuk kuliah", "izin tidak kuliah",
            "alpa", "presensi"
        ],
        "responses": [
            "Pastikan kehadiran tercatat pada sistem absensi yang digunakan kampus.",
            "Jika tidak dapat mengikuti perkuliahan, segera informasikan kepada dosen sesuai prosedur.",
            "Perhatikan batas minimal kehadiran yang ditetapkan oleh program studi."
        ]
    },

    "nilai": {
        "nama": "Nilai Akademik",
        "keywords": [
            "nilai kuliah", "nilai semester",
            "nilai ipk", "nilai ips",
            "indeks prestasi", "cek nilai"
        ],
        "responses": [
            "Nilai akademik biasanya dapat diperiksa melalui portal akademik kampus.",
            "IPS merupakan Indeks Prestasi Semester, sedangkan IPK merupakan Indeks Prestasi Kumulatif.",
            "Jika terdapat kesalahan nilai, silakan hubungi dosen pengampu atau bagian akademik."
        ]
    },

    "perpustakaan": {
        "nama": "Perpustakaan",
        "keywords": [
            "perpustakaan", "pinjam buku",
            "peminjaman buku", "referensi buku",
            "buku kuliah"
        ],
        "responses": [
            "Perpustakaan kampus dapat dimanfaatkan untuk mencari referensi pembelajaran.",
            "Kamu dapat mencari buku, jurnal, dan sumber ilmiah untuk membantu mengerjakan tugas.",
            "Pastikan mengikuti aturan peminjaman dan pengembalian buku perpustakaan."
        ]
    },

    "skripsi": {
        "nama": "Skripsi dan Tugas Akhir",
        "keywords": [
            "skripsi", "tugas akhir",
            "judul skripsi", "proposal penelitian",
            "seminar proposal", "sidang skripsi"
        ],
        "responses": [
            "Skripsi merupakan karya ilmiah yang disusun sebagai salah satu persyaratan penyelesaian studi sarjana.",
            "Mulailah dengan menentukan topik penelitian yang sesuai dengan bidang keilmuanmu.",
            "Diskusikan judul dan rancangan penelitian dengan dosen pembimbing."
        ]
    }
}


# ==================================================
# 2. FUNGSI NORMALISASI TEKS
# ==================================================

def normalisasi_teks(teks):
    teks = teks.lower()

    # Menghapus tanda baca
    teks = re.sub(r"[^a-z0-9\s]", " ", teks)

    # Menghapus spasi berlebihan
    teks = re.sub(r"\s+", " ", teks).strip()

    return teks


# ==================================================
# 3. FUNGSI MENGENALI KATEGORI PERTANYAAN
# ==================================================

def deteksi_intent(input_user):

    input_user = normalisasi_teks(input_user)

    skor_tertinggi = 0
    intent_terpilih = None

    for intent, data in knowledge_base.items():

        skor = 0

        for keyword in data["keywords"]:

            keyword = normalisasi_teks(keyword)

            # Mencocokkan frasa dengan pertanyaan
            if re.search(
                r"\b" + re.escape(keyword) + r"\b",
                input_user
            ):
                skor += len(keyword.split())

        if skor > skor_tertinggi:
            skor_tertinggi = skor
            intent_terpilih = intent

    # Jika tidak ditemukan kata kunci
    if skor_tertinggi == 0:
        return None

    return intent_terpilih


# ==================================================
# 4. FUNGSI MENGHASILKAN JAWABAN CHATBOT
# ==================================================

def chatbot_response(input_user):

    teks = normalisasi_teks(input_user)

    # Respons sapaan
    if teks in ["halo", "hai", "hello", "assalamualaikum"]:
        return "Waalaikumsalam! Halo mahasiswa! Ada yang bisa saya bantu?"

    # Respons ucapan terima kasih
    if teks in ["terima kasih", "makasih", "thanks"]:
        return "Sama-sama! Semoga kegiatan perkuliahanmu lancar."

    # Respons identitas chatbot
    if teks in ["siapa kamu", "kamu siapa", "nama kamu"]:
        return (
            "Saya adalah Chatbot AI Asisten Perkuliahan. "
            "Saya siap membantu menjawab pertanyaan seputar dunia kampus."
        )

    # Menampilkan bantuan
    if teks in ["bantuan", "help", "menu", "fitur"]:
        return (
            "Saya dapat membantu informasi tentang:\n"
            "- Jadwal kuliah\n"
            "- Materi perkuliahan\n"
            "- Tugas mahasiswa\n"
            "- UTS dan UAS\n"
            "- Praktikum\n"
            "- KRS dan SKS\n"
            "- Dosen\n"
            "- Beasiswa\n"
            "- Organisasi\n"
            "- Absensi\n"
            "- Nilai akademik\n"
            "- Perpustakaan\n"
            "- Skripsi dan tugas akhir\n\n"
            "Silakan ketik pertanyaan yang ingin kamu ajukan."
        )

    # Mendeteksi maksud pertanyaan
    intent = deteksi_intent(input_user)

    if intent is not None:

        jawaban = random.choice(
            knowledge_base[intent]["responses"]
        )

        return jawaban

    # Respons jika pertanyaan tidak dikenali
    return (
        "Maaf, saya belum memahami pertanyaan tersebut.\n"
        "Silakan gunakan kata kunci yang berhubungan dengan "
        "perkuliahan atau ketik 'bantuan' untuk melihat fitur."
    )


# ==================================================
# 5. FUNGSI MENAMPILKAN RIWAYAT PERCAKAPAN
# ==================================================

riwayat_percakapan = []

def tampilkan_riwayat():

    if len(riwayat_percakapan) == 0:
        print("\nBelum ada riwayat percakapan.")
        return

    print("\n========== RIWAYAT PERCAKAPAN ==========")

    for nomor, data in enumerate(riwayat_percakapan, 1):

        print(f"\nPercakapan ke-{nomor}")
        print("Mahasiswa :", data["pertanyaan"])
        print("Chatbot   :", data["jawaban"])

    print("========================================")


# ==================================================
# 6. PROGRAM UTAMA
# ==================================================

def main():

    print("\n" + "=" * 55)
    print("          CHATBOT AI ASISTEN PERKULIAHAN")
    print("=" * 55)

    print("Selamat datang di Chatbot Asisten Perkuliahan!")
    print("Saya siap membantu memberikan informasi kampus.")

    print("\nFitur yang tersedia:")
    print("1. Informasi akademik")
    print("2. Tugas dan praktikum")
    print("3. Ujian dan nilai")
    print("4. Kehidupan mahasiswa")
    print("5. Informasi kampus")

    print("\nKetik 'bantuan' untuk melihat seluruh fitur.")
    print("Ketik 'riwayat' untuk melihat percakapan.")
    print("Ketik 'keluar' untuk mengakhiri program.")

    print("-" * 55)

    while True:

        input_user = input("\nMahasiswa : ").strip()

        # Memeriksa input kosong
        if input_user == "":
            print("Chatbot   : Silakan masukkan pertanyaan terlebih dahulu.")
            continue

        teks = normalisasi_teks(input_user)

        # Perintah keluar
        if teks in ["keluar", "exit", "bye", "quit"]:

            print("\nChatbot   : Terima kasih telah menggunakan layanan saya.")
            print("            Semoga perkuliahanmu sukses!")
            print("=" * 55)

            break

        # Menampilkan riwayat
        if teks == "riwayat":

            tampilkan_riwayat()
            continue

        # Memproses jawaban chatbot
        jawaban = chatbot_response(input_user)

        print("\nChatbot   :", jawaban)

        # Menyimpan percakapan
        riwayat_percakapan.append({
            "waktu": datetime.now().strftime("%H:%M:%S"),
            "pertanyaan": input_user,
            "jawaban": jawaban
        })


# ==================================================
# 7. MENJALANKAN PROGRAM
# ==================================================

if __name__ == "__main__":
    main()
