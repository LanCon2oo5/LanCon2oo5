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

@pytest.mark.parametrize("status", [401, 403, 429])
def test_api_errors_are_translated(status):
    client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    with pytest.raises(PancakeApiError) as exc: PancakeApiAdapter("x", client=client).check_connection()
    assert exc.value.status_code == status
