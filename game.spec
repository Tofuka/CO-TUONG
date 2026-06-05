# -*- mode: python ; coding: utf-8 -*-
# game.spec – PyInstaller specification cho Cờ Tướng & Cờ Úp
# Đóng gói: --onedir  (game.exe + engines/ nằm cùng thư mục)
# Tên exe: game.exe

a = Analysis(
    ['client.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # --- Game modules (lazy imports trong functions) ---
        'ai',
        'models',
        'rules',
        'pikafish_engine',
        # --- Pygame ---
        'pygame',
        'pygame.mixer',
        'pygame.font',
        'pygame.display',
        'pygame.event',
        'pygame.draw',
        'pygame.transform',
        # --- WebSocket (lazy import trong WebSocketClientThread.run) ---
        'websocket',
        'websocket._core',
        'websocket._http',
        'websocket._handshake',
        'websocket._logging',
        'websocket._socket',
        'websocket._ssl_compat',
        'websocket._utils',
        'websocket._abnf',
        'websocket._cookiejar',
        'websocket._exceptions',
        'websocket._url',
        # --- asyncio (được dùng trong ai.py) ---
        'asyncio',
        'asyncio.coroutines',
        # --- http (cần cho websocket) ---
        'http',
        'http.cookies',
        'http.client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Chỉ exclude các package thực sự không dùng đến
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'cv2',
        'fastapi',
        'uvicorn',
        'starlette',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],                         # NOT a.binaries here – onedir mode
    exclude_binaries=True,      # onedir: binaries go to COLLECT
    name='game',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python312.dll'],
    console=False,              # windowed – no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python312.dll'],
    name='CoTuong',             # Output folder: dist\CoTuong\
)
