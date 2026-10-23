from datetime import date
from app.services import token_metadata
from app.services.token_store import save_page_token, get_page_token, delete_page_token

def test_page_tokens_are_independent(monkeypatch):
    values={}
    monkeypatch.setattr('app.services.token_store.keyring.set_password', lambda s,k,v: values.__setitem__(k,v))
    monkeypatch.setattr('app.services.token_store.keyring.get_password', lambda s,k: values.get(k))
    monkeypatch.setattr('app.services.token_store.keyring.delete_password', lambda s,k: values.pop(k))
    save_page_token('1','one'); save_page_token('2','two')
    assert get_page_token('1') == 'one' and get_page_token('2') == 'two'
    delete_page_token('1'); assert get_page_token('1') is None and get_page_token('2') == 'two'

def test_expiry_warnings():
    assert token_metadata.expiry_info('2026-10-24', today=date(2026,10,23))['warning'] == 'Hết hạn trong 3 ngày'
    assert token_metadata.expiry_info('2026-10-22', today=date(2026,10,23))['expired'] is True
