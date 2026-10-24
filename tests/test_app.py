import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from app.main import create_app
from app.services.pancake_api import PancakePage, PageListDiagnostics, PancakeApiError


def test_window_can_be_created(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app, db, window = create_app()
    assert window.windowTitle() == "Pancake Desktop Toolkit"
    assert window.nav.count() == 8
    db.close()


def test_page_refresh_updates_ui_and_database(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app, db, window = create_app()
    pages = [PancakePage("1", "One", {"id": 1}), PancakePage("2", "Two", {"id": 2})]
    diagnostics = PageListDiagnostics(200, True, "dict", ("data",), 2)
    window.worker_done((pages, diagnostics), None)
    assert window.page_list.count() == 2
    assert window.page_count.text() == "Fanpage: 2"
    assert db.connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0] == 2
    assert not window.page_connect.isEnabled()
    db.close()


def test_parser_error_diagnostics_reach_fanpage_ui(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app, db, window = create_app()
    diagnostics = PageListDiagnostics(200, True, "dict", ("success", "message"), 0, "application/json", "dict", True, None, "", "not found")
    error = PancakeApiError("Dữ liệu danh sách Fanpage thiếu trường danh sách.", 200, diagnostics)
    window.worker_done(None, error)
    text = window.page_diagnostics.toPlainText()
    assert "HTTP Status: 200" in text
    assert "Content-Type: application/json" in text
    assert "Top-level Fields: success, message" in text
    assert "Parser:" in text
    db.close()


def test_diagnostics_panel_is_multiline_copyable_and_sidebar_stable(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app, db, window = create_app()
    assert window.page_diagnostics.isReadOnly()
    assert window.page_diagnostics.lineWrapMode().name != "NoWrap"
    assert window.nav.width() == 240
    window.resize(960, 600)
    assert window.nav.width() == 240
    window.page_diagnostics.setPlainText("HTTP Status: 200\nContent-Type: application/json\nTop-level Fields: categorized, success\nToken: [not included]")
    window.copy_diagnostics_btn.click()
    copied = app.clipboard().text()
    assert "HTTP Status: 200" in copied
    assert "Top-level Fields: categorized, success" in copied
    assert "access_token" not in copied.lower()
    db.close()
