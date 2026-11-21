"""
cli.py  -  Antarmuka terminal AkademikBot.

PENANGGUNG JAWAB: Anggota 4 (Router, CLI & Evaluasi)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .config import KB_PATH, NAMA_BOT, NAMA_PRODI
from .dokumen import DokumenError
from .kuis import format_kuis
from .data_akademik import DataAkademik
from .kb_loader import KBError, muat_kb, periksa_kualitas
from .menu import Layar
from .router import Balasan, Chatbot
from .setup_otomatis import siapkan_env, tentukan_mode


class C:
    """Kode warna ANSI (otomatis mati jika bukan terminal / NO_COLOR diatur)."""
    on = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
    RESET = "\033[0m" if on else ""
    BOLD = "\033[1m" if on else ""
    DIM = "\033[2m" if on else ""
    GREEN = "\033[92m" if on else ""
    YELLOW = "\033[93m" if on else ""
    BLUE = "\033[94m" if on else ""
    CYAN = "\033[96m" if on else ""
    RED = "\033[91m" if on else ""


LABEL = {
    "kb": (C.GREEN, "KB lokal (TF-IDF)"),
    "llm": (C.BLUE, "LLM + konteks KB"),
    "fallback": (C.RED, "Fallback"),
    "sapaan": (C.CYAN, "Sapaan"),
    "saran": (C.YELLOW, "Saran topik"),
    "alat": (C.CYAN, "Alat akademik"),
}

DEMO = [
    "Halo",
    "Bagaimana cara mengisi KRS?",
    "gmn cara cuti kuliah?",
    "berapa sks maksimal per semester",
    "Apa saja syarat mengajukan skripsi?",
    "Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti?",
    "Kalau dosen tidak hadir dan presensi saya kurang dari batas, apakah masih boleh ikut UAS?",
    "Jadwal kuliah semester 3 hari Selasa",
    "Berapa SKS Sistem Operasi dan siapa dosennya?",
    "Berapa biaya UKT semester depan?",
    "Siapa presiden Indonesia pertama?",
    "Terima kasih",
]


def cetak_balasan(b: Balasan, debug: bool = False, tampil_opsi: bool = True) -> None:
    warna, nama = LABEL[b.mode]
    if b.dipilih:
        print(f"{C.DIM}  (memilih pilihan cepat: {b.dipilih}){C.RESET}")
    print(f"\n{C.BOLD}{NAMA_BOT}{C.RESET}: {b.teks}")
    if b.kuis:
        print("\n" + format_kuis(b.kuis))
    meta = nama
    if b.mode in ("kb", "llm", "saran", "fallback") and b.skor:
        meta += f" | skor {b.skor:.2f}"
    if b.model:
        meta += f" | model {b.model}"
    meta += f" | {b.waktu_ms:.0f} ms"
    print(f"{C.DIM}{warna}  [{meta}]{C.RESET}")
    if b.sumber:
        print(f"{C.DIM}  Sumber: {'; '.join(b.sumber)}{C.RESET}")
    if debug and b.percobaan:
        print(f"{C.DIM}  Jejak model: {' -> '.join(b.percobaan)}{C.RESET}")
    if debug and b.alasan:
        print(f"{C.DIM}  Alasan rute: {b.alasan}{C.RESET}")
    if tampil_opsi and b.opsi_cepat:
        print(f"\n{C.YELLOW}Pertanyaan lanjutan (ketik angkanya saja):{C.RESET}")
        for i, o in enumerate(b.opsi_cepat, 1):
            print(f"  {C.BOLD}{i}{C.RESET}. {o}")
    print()


def cetak_tabel(lay: Layar) -> None:
    """Tabel pilihan ber-nomor (ASCII) untuk menu terminal."""
    k1, k2, k3 = lay.kolom
    baris = [(str(o.no), o.label, o.ket) for o in lay.opsi]
    w1 = max(len(k1), *(len(b[0]) for b in baris)) if baris else len(k1)
    w2 = min(max(len(k2), *(len(b[1]) for b in baris)) if baris else len(k2), 52)
    w3 = min(max(len(k3), *(len(b[2]) for b in baris)) if baris else len(k3), 40)
    garis = f"+-{'-' * w1}-+-{'-' * w2}-+-{'-' * w3}-+"

    def f(a: str, b: str, c: str) -> str:
        return f"| {a:<{w1}} | {b[:w2]:<{w2}} | {c[:w3]:<{w3}} |"
    print(f"\n{C.BOLD}{C.CYAN}{lay.judul}{C.RESET}")
    print(garis); print(f(k1, k2, k3)); print(garis)
    for b in baris:
        print(f(*b))
    print(garis)
    print(f"{C.DIM}{lay.petunjuk}{C.RESET}")


def jalankan_menu(bot: Chatbot, debug: bool = False) -> str | None:
    """Menu pilihan tanpa mengetik. Mengembalikan teks bila pengguna mengetik pertanyaan biasa
    di tengah menu (supaya langsung diproses sebagai chat), None bila keluar dari menu."""
    jalur: list[str] = []
    pesan = ""
    while True:
        h = bot.menu.buka(jalur)
        if h.atur_semester is not None:
            bot.atur_semester(h.atur_semester)
            jalur, pesan = [], h.pesan
            continue
        if h.entri_id:
            cetak_balasan(bot.jawab_entri(h.entri_id), debug, tampil_opsi=False)
            jalur = h.balik
            continue
        lay = h.layar
        assert lay is not None
        jalur = lay.jalur
        if pesan or h.pesan:
            print(f"\n{C.GREEN}{pesan or h.pesan}{C.RESET}")
            pesan = ""
        if bot.semester:
            print(f"{C.DIM}Semester Anda: {bot.semester}{C.RESET}", end="")
        cetak_tabel(lay)
        try:
            pil = input(f"{C.BOLD}Pilih{C.RESET} (nomor / 0 kembali / q keluar): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if pil.lower() in ("q", "/keluar", "keluar", ""):
            return None
        if pil == "0":
            jalur = jalur[:-1]
            continue
        if pil.isdigit():
            cocok = [o for o in lay.opsi if o.no == int(pil)]
            if cocok:
                jalur = cocok[0].jalur
            else:
                print(f"{C.YELLOW}Nomor {pil} tidak ada di tabel.{C.RESET}")
            continue
        return pil        # bukan angka -> perlakukan sebagai pertanyaan chat


def data_info(bot: Chatbot) -> str:
    d = bot.data
    if not d:
        return ""
    return (f" | {len(d.matkul)} mata kuliah, {len(d.jadwal)} sesi jadwal"
            + (" (JADWAL DUMMY)" if d.dummy else ""))


def banner(bot: Chatbot) -> None:
    status = (f"{C.GREEN}aktif ({bot.llm.model}){C.RESET}" if bot.llm.tersedia
              else f"{C.YELLOW}nonaktif - {bot.llm.error}{C.RESET}")
    print(f"""
{C.BOLD}{C.CYAN}=============================================={C.RESET}
{C.BOLD}  {NAMA_BOT} - Layanan Akademik {NAMA_PRODI}{C.RESET}
{C.BOLD}{C.CYAN}=============================================={C.RESET}
  Knowledge base : {len(bot.index.entri)} entri (TF-IDF){data_info(bot)}
  LLM            : {status}
  Perintah       : /menu  /semester  /topik  /riwayat  /debug  /reset  /bantuan  /keluar
  Dokumen        : /dokumen berkas.pdf  (tanya jawab isi dokumen)  |  contoh alat: "cek sks: ...", "ruangan kosong hari Selasa jam 10.00"
  Tips           : setelah jawaban muncul "Pertanyaan lanjutan", cukup ketik 1, 2, atau 3
