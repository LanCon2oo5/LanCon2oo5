import httpx

from app.services.pancake_api import PancakeApiAdapter, PancakeApiError


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
