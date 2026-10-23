from __future__ import annotations

from datetime import datetime, timezone
import keyring
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QFrame, QLabel, QListWidget, QMainWindow, QStackedWidget, QStatusBar, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit, QPushButton, QMessageBox)
from app.services.pancake_api import PancakeApiAdapter, PancakeApiError
from app.services.pancake_api import PancakeApiClient
from app.services.token_store import save_page_token, delete_page_token, get_page_token
from app.services.token_metadata import estimated_expiry, expiry_info

class ApiWorker(QThread):
    done = Signal(object, object)
    def __init__(self, token, pages=False): super().__init__(); self.token=token; self.pages=pages
    def run(self):
        try:
            api=PancakeApiAdapter(self.token); self.done.emit(api.list_pages() if self.pages else api.check_connection(), None)
        except PancakeApiError as exc: self.done.emit(None, str(exc))


class MainWindow(QMainWindow):
    def __init__(self, database=None):
        super().__init__()
        self.database=database; self.worker=None
        self.setWindowTitle("Pancake Desktop Toolkit")
        self.resize(1180, 720)
        self.setMinimumSize(960, 600)
        self.setStyleSheet("""
        QMainWindow, QWidget { background: #f5f7fb; color: #172033; font-family: Segoe UI; }
        QListWidget { background: #111827; color: #dbe4f0; border: 0; padding: 12px 8px; font-size: 14px; }
        QListWidget::item { padding: 13px 14px; border-radius: 8px; margin: 2px 0; }
        QListWidget::item:selected { background: #2563eb; color: white; }
        QFrame#card { background: white; border: 1px solid #e5eaf2; border-radius: 12px; }
        QLabel#title { font-size: 24px; font-weight: 700; }
        QLabel#muted { color: #667085; }
        QLabel#metric { font-size: 28px; font-weight: 700; color: #2563eb; }
        """)
        self.nav = QListWidget()
        self.pages = QStackedWidget()
        items = ["Tổng quan", "Tài khoản Pancake", "Fanpage", "Hội thoại", "Tự động gắn thẻ", "Trả lời tự động", "Nhật ký hoạt động", "Cài đặt"]
        self.nav.addItems(items)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        for name in items:
            self.pages.addWidget(self._page(name))
        layout = QWidget(); root = QVBoxLayout(layout); root.setContentsMargins(0, 0, 0, 0)
        body = QWidget(); body_layout = QVBoxLayout(body); body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.addWidget(self.pages)
        from PySide6.QtWidgets import QHBoxLayout
        split = QHBoxLayout(); split.setContentsMargins(0, 0, 0, 0); split.addWidget(self.nav, 0); split.addWidget(body, 1)
        root.addLayout(split); self.setCentralWidget(layout)
        self.setStatusBar(QStatusBar()); self.statusBar().showMessage("Sẵn sàng • Chế độ local, API chưa kết nối")
        self.nav.setCurrentRow(0)

    def _page(self, name: str) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(32, 28, 32, 28); layout.setSpacing(18)
        title = QLabel(name); title.setObjectName("title"); layout.addWidget(title)
        if name == "Tài khoản Pancake":
            card=QFrame(); card.setObjectName("card"); box=QVBoxLayout(card); box.addWidget(QLabel("Public API Access Token (User Access Token)")); self.token_input=QLineEdit(); self.token_input.setEchoMode(QLineEdit.Password); self.token_input.setPlaceholderText("Dán token Pancake tại đây"); box.addWidget(self.token_input); row=QHBoxLayout(); self.check_btn=QPushButton("Kiểm tra kết nối"); self.save_btn=QPushButton("Lưu token"); self.delete_btn=QPushButton("Xóa token"); [row.addWidget(b) for b in (self.check_btn,self.save_btn,self.delete_btn)]; box.addLayout(row); self.account_status=QLabel("Chưa kết nối"); box.addWidget(self.account_status); layout.addWidget(card); self.check_btn.clicked.connect(self.check_connection); self.save_btn.clicked.connect(self.save_token); self.delete_btn.clicked.connect(self.delete_token)
        elif name == "Fanpage":
            card=QFrame(); card.setObjectName("card"); box=QVBoxLayout(card); self.refresh_btn=QPushButton("Làm mới danh sách"); self.page_list=QListWidget(); self.page_token=QLineEdit(); self.page_token.setEchoMode(QLineEdit.Password); self.page_token.setPlaceholderText("Page Access Token của Fanpage được chọn"); self.page_save=QPushButton("Lưu Page Token"); self.page_delete=QPushButton("Xóa Page Token"); self.page_check=QPushButton("Kiểm tra kết nối"); self.sync_status=QLabel("Chưa đồng bộ"); box.addWidget(self.refresh_btn); box.addWidget(self.page_list); box.addWidget(self.page_token); row=QHBoxLayout(); [row.addWidget(b) for b in (self.page_save,self.page_delete,self.page_check)]; box.addLayout(row); box.addWidget(self.sync_status); layout.addWidget(card); self.refresh_btn.clicked.connect(self.refresh_pages); self.page_list.currentRowChanged.connect(self.page_selected); self.page_save.clicked.connect(self.save_page); self.page_delete.clicked.connect(self.delete_page); self.page_check.clicked.connect(self.check_page)
        elif name == "Tổng quan":
            sub = QLabel("Theo dõi hoạt động của Pancake Desktop Toolkit"); sub.setObjectName("muted"); layout.addWidget(sub)
            row = QHBoxLayout()
            for label, value in [("Tài khoản", "0"), ("Fanpage", "0"), ("Hội thoại", "0"), ("Kết nối API", "Chưa kết nối")]:
                card = QFrame(); card.setObjectName("card"); box = QVBoxLayout(card); box.addWidget(QLabel(label)); metric = QLabel(value); metric.setObjectName("metric"); box.addWidget(metric); row.addWidget(card)
            layout.addLayout(row)
            note = QLabel("Chưa có dữ liệu. Hãy thêm tài khoản khi kết nối Pancake API được triển khai."); note.setObjectName("muted"); layout.addWidget(note); layout.addStretch()
        else:
            card = QFrame(); card.setObjectName("card"); box = QVBoxLayout(card); state = QLabel("Chưa kết nối"); state.setStyleSheet("color:#b45309;font-weight:600;font-size:16px"); box.addWidget(state); box.addWidget(QLabel("Tính năng này sẽ được triển khai ở giai đoạn tích hợp tiếp theo.")); layout.addWidget(card); layout.addStretch()
        return page

    def run_worker(self, pages=False):
        token=self.token_input.text().strip()
        if not token: QMessageBox.warning(self,"Thiếu token","Vui lòng nhập Public API Access Token."); return
        self.worker=ApiWorker(token,pages); self.worker.done.connect(self.worker_done); self.worker.start()
    def check_connection(self): self.account_status.setText("Đang kiểm tra..."); self.run_worker()
    def refresh_pages(self): self.sync_status.setText("Đang đồng bộ..."); self.run_worker(True)
    def worker_done(self, result, error):
        if error: self.account_status.setText(error); self.sync_status.setText(error); return
        if isinstance(result,list):
            self.page_list.clear(); [self.page_list.addItem(f"{p.name} — Page ID: {p.page_id}") for p in result]; now=datetime.now(timezone.utc).isoformat(); self.sync_status.setText(f"Đã đồng bộ {len(result)} Fanpage lúc {now}");
            if self.database: self.database.replace_pages([(p.page_id,p.name) for p in result],now)
        else: self.account_status.setText("Kết nối thành công")
    def selected_page_id(self):
        item=self.page_list.currentItem(); return item.text().rsplit("Page ID: ",1)[-1] if item and "Page ID: " in item.text() else None
    def page_selected(self, _):
        pid=self.selected_page_id(); self.page_token.setText(get_page_token(pid) or "" if pid else "")
    def save_page(self):
        pid=self.selected_page_id()
        if not pid: QMessageBox.warning(self,"Chưa chọn Fanpage","Hãy chọn một Fanpage trước."); return
        try: save_page_token(pid,self.page_token.text()); now=datetime.now(timezone.utc).isoformat(); self.database.update_page_token_metadata(pid,now,estimated_expiry(now),True,"Đã lưu - chưa kiểm tra") if self.database else None; self.sync_status.setText("Đã lưu Page Token an toàn")
        except Exception as exc: self.sync_status.setText(str(exc))
    def delete_page(self):
        pid=self.selected_page_id()
        if pid: delete_page_token(pid); self.page_token.clear(); self.database.set_page_token_status(pid,"Chưa cấu hình") if self.database else None; self.sync_status.setText("Đã xóa Page Token")
    def check_page(self):
        pid=self.selected_page_id(); token=self.page_token.text().strip()
        if not pid or not token: QMessageBox.warning(self,"Thiếu thông tin","Hãy chọn Fanpage và nhập Page Token."); return
        try: PancakeApiClient(pid,token).check_connection(); self.database.set_page_token_status(pid,"Đã kết nối") if self.database else None; self.sync_status.setText("Page Token hợp lệ và đã kết nối")
        except PancakeApiError as exc: self.database.set_page_token_status(pid,"Cần xác thực lại") if self.database else None; self.sync_status.setText(str(exc))
    def save_token(self):
        token=self.token_input.text().strip()
        if not token: QMessageBox.warning(self,"Thiếu token","Vui lòng nhập token trước khi lưu."); return
        keyring.set_password("PancakeDesktopToolkit","public_api_access_token",token); self.account_status.setText("Đã lưu token an toàn")
    def delete_token(self):
        try: keyring.delete_password("PancakeDesktopToolkit","public_api_access_token")
        except keyring.errors.PasswordDeleteError: pass
        self.token_input.clear(); self.account_status.setText("Đã xóa token")
