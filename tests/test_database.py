from app.db.database import Database


def test_database_initializes(tmp_path):
    db = Database(tmp_path / "data.sqlite3")
    db.initialize()
    tables = {row["name"] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"accounts", "pages", "settings", "activity_log"} <= tables
    db.close()
