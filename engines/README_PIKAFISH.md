# Hướng dẫn cài đặt Pikafish Engine

Pikafish là engine cờ tướng **mạnh nhất mã nguồn mở** thế giới,
dựa trên Stockfish với neural network (NNUE) chuyên dụng cho cờ tướng.

---

## Bước 1 – Tải Pikafish

Truy cập trang release chính thức:

> https://github.com/official-pikafish/Pikafish/releases/latest

Tải về **2 file** (tên có thể thay đổi theo phiên bản):

| File | Mô tả |
|------|-------|
| `pikafish-windows-x86-64-avx2.exe` | Binary engine (Windows) |
| `pikafish.nnue` | File neural network (bắt buộc) |

---

## Bước 2 – Đặt vào thư mục `engines/`

Đổi tên binary thành **`pikafish.exe`** rồi copy cả hai file vào:

```
e:\CO-TUONG-main\engines\
├── pikafish.exe     ← engine binary
└── pikafish.nnue    ← neural network weights
```

> ⚠️ File `.nnue` **phải nằm cùng thư mục** với `pikafish.exe`.

---

## Bước 3 – Khởi động lại game

Khởi động lại `client.py`. Trong chế độ **PvE (Đấu với máy)**,
thanh bên phải sẽ hiện nhãn **Engine: PIKAFISH** màu xanh lá.

---

## Kiểm tra nhanh

Chạy lệnh sau trong thư mục gốc:

```powershell
python -c "from pikafish_engine import is_pikafish_available; print('OK' if is_pikafish_available() else 'NOT FOUND')"
```

---

## Độ khó khi dùng Pikafish

| Chế độ | Thời gian suy nghĩ |
|--------|-------------------|
| EASY   | 300 ms |
| MEDIUM | 1500 ms |
| HARD   | 4000 ms |

Ở cài đặt HARD, Pikafish có thể đạt trình độ **kiện tướng quốc gia**.

---

## Lưu ý

- Nếu không có `pikafish.exe`, game sẽ tự động dùng **Custom AI** (tốt, nhưng yếu hơn Pikafish).
- Pikafish yêu cầu CPU hỗ trợ **AVX2** (hầu hết CPU Intel/AMD từ 2013 trở đi đều được).
  Nếu game báo lỗi khi khởi động, thử tải file `pikafish-windows-x86-64.exe` (không có `-avx2`).
