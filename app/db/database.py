from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row

    def initialize(self) -> None:
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Chưa kết nối', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS pages (id TEXT PRIMARY KEY, name TEXT NOT NULL, account_id INTEGER, status TEXT NOT NULL DEFAULT 'Đã đồng bộ', synced_at TEXT, token_entered_at TEXT, token_expires_at TEXT, token_expiry_estimated INTEGER NOT NULL DEFAULT 1, token_status TEXT NOT NULL DEFAULT 'Chưa cấu hình');
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY, message TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
        self.connection.commit()
        columns={row[1] for row in self.connection.execute("PRAGMA table_info(pages)")}
        for name, definition in {"token_entered_at":"TEXT", "token_expires_at":"TEXT", "token_expiry_estimated":"INTEGER NOT NULL DEFAULT 1", "token_status":"TEXT NOT NULL DEFAULT 'Chưa cấu hình'"}.items():
            if name not in columns: self.connection.execute(f"ALTER TABLE pages ADD COLUMN {name} {definition}")
        self.connection.commit()

    def replace_pages(self, pages: list[tuple[str, str]], synced_at: str) -> None:
        ids={pid for pid, _ in pages}; existing={row[0] for row in self.connection.execute("SELECT id FROM pages")}
        self.connection.executemany("INSERT INTO pages(id, name, synced_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, synced_at=excluded.synced_at", [(pid, name, synced_at) for pid, name in pages])
        for pid in existing-ids: self.connection.execute("UPDATE pages SET status='Không còn trong tài khoản' WHERE id=?", (pid,))
        self.connection.commit()

    def update_page_token_metadata(self, page_id, entered_at, expires_at, estimated=True, status='Chưa kiểm tra'):
        self.connection.execute("UPDATE pages SET token_entered_at=?, token_expires_at=?, token_expiry_estimated=?, token_status=? WHERE id=?", (entered_at, expires_at, int(estimated), status, str(page_id))); self.connection.commit()
    def set_page_token_status(self, page_id, status): self.connection.execute("UPDATE pages SET token_status=? WHERE id=?", (status, str(page_id))); self.connection.commit()

    def close(self) -> None:
        self.connection.close()
