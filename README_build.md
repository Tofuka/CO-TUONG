Hướng dẫn đóng gói game thành file .exe (Windows)

Yêu cầu:
- Python 3.8+ cài đặt trên hệ thống
- Kết nối Internet để tải gói pip

Bước nhanh (gợi ý):
1. Mở Command Prompt hoặc PowerShell tại thư mục dự án (chứa `client.py`).
2. Chạy script build (tự động tạo virtualenv, cài dependencies và PyInstaller):

```powershell
build_exe.bat
```

Hoặc thủ công:
```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --windowed client.py
```

Kết quả:
- Tệp thực thi sẽ xuất hiện trong thư mục `dist\client.exe`.

Ghi chú & mẹo:
- Nếu bạn chỉ muốn chơi chế độ Local PvE (chơi với AI), không cần `server.py`.
- Nếu muốn đóng gói server (đa người), cần cài thêm `fastapi` và `uvicorn` và tạo exe riêng cho `server.py`.
- Nếu PyInstaller báo thiếu module, thêm `--hidden-import <module>` vào lệnh PyInstaller hoặc chỉnh sửa `client.spec`.

Nếu bạn muốn, tôi có thể:
- Tự động thêm `pyinstaller` spec file với tinh chỉnh cho assets.
- Tạo exe cho `server.py` (PvP) và hướng dẫn chạy cả server + client.
