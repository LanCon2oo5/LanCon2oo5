import sqlite3
from app.db.database import Database, DatabaseError
from app.services.token_store import save_page_token, get_page_token, delete_page_token

def test_database_persists_and_migrates(tmp_path):
    path=tmp_path/'data.sqlite3'; db=Database(path); db.initialize(); db.connection.execute("INSERT INTO settings(key,value) VALUES('x','y')"); db.connection.commit(); db.close()
    db=Database(path); db.initialize(); assert db.connection.execute("SELECT value FROM settings WHERE key='x'").fetchone()[0]=='y'; assert 'token_status' in {r[1] for r in db.connection.execute('PRAGMA table_info(pages)')}; db.close()

def test_database_permission_failure(tmp_path, monkeypatch):
    blocked=tmp_path/'blocked'; monkeypatch.setattr('pathlib.Path.mkdir', lambda *a, **k: (_ for _ in ()).throw(PermissionError('denied')))
    try:
        Database(blocked/'data.sqlite3')
    except DatabaseError as exc:
        assert 'Không thể mở dữ liệu' in str(exc)
    else: raise AssertionError('expected DatabaseError')

def test_credential_store_mock(monkeypatch):
    values={}; monkeypatch.setattr('app.services.token_store.keyring.set_password', lambda s,k,v: values.__setitem__(k,v)); monkeypatch.setattr('app.services.token_store.keyring.get_password', lambda s,k: values.get(k)); monkeypatch.setattr('app.services.token_store.keyring.delete_password', lambda s,k: values.pop(k))
    save_page_token('fake-page','fake-token'); assert get_page_token('fake-page')=='fake-token'; delete_page_token('fake-page'); assert get_page_token('fake-page') is None
