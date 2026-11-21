"""
waktu.py  -  Waktu WIB (Asia/Jakarta) yang aman di semua OS.

Windows tidak membawa database zona waktu IANA; `ZoneInfo("Asia/Jakarta")` bisa gagal bila paket
`tzdata` belum terpasang. WIB tidak mengenal DST (selalu UTC+7), jadi fallback UTC+7 tetap tepat.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    ZONA_WIB = ZoneInfo("Asia/Jakarta")
except Exception:  # ImportError / ZoneInfoNotFoundError
    ZONA_WIB = timezone(timedelta(hours=7), "WIB")


def sekarang_wib() -> datetime:
    """Waktu saat ini di WIB (timezone-aware)."""
    return datetime.now(ZONA_WIB)
