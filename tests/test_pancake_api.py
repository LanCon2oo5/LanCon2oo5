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

def test_categorized_structure_is_summarized_without_parsing_guesswork():
    payload = {"categorized": {"facebook": [{"id": "hidden"}], "zalo": [], "meta": {"count": 1}}, "success": True}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    with pytest.raises(PancakeApiError) as caught:
        PancakeApiAdapter("secret", client=client).list_pages()
    diagnostics = caught.value.diagnostics
    assert diagnostics.categorized_type == "dict"
    assert diagnostics.categorized_keys == ("facebook", "meta", "zalo")
    assert "facebook" in diagnostics.collection_candidates
    assert "facebook: list/1" in diagnostics.categorized_summary
    assert "hidden" not in str(diagnostics)

def test_activated_item_shape_is_summarized_without_values():
    payload = {"categorized": {"activated": [{"id": "hidden", "name": "Hidden Name", "enabled": True}], "activated_page_ids": ["hidden"]}, "success": True}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    pages, diagnostics = PancakeApiAdapter("secret", client=client).list_pages_with_diagnostics()
    assert len(pages) == 1
    assert diagnostics.activated_item_type == "dict"
    assert diagnostics.activated_item_keys == ("enabled", "id", "name")
    assert "id: str" in diagnostics.activated_field_types
    assert "Hidden Name" not in str(diagnostics)

def test_categorized_activated_parses_seven_pages_without_counting_ids():
    activated = [{"id": str(i), "name": f"Page {i}", "platform": "facebook", "is_activated": True, "role_in_page": "admin"} for i in range(7)]
    payload = {"success": True, "categorized": {"activated": activated, "activated_page_ids": [str(i) for i in range(7)], "hidden": [], "inactivated": [], "nopermission": []}}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    pages, diagnostics = PancakeApiAdapter("secret", client=client).list_pages_with_diagnostics()
    assert len(pages) == 7 and pages[0].page_id == "0" and pages[0].name == "Page 0"
    assert diagnostics.list_location == "categorized.activated"
    assert diagnostics.skipped_count == 0


def test_categorized_activated_preserves_role_in_page():
    payload = {"success": True, "categorized": {"activated": [{"id": "42", "name": "Shop", "role_in_page": "admin"}]}}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    pages = PancakeApiAdapter("secret", client=client).list_pages()
    assert pages[0].role_in_page == "admin"

def test_categorized_activated_skips_invalid_and_duplicate_ids():
    activated = [{"id": "1", "name": "One"}, {"id": "1", "name": "Duplicate"}, {"id": "2"}, {"id": "3", "name": "Three"}]
    payload = {"success": True, "categorized": {"activated": activated}}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    pages, diagnostics = PancakeApiAdapter("secret", client=client).list_pages_with_diagnostics()
    assert [page.page_id for page in pages] == ["1", "3"]
    assert diagnostics.skipped_count == 2

def test_categorized_activated_empty_is_successful_empty_list():
    payload = {"success": True, "categorized": {"activated": [], "activated_page_ids": []}}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    pages, diagnostics = PancakeApiAdapter("secret", client=client).list_pages_with_diagnostics()
    assert pages == [] and diagnostics.list_location == "categorized.activated"

@pytest.mark.parametrize("status", [401, 403, 429])
def test_api_errors_are_translated(status):
    client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    with pytest.raises(PancakeApiError) as exc: PancakeApiAdapter("x", client=client).check_connection()
    assert exc.value.status_code == status
