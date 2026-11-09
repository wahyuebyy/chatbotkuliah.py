
menu = {
    "1": {"nama": "Nasi Goreng Spesial", "harga": 35000},
    "2": {"nama": "Chicken Cordon Bleu", "harga": 45000},
    "3": {"nama": "Mie Goreng", "harga": 30000},
    "4": {"nama": "Cap Cay", "harga": 32000},
    "5": {"nama": "Ayam Goreng Mentega", "harga": 40000},
    "6": {"nama": "Es Teh Manis", "harga": 8000},
    "7": {"nama": "Jus Jeruk", "harga": 15000},
    "8": {"nama": "Es Jeruk", "harga": 12000}
}

keranjang = []


def tampilkan_menu():
    print("\n========== MENU SOLARIA ==========")
    for nomor, item in menu.items():
        print(f"{nomor}. {item['nama']} - Rp{item['harga']:,}")
    print("==================================")


def tampilkan_keranjang():
    if not keranjang:
        print("\nKeranjang masih kosong.")
        return

    print("\n========== PESANAN ANDA ==========")
    total = 0

    for item in keranjang:
        subtotal = item["harga"] * item["jumlah"]
        total += subtotal
        print(
            f"{item['nama']} x{item['jumlah']} "
            f"= Rp{subtotal:,}"
        )

    print("----------------------------------")
    print(f"Total pembayaran: Rp{total:,}")


def pesan_makanan():
    tampilkan_menu()

    nomor = input("\nMasukkan nomor menu: ")

    if nomor not in menu:
        print("Maaf, nomor menu tidak tersedia.")
        return

    try:
        jumlah = int(input("Masukkan jumlah pesanan: "))

        if jumlah <= 0:
            print("Jumlah pesanan harus lebih dari 0.")
            return

    except ValueError:
        print("Masukkan jumlah menggunakan angka.")
        return

    item = menu[nomor]

    keranjang.append({
        "nama": item["nama"],
        "harga": item["harga"],
        "jumlah": jumlah
    })

    print(f"\n{item['nama']} berhasil ditambahkan ke pesanan.")


def checkout():
    if not keranjang:
        print("\nBelum ada pesanan.")
        return

    tampilkan_keranjang()

    total = sum(
        item["harga"] * item["jumlah"]
        for item in keranjang
    )

    print("\n========== PEMBAYARAN ==========")
    print(f"Total yang harus dibayar: Rp{total:,}")
    print("Terima kasih telah memesan di Solaria!")
    print("Silakan lakukan pembayaran di kasir.")

    keranjang.clear()


def chatbot():
    print("===================================")
    print("   CHATBOT RESTORAN SOLARIA")
    print("===================================")
    print("Halo! Selamat datang di Restoran Solaria.")
    print("Saya adalah asisten virtual Solaria.")
    print("Ketik 'bantuan' untuk melihat perintah.")

    while True:
        pesan = input("\nAnda: ").lower().strip()

        if any(kata in pesan for kata in ["halo", "hai", "hello"]):
            print("Bot: Halo! Selamat datang di Solaria.")

        elif "menu" in pesan or "makanan" in pesan:
            tampilkan_menu()

        elif "pesan" in pesan or "order" in pesan:
            pesan_makanan()

        elif "keranjang" in pesan or "pesanan" in pesan:
            tampilkan_keranjang()

        elif "harga" in pesan:
            print("Bot: Harga makanan dan minuman dapat dilihat pada menu.")

        elif "lokasi" in pesan or "alamat" in pesan:
            print("Bot: Solaria memiliki berbagai cabang.")
            print("Silakan periksa lokasi cabang melalui situs resmi Solaria.")

        elif "jam" in pesan or "buka" in pesan:
            print("Bot: Jam operasional berbeda pada setiap cabang.")
            print("Silakan hubungi cabang Solaria yang dituju.")

        elif "checkout" in pesan or "bayar" in pesan:
            checkout()

        elif "bantuan" in pesan:
            print("\nPerintah yang tersedia:")
            print("- Halo")
            print("- Menu")
            print("- Pesan makanan")
            print("- Keranjang")
            print("- Harga")
            print("- Lokasi")
            print("- Jam buka")
            print("- Checkout")
            print("- Keluar")

        elif "keluar" in pesan or "exit" in pesan:
            print("Bot: Terima kasih telah mengunjungi Solaria!")
            print("Selamat menikmati makanan Anda.")
            break

        else:
            print("Bot: Maaf, saya belum memahami pesan Anda.")
            print("Ketik 'bantuan' untuk melihat perintah.")


chatbot()
