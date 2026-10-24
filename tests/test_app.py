import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from app.main import create_app
from app.services.pancake_api import PancakePage, PageListDiagnostics


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