""")


def jalankan_cli(bot: Chatbot) -> None:
    banner(bot)
    debug = False
    antre: str | None = None
    while True:
        if antre is not None:
            q, antre = antre, None
        else:
            try:
                q = input(f"{C.BOLD}Anda{C.RESET}: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSampai jumpa!")
                return
        if not q:
            continue
        cmd = q.lower()
        if cmd in ("/menu", "menu"):
            antre = jalankan_menu(bot, debug)
            continue
        if cmd.startswith("/semester"):
            arg = cmd.split(maxsplit=1)[1:] or [""]
            try:
                bot.atur_semester(int(arg[0]) if arg[0] else None)
                print(f"  Semester Anda: {bot.semester or 'belum diatur'}\n")
            except ValueError:
                print("  Pemakaian: /semester 3   (angka 1-8)\n")
            continue
        if cmd in ("/keluar", "/exit", "/quit"):
            print("Sampai jumpa!")
            return
        if cmd in ("/bantuan", "/help"):
            print("  /menu = tabel pilihan (tanpa mengetik) | /semester 3 = atur semester Anda | "
                  "/topik = daftar topik | /riwayat = riwayat chat | /debug = alasan rute | "
                  "/reset = hapus riwayat | /keluar = selesai | 1/2/3 = pilih pertanyaan lanjutan\n")
            continue
        if cmd.startswith("/dokumen"):
            arg = q.split(maxsplit=1)[1].strip().strip('"') if len(q.split(maxsplit=1)) > 1 else ""
            if arg.lower() in ("hapus", "lepas", "reset"):
                bot.hapus_dokumen()
                print("  Dokumen dilepas.\n")
            elif not arg:
                print("  Pemakaian: /dokumen C:\\jalur\\edaran.pdf   (txt/pdf)  |  /dokumen hapus\n")
            else:
                try:
                    info = bot.muat_dokumen(Path(arg).name, Path(arg).read_bytes())
                    print(f"  Dokumen dimuat: {info['nama']} ({info['karakter']} karakter, "
                          f"{info['potongan']} bagian). Silakan bertanya tentang isinya.\n")
                except (OSError, DokumenError) as exc:
                    print(f"  {C.RED}Gagal memuat dokumen: {exc}{C.RESET}\n")
            continue
        if cmd == "/topik":
            for e in bot.index.entri:
                print(f"  - [{e.kategori}] {e.pertanyaan}")
            print()
            continue
        if cmd == "/riwayat":
            for i, (u, _, _) in enumerate(bot.riwayat, 1):
                print(f"  {i}. {u}")
            print()
            continue
        if cmd == "/reset":
            bot.riwayat.clear()
            print("  Riwayat percakapan dihapus.\n")
            continue
        if cmd == "/debug":
            debug = not debug
            print(f"  Mode debug {'aktif' if debug else 'nonaktif'}\n")
            continue
        cetak_balasan(bot.tanya(q), debug)


def cek_data() -> int:
    from .config import DATA_DIR
    d = DataAkademik.muat(DATA_DIR)
    if d is None:
        print(f"{C.RED}kurikulum.json tidak ditemukan di {DATA_DIR}{C.RESET}")
        return 1
    print(f"Data valid: {len(d.matkul)} mata kuliah, {len(d.jadwal)} sesi jadwal "
          f"(semester berjadwal: {d.semester_berjadwal()}), {len(d.entri_kb())} entri dibangkitkan.")
    if d.dummy:
        print(f"{C.YELLOW}CATATAN: jadwal masih DUMMY (data/jadwal_info.json -> \"dummy\": true).{C.RESET}")
    masalah = d.periksa()
    for m in masalah or ["Tidak ada jadwal bentrok."]:
        print(" -", m)
    return 1 if masalah else 0


def _terapkan_mode_otomatis(args: argparse.Namespace) -> argparse.Namespace:
    """Smart Auto-Mode: siapkan .env, lalu pilih multi-model (ada API key + internet) atau offline. Tanpa error."""
    status = siapkan_env()
    if status == "dibuat":
        print(f"{C.GREEN}Berkas .env belum ada -> dibuat otomatis dari .env.example.{C.RESET}")
        print(f"{C.DIM}  Isi API key di .env bila ingin mengaktifkan LLM.{C.RESET}")
    args.web = True
    args.buka_browser = True
    if args.offline:
        return args
    pakai_multi, alasan = tentukan_mode()
    if pakai_multi:
        args.multi = True
        print(f"{C.GREEN}Mode otomatis: multi-model + web ({alasan}).{C.RESET}")
    else:
        args.offline = True
        print(f"{C.YELLOW}Mode otomatis: offline + web ({alasan}). Jawaban tetap dari knowledge base.{C.RESET}")
    return args


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chatbot layanan akademik (KB + TF-IDF & LLM)")
    ap.add_argument("--offline", action="store_true", help="nonaktifkan LLM")
    ap.add_argument("--demo", action="store_true", help="jalankan demo otomatis")
    ap.add_argument("--cek-kb", action="store_true", help="validasi knowledge base lalu keluar")
    ap.add_argument("--cek-data", action="store_true",
                    help="validasi kurikulum.json + jadwal.csv (format & jadwal bentrok) lalu keluar")
    ap.add_argument("--llm-demo", nargs="?", const="baik", metavar="MODE",
                    choices=["baik", "halusinasi", "tanpa_sitasi", "sitasi_palsu", "tidak_tahu"],
                    help="pakai LLM DUMMY tanpa API key (mode: baik|halusinasi|tanpa_sitasi|"
                         "sitasi_palsu|tidak_tahu; default baik)")
    ap.add_argument("--multi", action="store_true",
                    help="multi-model: Claude + GPT + Gemini (yang punya API key), dengan failover")
    ap.add_argument("--multi-demo", nargs="?", const="halusinasi", metavar="MODE_GPT",
                    choices=["baik", "halusinasi", "tanpa_sitasi", "sitasi_palsu", "tidak_tahu"],
                    help="multi-model DUMMY tanpa API key; GPT dummy berperilaku MODE_GPT "
                         "(default halusinasi -> memperlihatkan failover ke Claude)")
    ap.add_argument("--auto", action="store_true",
                    help="mode otomatis: .env dibuat bila belum ada; API key + internet ada -> --multi --web, "
                         "selain itu --offline --web (juga berlaku bila dijalankan tanpa argumen)")
    ap.add_argument("--cli", action="store_true", help="paksa chat di terminal (tanpa argumen = mode otomatis)")
    ap.add_argument("--buka-browser", action="store_true", help="buka browser otomatis saat server web siap")
    ap.add_argument("--web", action="store_true", help="jalankan antarmuka web")
    ap.add_argument("--host", default="127.0.0.1", help="alamat bind server web (default lokal)")
    ap.add_argument("--port", type=int, default=8000, help="port server web")
    ap.add_argument("--kb", type=Path, default=KB_PATH, help="path knowledge_base.json")
    otomatis_diam = argv is None and len(sys.argv) == 1          # `python main.py` tanpa argumen
    args = ap.parse_args(argv)
    if args.cli:
        otomatis_diam = False
    mode_otomatis = (args.auto or otomatis_diam) and not (args.demo or args.cek_kb or args.cek_data)

    try:
        if mode_otomatis:
            args = _terapkan_mode_otomatis(args)
        elif not (args.demo or args.cek_kb or args.cek_data):
            siapkan_env()                                         # .env selalu tersedia saat aplikasi jalan
        if args.cek_kb:
            entri = muat_kb(args.kb)
            print(f"KB valid: {len(entri)} entri.")
            for p in periksa_kualitas(entri) or ["Tidak ada peringatan kualitas."]:
                print(" -", p)
            return 0
        if args.cek_data:
            return cek_data()
        llm = None
        if args.multi_demo and not args.offline:
            from .llm_orchestrator import buat_llm_multi_demo
            llm = buat_llm_multi_demo(args.multi_demo)
        elif args.multi and not args.offline:
            from .llm_orchestrator import buat_llm_multi
            llm = buat_llm_multi()
        elif args.llm_demo and not args.offline:
            from .llm_demo import buat_llm_demo
            llm = buat_llm_demo(args.llm_demo)
        if args.web:
            from .web import jalankan_web
            jalankan_web(args.host, args.port, args.offline, args.kb, llm, buka_browser=args.buka_browser)
            return 0
        bot = Chatbot(args.kb, offline=args.offline, llm=llm)
    except KBError as exc:
        print(f"{C.RED}Gagal memuat knowledge base: {exc}{C.RESET}", file=sys.stderr)
        return 1

    if args.demo:
        banner(bot)
        for q in DEMO:
            print(f"{C.BOLD}Anda{C.RESET}: {q}")
            cetak_balasan(bot.tanya(q), debug=True)
    else:
        jalankan_cli(bot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
