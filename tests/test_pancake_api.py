import httpx
import pytest
from app.services.pancake_api import PancakeApiAdapter, PancakeApiError

def test_list_pages_uses_official_user_token_query():
    def handler(request):
        assert request.url.path == "/api/v1/pages"
        assert request.url.params["access_token"] == "secret"
        return httpx.Response(200, json={"data": [{"id": 123, "name": "Shop"}]})
    pages = PancakeApiAdapter("secret", client=httpx.Client(transport=httpx.MockTransport(handler))).list_pages()
    assert pages[0].page_id == "123" and pages[0].name == "Shop"

def test_list_pages_parses_nested_pages_and_diagnostics():
    payload = {"data": {"pages": [{"page_id": "42", "title": "Nested Shop"}]}, "success": True}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    pages, diagnostics = PancakeApiAdapter("secret", client=client).list_pages_with_diagnostics()
    assert len(pages) == 1 and pages[0].page_id == "42"
    assert diagnostics.http_status == 200 and diagnostics.parsed_count == 1
    assert diagnostics.top_level_fields == ("data", "success")

def test_list_pages_rejects_unexpected_response_shape():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"success": True})))
    with pytest.raises(PancakeApiError):
        PancakeApiAdapter("secret", client=client).list_pages()

def test_diagnostics_survive_parser_failure_and_redact_token():
    payload = {"success": False, "error": {"code": "AUTH", "message": "bad access_token=top-secret"}}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403, json=payload, headers={"content-type": "application/json"})))
    with pytest.raises(PancakeApiError) as caught:
        PancakeApiAdapter("top-secret", client=client).list_pages()
    error = caught.value
    assert error.status_code == 403
    assert error.diagnostics.content_type == "application/json"
    assert error.diagnostics.top_level_fields == ("error", "success")
    assert error.diagnostics.success is False
    assert "top-secret" not in error.diagnostics.error_message

@pytest.mark.parametrize("status", [401, 403, 429])
def test_api_errors_are_translated(status):
    client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    with pytest.raises(PancakeApiError) as exc: PancakeApiAdapter("x", client=client).check_connection()
    assert exc.value.status_code == status
