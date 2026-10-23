from pathlib import Path
import os
import logging
import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from app.db.database import Database, DatabaseError
from app.ui.main_window import MainWindow


def log_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PancakeDesktopToolkit" / "logs" / "startup.log"


def configure_logging() -> logging.Logger:
    path = log_path(); path.parent.mkdir(parents=True, exist_ok=True)
    try:
        logging.basicConfig(filename=path, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8", force=True)
    except (OSError, PermissionError):
        fallback = Path(os.environ.get("TEMP", Path.home())) / "PancakeDesktopToolkit" / "logs" / f"startup-{os.getpid()}.log"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=fallback, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8", force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return logging.getLogger("pancake")


LOGGER = configure_logging()


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt): return sys.__excepthook__(exc_type, exc_value, exc_traceback)
    LOGGER.critical("Unhandled exception during startup/runtime\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = handle_exception


def user_data_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / "PancakeDesktopToolkit"
    return base


def create_app() -> tuple[QApplication, Database, MainWindow]:
    LOGGER.info("startup: creating QApplication")
    qt_app = QApplication.instance() or QApplication([])
    LOGGER.info("startup: QApplication ready")
    LOGGER.info("startup: opening SQLite under AppData")
    try:
        db = Database(user_data_dir() / "data.sqlite3")
        db.initialize()
    except DatabaseError as exc:
        LOGGER.error("startup: database unavailable: %s", exc)
        QMessageBox.critical(None, "Không thể mở dữ liệu", f"{exc}\n\nỨng dụng sẽ đóng để tránh tạo database thay thế.")
        raise
    LOGGER.info("startup: SQLite ready")
    window = MainWindow(db)
    LOGGER.info("startup: MainWindow ready")
    return qt_app, db, window


def main() -> int:
    LOGGER.info("startup: main entered")
    qt_app, db, window = create_app()
    window.show()
    LOGGER.info("startup: MainWindow shown")
    result = qt_app.exec()
    db.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
