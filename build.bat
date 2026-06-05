@echo off
chcp 65001 >nul
echo ================================================
echo   BUILD: Co Tuong ^& Co Up  -^>  game.exe
echo ================================================
echo.

REM ─── Bước 1: Kiểm tra Python ───────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay Python. Hay cai dat Python 3.8+ va thu lai.
    pause & exit /b 1
)
echo [OK] Python da san sang.

REM ─── Bước 2: Cài dependencies ──────────────────────────────────────────────
echo.
echo [*] Cai dat dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install pygame websocket-client pyinstaller --quiet
if errorlevel 1 (
    echo [LOI] Cai dat pip that bai.
    pause & exit /b 1
)
echo [OK] Dependencies da san sang.

REM ─── Bước 3: Dọn build cũ ─────────────────────────────────────────────────
echo.
echo [*] Don dep build cu...
if exist dist\CoTuong rmdir /s /q dist\CoTuong
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__

REM ─── Bước 4: Build với PyInstaller ─────────────────────────────────────────
echo.
echo [*] Dang build game.exe (co the mat 1-3 phut)...
pyinstaller --noconfirm game.spec
if errorlevel 1 (
    echo [LOI] PyInstaller build that bai!
    pause & exit /b 1
)

REM ─── Bước 5: Copy engines vào dist ─────────────────────────────────────────
echo.
echo [*] Copy Pikafish engine vao dist\CoTuong\engines\...
if not exist dist\CoTuong\engines mkdir dist\CoTuong\engines
xcopy /y /q engines\pikafish.exe dist\CoTuong\engines\
xcopy /y /q engines\pikafish.nnue dist\CoTuong\engines\
echo [OK] Da copy engines.

REM ─── Hoàn thành ─────────────────────────────────────────────────────────────
echo.
echo ================================================
echo   BUILD THANH CONG!
echo   File game: dist\CoTuong\game.exe
echo   Thu muc  : dist\CoTuong\
echo ================================================
echo.
echo Nhan phim bat ky de thoat...
pause >nul
