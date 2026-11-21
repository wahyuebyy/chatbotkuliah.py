#!/usr/bin/env python3
"""
jalankan_evaluasi.py  -  Mengukur akurasi router tanpa memanggil LLM.

PENANGGUNG JAWAB: Anggota 4 (Router, CLI & Evaluasi)

Yang diukur:
  - akurasi jalur (kb / llm / fallback / sapaan) terhadap evaluasi/test_cases.json
  - akurasi entri KB teratas untuk kasus jalur 'kb'
  - confusion matrix + daftar kasus yang salah

Pemakaian (dari folder utama proyek):
    python evaluasi/jalankan_evaluasi.py                 # tampilkan hasil
    python evaluasi/jalankan_evaluasi.py --simpan        # + simpan evaluasi/hasil_evaluasi.md
    python evaluasi/jalankan_evaluasi.py --sweep         # coba beberapa kombinasi threshold
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from akademikbot import router as router_mod  # noqa: E402
from akademikbot.router import Chatbot  # noqa: E402

CASES = Path(__file__).resolve().parent / "test_cases.json"
LAPORAN = Path(__file__).resolve().parent / "hasil_evaluasi.md"
JALUR = ["kb", "llm", "fallback", "sapaan"]


def muat_kasus() -> list[dict]:
    return json.loads(CASES.read_text(encoding="utf-8"))["kasus"]


def evaluasi(bot: Chatbot, kasus: list[dict]) -> dict:
    baris = []
    for k in kasus:
        r = bot.rute(k["q"])
        top = r.hasil[0].entri.id if r.hasil else None
        jalur_ok = r.jalur == k["jalur"]
        entri_ok = None
        if k["jalur"] == "kb" and "entri" in k:
            entri_ok = jalur_ok and top == k["entri"]
        baris.append({**k, "prediksi": r.jalur, "top": top, "alasan": r.alasan,
                      "skor": r.hasil[0].skor if r.hasil else 0.0,
                      "jalur_ok": jalur_ok, "entri_ok": entri_ok})
    n = len(baris)
    kb_kasus = [b for b in baris if b["entri_ok"] is not None]
    ho = [b for b in baris if b.get("heldout")]
    return {
        "baris": baris,
        "n_heldout": len(ho),
        "akurasi_heldout": (sum(b["jalur_ok"] and b["entri_ok"] is not False for b in ho) / len(ho)) if ho else None,
        "akurasi_jalur": sum(b["jalur_ok"] for b in baris) / n,
        "akurasi_entri": (sum(b["entri_ok"] for b in kb_kasus) / len(kb_kasus)) if kb_kasus else 0.0,
        "confusion": Counter((b["jalur"], b["prediksi"]) for b in baris),
        "n": n,
    }


def teks_laporan(h: dict) -> str:
    out = [f"Jumlah kasus uji     : {h['n']}",
           f"Akurasi jalur router : {h['akurasi_jalur']:.1%}",
           f"Akurasi entri KB     : {h['akurasi_entri']:.1%} (khusus kasus jalur kb)"]
    if h["akurasi_heldout"] is not None:
        out.append(f"Akurasi held-out     : {h['akurasi_heldout']:.1%} ({h['n_heldout']} kasus yang tidak dipakai tuning)")
    out += ["",
           "Confusion matrix (baris = harapan, kolom = prediksi):",
           "harapan \\ prediksi".ljust(20) + "".join(j.rjust(10) for j in JALUR)]
    for a in JALUR:
        out.append(a.ljust(20) + "".join(str(h["confusion"].get((a, p), 0)).rjust(10) for p in JALUR))
    salah = [b for b in h["baris"] if not b["jalur_ok"] or b["entri_ok"] is False]
    out += ["", f"Kasus yang salah ({len(salah)}):"]
    if not salah:
        out.append("  (tidak ada)")
    for b in salah:
        out.append(f"  - \"{b['q']}\"  harapan={b['jalur']}/{b.get('entri', '-')}  "
                   f"prediksi={b['prediksi']}/{b['top']}  skor={b['skor']:.2f}  alasan={b['alasan']}")
    return "\n".join(out)


def laporan_markdown(h: dict) -> str:
    md = ["# Hasil Evaluasi Router AkademikBot", "",
          f"- Jumlah kasus uji: **{h['n']}**",
          f"- Akurasi jalur router: **{h['akurasi_jalur']:.1%}**",
          f"- Akurasi entri KB (jalur kb): **{h['akurasi_entri']:.1%}**"]
    if h["akurasi_heldout"] is not None:
        md.append(f"- Akurasi held-out ({h['n_heldout']} kasus di luar tuning): **{h['akurasi_heldout']:.1%}**")
    md += ["",
          "## Confusion matrix", "",
          "| harapan \\ prediksi | " + " | ".join(JALUR) + " |",
          "|---|" + "---|" * len(JALUR)]
    for a in JALUR:
        md.append(f"| {a} | " + " | ".join(str(h["confusion"].get((a, p), 0)) for p in JALUR) + " |")
    md += ["", "## Detail per kasus", "", "| Pertanyaan | Harapan | Prediksi | Entri | Skor | Alasan | OK |",
           "|---|---|---|---|---|---|---|"]
    for b in h["baris"]:
        ok = "ya" if b["jalur_ok"] and b["entri_ok"] is not False else "TIDAK"
        md.append(f"| {b['q']} | {b['jalur']} | {b['prediksi']} | {b['top'] or '-'} | "
                  f"{b['skor']:.2f} | {b['alasan']} | {ok} |")
    return "\n".join(md) + "\n"


def sweep(kasus: list[dict]) -> None:
    """Coba kombinasi threshold untuk bahan bab 'Pengujian & Tuning' di laporan."""
    asli = (router_mod.THRESHOLD_YAKIN, router_mod.THRESHOLD_SANGAT_YAKIN, router_mod.CAKUPAN_MIN)
    print("YAKIN  SANGAT_YAKIN  CAKUPAN_MIN  akurasi_jalur  akurasi_entri")
    try:
        for y, sy, c in itertools.product((0.30, 0.40, 0.50), (0.45, 0.55, 0.65), (0.40, 0.50, 0.60)):
            if sy < y:
                continue
            router_mod.THRESHOLD_YAKIN, router_mod.THRESHOLD_SANGAT_YAKIN, router_mod.CAKUPAN_MIN = y, sy, c
            h = evaluasi(Chatbot(offline=True, log_path=None), kasus)
            print(f"{y:.2f}   {sy:.2f}          {c:.2f}         {h['akurasi_jalur']:.1%}          {h['akurasi_entri']:.1%}")
    finally:
        router_mod.THRESHOLD_YAKIN, router_mod.THRESHOLD_SANGAT_YAKIN, router_mod.CAKUPAN_MIN = asli


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluasi router AkademikBot")
    ap.add_argument("--simpan", action="store_true", help="simpan laporan ke evaluasi/hasil_evaluasi.md")
    ap.add_argument("--sweep", action="store_true", help="uji kombinasi threshold")
    args = ap.parse_args()

    kasus = muat_kasus()
    if args.sweep:
        sweep(kasus)
        return 0
    h = evaluasi(Chatbot(offline=True, log_path=None), kasus)
    print(teks_laporan(h))
    if args.simpan:
        LAPORAN.write_text(laporan_markdown(h), encoding="utf-8")
        print(f"\nLaporan disimpan: {LAPORAN}")
    return 0 if h["akurasi_jalur"] >= 0.9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
