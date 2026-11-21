#!/usr/bin/env python3
"""
contoh_llm.py  -  Membuat evaluasi/contoh_output_llm_dummy.md: contoh keluaran LLM DUMMY pada
pertanyaan majemuk di semua mode, beserta keputusan guardrail. Berguna untuk lampiran laporan.
    python evaluasi/contoh_llm.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from akademikbot.llm_demo import MODE_DEMO, buat_llm_demo  # noqa: E402
from akademikbot.router import Chatbot  # noqa: E402

PERTANYAAN = [
    "Saya sakit waktu UTS, terus syarat skripsi juga apa saja dan bagaimana kalau mau cuti?",
    "Kalau dosen tidak hadir dan presensi saya kurang dari batas, apakah masih boleh ikut UAS?",
    "Saya mau kerja praktik, apa syarat SKS-nya dan bagaimana bimbingan skripsi nanti?",
]


def main() -> None:
    out = ["# Contoh keluaran LLM DUMMY + guardrail", "",
           "> LLM dummy adalah tiruan berbasis aturan, bukan model sungguhan. "
           "Dibuat oleh `evaluasi/contoh_llm.py`.", ""]
    for q in PERTANYAAN:
        out += [f"## {q}", ""]
        for mode in MODE_DEMO:
            b = Chatbot(llm=buat_llm_demo(mode), log_path=None).tanya(q)
            out += [f"### mode `{mode}` -> hasil: **{b.mode}**",
                    f"- alasan: `{b.alasan}`",
                    f"- sumber: {'; '.join(b.sumber) or '-'}", "", "```", b.teks, "```", ""]
    dest = Path(__file__).resolve().parent / "contoh_output_llm_dummy.md"
    dest.write_text("\n".join(out), encoding="utf-8")
    print("Tersimpan:", dest)


if __name__ == "__main__":
    main()
