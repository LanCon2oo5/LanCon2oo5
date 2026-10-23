import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from app.main import create_app


def test_window_can_be_created(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app, db, window = create_app()
    assert window.windowTitle() == "Pancake Desktop Toolkit"
    assert window.nav.count() == 8
    db.close()
