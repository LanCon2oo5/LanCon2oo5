# Pancake Desktop Toolkit

Ứng dụng desktop Windows 10/11, Python 3.13 + PySide6, chạy local và lưu SQLite.

## Chạy phát triển

```bat
.venv\Scripts\python.exe -m app.main
```

## Kiểm thử và đóng gói

```bat
.venv\Scripts\python.exe -m pytest -q
build.bat
```

Bản portable nằm tại `dist\PancakeDesktopToolkit\PancakeDesktopToolkit.exe`. Có thể copy cả thư mục `dist\PancakeDesktopToolkit` sang máy Windows khác. Dữ liệu người dùng được lưu tại `%APPDATA%\PancakeDesktopToolkit\data.sqlite3`, nằm ngoài thư mục đóng gói.

Giai đoạn 1 chưa dùng token thật, chưa gọi Pancake API và chưa gửi tin nhắn. Các khu vực chưa tích hợp hiển thị “Chưa kết nối”.
