def test_token_service_modules_are_present():
    from app.services.token_store import get_page_token, save_page_token, delete_page_token
    from app.services.token_metadata import estimated_expiry, expiry_info

    assert callable(save_page_token)
    assert callable(get_page_token)
    assert callable(delete_page_token)
    assert callable(estimated_expiry)
    assert callable(expiry_info)
