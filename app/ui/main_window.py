from __future__ import annotations

from datetime import datetime, timezone
import keyring
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QListWidget, QMainWindow, QStackedWidget, QStatusBar, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit, QPushButton, QMessageBox, QSplitter, QPlainTextEdit)
from app.services.pancake_api import PancakeApiAdapter, PancakeApiError, ConversationSyncService
from app.services.pancake_api import PancakeApiClient
from app.services.token_store import save_page_token, delete_page_token, get_page_token
from app.services.token_metadata import estimated_expiry, expiry_info

class ApiWorker(QThread):
    done = Signal(object, object)
    def __init__(self, token, pages=False): super().__init__(); self.token=token; self.pages=pages
    def run(self):
        try:
            api=PancakeApiAdapter(self.token); self.done.emit(api.list_pages_with_diagnostics() if self.pages else api.check_connection(), None)
        except PancakeApiError as exc: self.done.emit(None, exc)

class ConversationWorker(QThread):
    done=Signal(object,object)
    def __init__(self,page_id,token): super().__init__(); self.page_id=page_id; self.token=token; self.cancelled=False
    def cancel(self): self.cancelled=True
    def run(self):
        try: self.done.emit(ConversationSyncService(PancakeApiClient(self.page_id,self.token)).sync(lambda:self.cancelled),None)
        except PancakeApiError as exc: self.done.emit(None,str(exc))


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
        self.nav.setFixedWidth(240)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
            card=QFrame(); card.setObjectName("card"); box=QVBoxLayout(card); self.refresh_btn=QPushButton("Làm mới danh sách"); self.page_list=QListWidget(); self.page_token=QLineEdit(); self.page_token.setEchoMode(QLineEdit.Password); self.page_token.setPlaceholderText("Page Access Token thủ công (tuỳ chọn)"); self.page_connect=QPushButton("Kết nối Fanpage"); self.page_save=QPushButton("Lưu Page Token"); self.page_delete=QPushButton("Ngắt kết nối"); self.page_check=QPushButton("Kiểm tra kết nối"); self.page_count=QLabel("Fanpage: 0"); self.page_diagnostics=QPlainTextEdit(); self.page_diagnostics.setReadOnly(True); self.page_diagnostics.setLineWrapMode(QPlainTextEdit.WidgetWidth); self.page_diagnostics.setMinimumHeight(190); self.copy_diagnostics_btn=QPushButton("Sao chép chẩn đoán"); self.sync_status=QLabel("Chưa đồng bộ"); box.addWidget(self.refresh_btn); box.addWidget(self.page_count); box.addWidget(self.page_list); box.addWidget(self.page_token); row=QHBoxLayout(); [row.addWidget(b) for b in (self.page_connect,self.page_save,self.page_delete,self.page_check)]; box.addLayout(row); diag_row=QHBoxLayout(); diag_row.addWidget(self.page_diagnostics,1); diag_row.addWidget(self.copy_diagnostics_btn,0); box.addLayout(diag_row); box.addWidget(self.sync_status); layout.addWidget(card); self.refresh_btn.clicked.connect(self.refresh_pages); self.page_list.currentRowChanged.connect(self.page_selected); self.page_connect.clicked.connect(self.connect_page); self.page_save.clicked.connect(self.save_page); self.page_delete.clicked.connect(self.delete_page); self.page_check.clicked.connect(self.check_page); self.copy_diagnostics_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.page_diagnostics.toPlainText())); self._set_page_actions_enabled(False)
        elif name == "Hội thoại":
            card=QFrame(); card.setObjectName("card"); box=QVBoxLayout(card)
            row=QHBoxLayout(); self.conversation_page=QLineEdit(); self.conversation_page.setPlaceholderText("Page ID"); self.conversation_token=QLineEdit(); self.conversation_token.setEchoMode(QLineEdit.Password); self.conversation_token.setPlaceholderText("Page Access Token"); self.sync_conversations_btn=QPushButton("Đồng bộ"); self.stop_conversations_btn=QPushButton("Dừng"); [row.addWidget(x) for x in (self.conversation_page,self.conversation_token,self.sync_conversations_btn,self.stop_conversations_btn)]; box.addLayout(row)
            self.conversation_status=QLabel("Chưa đồng bộ"); box.addWidget(self.conversation_status)
            split=QSplitter(); self.conversation_pages=QListWidget(); self.conversation_pages.addItem("Fanpage đang chọn"); self.conversation_list=QListWidget(); self.conversation_detail=QLabel("Chọn một hội thoại để xem chi tiết.\n\nĐồng bộ message chưa được bật: tài liệu Public API hiện chưa xác nhận chính xác endpoint v1 và tham số current_count."); self.conversation_detail.setWordWrap(True); self.conversation_detail.setObjectName("muted"); split.addWidget(self.conversation_pages); split.addWidget(self.conversation_list); split.addWidget(self.conversation_detail); split.setSizes([180,420,360]); box.addWidget(split); layout.addWidget(card)
            self.conversation_list.currentRowChanged.connect(self.show_conversation_detail); self.sync_conversations_btn.clicked.connect(self.sync_conversations); self.stop_conversations_btn.clicked.connect(self.stop_conversations)
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
    def refresh_pages(self): self.sync_status.setText("Đang gọi API..."); self.page_diagnostics.setPlainText("Chẩn đoán API\nTrạng thái: đang thực hiện request GET /pages..."); self.run_worker(True)
    def _set_page_actions_enabled(self, enabled):
        for button in (self.page_connect,self.page_save,self.page_delete,self.page_check): button.setEnabled(enabled)
    def worker_done(self, result, error):
        if error:
            message=str(error); self.account_status.setText(message); self.sync_status.setText(message)
            diagnostics=getattr(error,"diagnostics",None)
            if diagnostics: self.page_diagnostics.setPlainText(self._diagnostic_text(diagnostics, sqlite_count=None, ui_count=self.page_list.count(), parser_error=message))
            else: self.page_diagnostics.setPlainText(f"Chẩn đoán API:\nTrạng thái: request thất bại trước HTTP response\nLỗi: {message}")
            return
        if isinstance(result,list):
            self.page_list.clear(); [self.page_list.addItem(f"{p.name} — Page ID: {p.page_id} — Chưa kết nối") for p in result]; now=datetime.now(timezone.utc).isoformat(); self.sync_status.setText(f"Đã đồng bộ {len(result)} Fanpage lúc {now}");
            if self.database: self.database.replace_pages([(p.page_id,p.name) for p in result],now)
        elif isinstance(result, tuple) and len(result) == 2:
            pages, diagnostics = result; self.page_list.clear(); [self.page_list.addItem(f"{p.name} — Page ID: {p.page_id} — Chưa kết nối") for p in pages]; now=datetime.now(timezone.utc).isoformat(); self.page_count.setText(f"Fanpage: {len(pages)}"); sqlite_count=None
            if self.database:
                self.database.replace_pages([(p.page_id,p.name) for p in pages],now); sqlite_count=self.database.connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
            self.page_diagnostics.setPlainText(self._diagnostic_text(diagnostics, sqlite_count, len(pages))); self.sync_status.setText(f"Đã đồng bộ {len(pages)} Fanpage"); self._set_page_actions_enabled(False)
        else: self.account_status.setText("Kết nối thành công")
    def _diagnostic_text(self, diagnostics, sqlite_count=None, ui_count=None, parser_error=None):
        success = "chưa có" if diagnostics.success is None else str(diagnostics.success)
        error = f" • error: {diagnostics.error_code or '-'} {diagnostics.error_message}" if diagnostics.error_code or diagnostics.error_message else ""
        parser = f" • parser: {parser_error}" if parser_error else ""
        categorized = f" • categorized: {diagnostics.categorized_type}; keys: {', '.join(diagnostics.categorized_keys) or '-'}; children: {', '.join(diagnostics.categorized_summary) or '-'}; collections: {', '.join(x for x in diagnostics.collection_candidates if x) or '-'}" if diagnostics.categorized_type != "absent" else ""
        return "\n".join((
            "Chẩn đoán API",
            f"HTTP Status: {diagnostics.http_status}",
            f"Content-Type: {diagnostics.content_type or '-'}",
            f"JSON Type: {diagnostics.json_type}",
            f"Top-level Fields: {', '.join(diagnostics.top_level_fields) or '(không có)'}",
            f"API Success: {success}{error}",
            f"List Location: {diagnostics.list_location}",
            f"Parsed Pages: {diagnostics.parsed_count}",
            f"Skipped Invalid/Duplicate: {diagnostics.skipped_count}",
            f"SQLite Pages: {sqlite_count if sqlite_count is not None else '-'}",
            f"UI Pages: {ui_count if ui_count is not None else '-'}",
            f"categorized type: {diagnostics.categorized_type}",
            f"categorized child keys: {', '.join(diagnostics.categorized_keys) or '-'}",
            f"child types/sizes: {', '.join(diagnostics.categorized_summary) or '-'}",
            f"collection candidates: {', '.join(x for x in diagnostics.collection_candidates if x) or '-'}",
            f"activated item type: {diagnostics.activated_item_type}",
            f"activated item keys: {', '.join(diagnostics.activated_item_keys) or '-'}",
            f"activated field types: {', '.join(diagnostics.activated_field_types) or '-'}",
            *( [f"Parser: {parser_error}"] if parser_error else [] ),
        ))
    def selected_page_id(self):
        item=self.page_list.currentItem(); return item.text().split("Page ID: ",1)[-1].split(" — ",1)[0] if item and "Page ID: " in item.text() else None
    def sync_conversations(self):
        pid=self.conversation_page.text().strip(); token=self.conversation_token.text().strip()
        if not pid or not token: self.conversation_status.setText("Nhập Page ID và Page Token để đồng bộ."); return
        self.conversation_status.setText("Đang đồng bộ tối đa 60 hội thoại/lượt..."); self.conversation_worker=ConversationWorker(pid,token); self.conversation_worker.done.connect(self.conversations_done); self.conversation_worker.start()
    def stop_conversations(self):
        if getattr(self,'conversation_worker',None): self.conversation_worker.cancel(); self.conversation_status.setText("Đã yêu cầu dừng đồng bộ")
    def conversations_done(self,result,error):
        if error: self.conversation_status.setText(error); return
        rows,cursor=result; self.conversation_list.clear(); [self.conversation_list.addItem(f"{r.get('customer_name') or 'Khách hàng'} — {r.get('last_message') or 'Chưa có tin nhắn'}") for r in rows]
        if self.database:
            self.database.cache_conversations(self.conversation_page.text().strip(), rows, datetime.now(timezone.utc).isoformat())
        self.conversation_status.setText(f"Đã tải {len(rows)} hội thoại; cursor: {cursor or 'hết dữ liệu'}")
    def show_conversation_detail(self, _):
        item=self.conversation_list.currentItem()
        if item: self.conversation_detail.setText(item.text()+"\n\nMessage detail: Chưa hỗ trợ trong Giai đoạn 4A vì endpoint v1/current_count chưa được xác minh từ tài liệu chính thức.")
    def page_selected(self, _):
        pid=self.selected_page_id(); self.page_token.setText(get_page_token(pid) or "" if pid else ""); self._set_page_actions_enabled(bool(pid))
    def save_page(self):
        pid=self.selected_page_id()
        if not pid: QMessageBox.warning(self,"Chưa chọn Fanpage","Hãy chọn một Fanpage trước."); return
        try: save_page_token(pid,self.page_token.text()); now=datetime.now(timezone.utc).isoformat(); self.database.update_page_token_metadata(pid,now,None,False,"Đã lưu - chưa kiểm tra") if self.database else None; self.sync_status.setText("Đã lưu Page Token an toàn; thời hạn: chưa xác định")
        except Exception as exc: self.sync_status.setText(str(exc))
    def connect_page(self):
        pid=self.selected_page_id()
        if not pid: QMessageBox.warning(self,"Chưa chọn Fanpage","Hãy chọn một Fanpage trước."); return
        existing=get_page_token(pid)
        if existing:
            try: PancakeApiClient(pid,existing).check_connection(); self.database.set_page_token_status(pid,"Đã kết nối") if self.database else None; self.sync_status.setText("Đã tái sử dụng Page Token hiện có"); return
            except PancakeApiError: pass
        if not self.token_input.text().strip(): QMessageBox.warning(self,"Thiếu User Token","Nhập User Access Token ở trang Tài khoản Pancake trước."); return
        answer=QMessageBox.question(self,"Cấp Page Token mới","Pancake sẽ vô hiệu hóa Page Token cũ nếu có. Bạn có chắc muốn tiếp tục?",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if answer != QMessageBox.Yes: self.sync_status.setText("Đã hủy cấp Page Token"); return
        api_adapter = PancakeApiAdapter(self.token_input.text())
        try:
            token=api_adapter.generate_page_access_token(pid)
            PancakeApiClient(pid,token).check_connection(); save_page_token(pid,token)
            if self.database: self.database.update_page_token_metadata(pid,datetime.now(timezone.utc).isoformat(),None,False,"Đã kết nối")
            self.page_token.setText(token); self.sync_status.setText("Đã kết nối bằng Page Token mới; thời hạn: không tự hết hạn")
        except PancakeApiError as exc:
            self.sync_status.setText(str(exc))
            diagnostics=getattr(exc,"diagnostics",None) or api_adapter.last_token_generation_diagnostics
            if diagnostics: self.page_diagnostics.setPlainText(self._token_diagnostic_text(diagnostics, uncertain=True))
        except Exception as exc: self.sync_status.setText(str(exc))
    def _token_diagnostic_text(self, diagnostics, uncertain=False):
        success = "chưa có" if diagnostics.success is None else str(diagnostics.success)
        state = "Chưa xác định — không tạo lại token" if uncertain or diagnostics.request_state != "HTTP response received" else diagnostics.request_state
        return "\n".join(("Chẩn đoán cấp Page Token", f"Trạng thái request: {state}", f"HTTP Status: {diagnostics.http_status if diagnostics.http_status is not None else '-'}", f"Content-Type: {diagnostics.content_type or '-'}", f"JSON Type: {diagnostics.json_type}", f"Top-level Fields: {', '.join(diagnostics.top_level_fields) or '-'}", f"API Success: {success}", f"Error Code: {diagnostics.error_code or '-'}", f"Error Message: {diagnostics.error_message or '-'}", f"Token Field Location: {diagnostics.token_field_location}", f"Token Present: {diagnostics.token_present}"))
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
