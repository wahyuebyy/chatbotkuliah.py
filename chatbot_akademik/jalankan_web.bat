@echo off
rem ============================================================
rem  jalankan_web.bat - SEKALI KLIK: siapkan .env, pasang paket yang kurang,
rem  pilih mode otomatis (multi-model bila ada API key + internet, selain itu offline),
rem  jalankan server web, dan buka browser. Ctrl+C di jendela ini untuk berhenti.
rem ============================================================
setlocal
cd /d "%~dp0"
title AkademikBot Web

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
    echo [ERROR] Python belum terpasang. Pasang dari https://www.python.org/downloads/
    echo         dan centang "Add Python to PATH", lalu klik dua kali berkas ini lagi.
    pause
    exit /b 1
)

echo Memeriksa kebutuhan program ^(paket dipasang otomatis bila belum ada^)...
%PY% -m akademikbot.setup_otomatis --pasang

rem --auto: buat .env bila belum ada, pilih --multi/--offline, cari port kosong, buka browser.
%PY% main.py --auto

echo.
echo Server berhenti.
pause
