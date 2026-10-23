from pathlib import Path
import os
from PySide6.QtWidgets import QApplication
from app.db.database import Database
from app.ui.main_window import MainWindow


def user_data_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / "PancakeDesktopToolkit"
    return base


def create_app() -> tuple[QApplication, Database, MainWindow]:
    qt_app = QApplication.instance() or QApplication([])
    db = Database(user_data_dir() / "data.sqlite3")
    db.initialize()
    window = MainWindow(db)
    return qt_app, db, window


def main() -> int:
    qt_app, db, window = create_app()
    window.show()
    result = qt_app.exec()
    db.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
