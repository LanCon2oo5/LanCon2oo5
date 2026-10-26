import httpx
import pytest

from app.services.pancake_api import PancakeApiAdapter, PancakeApiClient, PancakeApiError


def test_generate_page_token_uses_post_and_user_token():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path.endswith("/pages/42/generate_page_access_token")
        assert request.url.params["access_token"] == "user-secret"
        return httpx.Response(200, json={"page_access_token": "page-secret"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert PancakeApiAdapter("user-secret", client=client).generate_page_access_token("42") == "page-secret"


def test_generate_page_token_does_not_return_secret_on_bad_response():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True})))
    try:
        PancakeApiAdapter("user-secret", client=client).generate_page_access_token("42")
    except PancakeApiError as exc:
        assert "user-secret" not in str(exc)
        assert "page-secret" not in str(exc)
    else:
        raise AssertionError("expected PancakeApiError")


def test_missing_token_response_preserves_safe_diagnostics():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"success": True, "data": {"ok": True}}, headers={"content-type": "application/json"})))
    with pytest.raises(PancakeApiError) as caught:
        PancakeApiAdapter("user-secret", client=client).generate_page_access_token("42")
    diagnostics = caught.value.diagnostics
    assert diagnostics.http_status == 200
    assert diagnostics.content_type == "application/json"
    assert diagnostics.top_level_fields == ("data", "success")
    assert diagnostics.token_present is False
    assert "user-secret" not in str(diagnostics)


@pytest.mark.parametrize("message, expected", [("Permission denied for this page", "Permission denied"), ({"code": "PAGE_ADMIN", "detail": "hidden"}, "message object; fields: code, detail"), ([{"detail": "hidden"}], "message list; items: 1")])
def test_business_error_message_is_safe(message, expected):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"success": False, "message": message, "page_access_token": None})))
    with pytest.raises(PancakeApiError) as caught:
        PancakeApiAdapter("user-secret", client=client).generate_page_access_token("42")
    diagnostics = caught.value.diagnostics
    assert expected in diagnostics.error_message
    assert diagnostics.http_status == 200
    assert diagnostics.token_field_exists is True
    assert diagnostics.token_is_null is True
    assert diagnostics.token_present is False


def test_empty_token_is_diagnosed_without_exposing_value():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"success": False, "message": "empty", "page_access_token": ""})))
    with pytest.raises(PancakeApiError) as caught:
        PancakeApiAdapter("user-secret", client=client).generate_page_access_token("42")
    diagnostics = caught.value.diagnostics
    assert diagnostics.token_field_exists is True
    assert diagnostics.token_value_type == "str"
    assert diagnostics.token_is_empty is True
    assert diagnostics.token_present is False


def test_generate_page_token_timeout_does_not_retry():
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("timeout")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(PancakeApiError) as caught:
        PancakeApiAdapter("user-secret", client=client).generate_page_access_token("42")
    assert len(calls) == 1
    assert caught.value.diagnostics.http_status is None
    assert "không tạo lại token" in str(caught.value)


def test_page_token_connection_rejects_business_failure_on_http_200():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json={"success": False, "message": "page_access_token=hidden"}
    )))
    page_client = PancakeApiClient("42", "page-secret", client=client)
    with pytest.raises(PancakeApiError) as caught:
        page_client.check_connection()
    assert caught.value.status_code == 200
    assert "hidden" not in str(caught.value)
    assert "page_access_token" not in str(caught.value)


def test_generate_page_token_curl_uses_placeholder_and_current_post_shape():
    curl = PancakeApiAdapter.generate_page_token_curl("42")
    assert curl == 'curl -X POST "https://pages.fm/api/v1/pages/42/generate_page_access_token?access_token=YOUR_USER_ACCESS_TOKEN" -H "Accept: application/json"'
    assert "user-secret" not in curl
    assert "page-secret" not in curl
