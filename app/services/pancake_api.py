from dataclasses import dataclass
import time
import re
from typing import Any
import httpx

class PancakeApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None, diagnostics=None):
        super().__init__(message); self.status_code = status_code; self.diagnostics = diagnostics

@dataclass(frozen=True)
class PancakePage:
    page_id: str
    name: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class PageListDiagnostics:
    http_status: int
    api_success: bool
    response_type: str
    top_level_fields: tuple[str, ...]
    parsed_count: int
    content_type: str = ""
    json_type: str = "unknown"
    success: object = None
    error_code: object = None
    error_message: str = ""
    list_location: str = "not found"

class PancakeApiAdapter:
    BASE_URL = "https://pages.fm/api/v1"
    def __init__(self, access_token: str, timeout: float = 15.0, client: httpx.Client | None = None):
        self.access_token = access_token.strip(); self.timeout = timeout; self._client = client; self.last_page_diagnostics = None
    def _request(self, path: str) -> Any:
        if not self.access_token: raise PancakeApiError("Vui lòng nhập Public API Access Token.")
        owns = self._client is None; client = self._client or httpx.Client(timeout=self.timeout)
        try: response = client.get(f"{self.BASE_URL}{path}", params={"access_token": self.access_token})
        except httpx.RequestError as exc: raise PancakeApiError("Không thể kết nối Pancake. Hãy kiểm tra mạng và thử lại.") from exc
        finally:
            if owns: client.close()
        try: payload = response.json()
        except ValueError:
            raise PancakeApiError(f"Pancake trả về dữ liệu không phải JSON (HTTP {response.status_code}).", response.status_code)
        top = tuple(sorted(payload.keys())) if isinstance(payload, dict) else ()
        success = payload.get("success") if isinstance(payload, dict) else None
        err = payload.get("error") if isinstance(payload, dict) else None
        err_code = err.get("code") if isinstance(err, dict) else None
        err_message = err.get("message") if isinstance(err, dict) else (str(err) if err else "")
        err_message = re.sub(r"https?://\S+|access_token=[^&\s]+|page_access_token=[^&\s]+", "[redacted]", str(err_message))[:300]
        self.last_page_diagnostics = PageListDiagnostics(response.status_code, response.is_success and success is not False, type(payload).__name__, top, 0, response.headers.get("content-type", ""), type(payload).__name__, success, err_code, err_message)
        messages = {401:"Token không hợp lệ hoặc đã hết hạn (401).",403:"Không có quyền truy cập Fanpage (403).",429:"Pancake đang giới hạn số lần gọi API (429)."}
        if response.status_code in messages: raise PancakeApiError(messages[response.status_code], response.status_code, self.last_page_diagnostics)
        if response.is_error or success is False: raise PancakeApiError(err_message or f"Pancake trả về lỗi HTTP {response.status_code}.", response.status_code, self.last_page_diagnostics)
        return payload
    def list_pages(self) -> list[PancakePage]:
        payload = self._request("/pages")
        return self._parse_pages(payload, http_status=self.last_page_diagnostics.http_status if self.last_page_diagnostics else 200)

    def _parse_pages(self, payload: Any, http_status: int = 200) -> list[PancakePage]:
        top_fields = tuple(sorted(payload.keys())) if isinstance(payload, dict) else ()
        if isinstance(payload, dict) and not any(key in payload for key in ("data", "pages", "items", "results")):
            raise PancakeApiError("Dữ liệu danh sách Fanpage thiếu trường danh sách.", http_status, self.last_page_diagnostics)
        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(rows, dict):
            rows = rows.get("pages", rows.get("items", rows.get("results", [])))
        if not isinstance(rows, list):
            raise PancakeApiError("Dữ liệu danh sách Fanpage không đúng định dạng.", http_status, self.last_page_diagnostics)
        pages = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            page_id = row.get("id", row.get("page_id"))
            if page_id is None:
                continue
            pages.append(PancakePage(str(page_id), str(row.get("name") or row.get("title") or page_id), row))
        old = self.last_page_diagnostics
        self.last_page_diagnostics = PageListDiagnostics(http_status, True, type(payload).__name__, top_fields, len(pages), old.content_type if old else "", old.json_type if old else type(payload).__name__, old.success if old else None, old.error_code if old else None, old.error_message if old else "", "data" if isinstance(payload, dict) and "data" in payload else "top-level")
        return pages

    def list_pages_with_diagnostics(self) -> tuple[list[PancakePage], PageListDiagnostics]:
        pages = self.list_pages()
        return pages, self.last_page_diagnostics

    def generate_page_access_token(self, page_id: str) -> str:
        if not self.access_token:
            raise PancakeApiError("Vui lòng nhập Public API Access Token.")
        owns = self._client is None
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            response = client.post(
                f"{self.BASE_URL}/pages/{str(page_id).strip()}/generate_page_access_token",
                params={"access_token": self.access_token},
            )
        except httpx.RequestError as exc:
            raise PancakeApiError("Không thể kết nối Pancake. Hãy kiểm tra mạng và thử lại.") from exc
        finally:
            if owns:
                client.close()
        messages = {401: "Token không hợp lệ hoặc đã hết hạn (401).", 403: "Bạn không có quyền quản trị Fanpage này (403).", 429: "Pancake đang giới hạn số lần gọi API (429). Vui lòng thử lại sau."}
        if response.status_code in messages:
            raise PancakeApiError(messages[response.status_code], response.status_code)
        if response.is_error:
            raise PancakeApiError(f"Pancake trả về lỗi HTTP {response.status_code}.", response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise PancakeApiError("Pancake trả về dữ liệu không hợp lệ.") from exc
        token = payload.get("page_access_token") if isinstance(payload, dict) else None
        if not token and isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            token = payload["data"].get("page_access_token")
        if not isinstance(token, str) or not token.strip():
            raise PancakeApiError("Pancake không trả về Page Access Token.")
        return token.strip()

    def check_connection(self) -> bool: self.list_pages(); return True

class PancakeApiClient:
    """Page-scoped public API client. Secrets are accepted only in memory."""
    BASE_URL = "https://pages.fm/api/public_api/v2"
    def __init__(self, page_id: str, page_access_token: str, timeout: float = 15.0, client=None):
        self.page_id = str(page_id); self.token = page_access_token.strip(); self.timeout = timeout; self._client = client
    def request(self, path: str, params=None):
        if not self.token: raise PancakeApiError("Chưa cấu hình Page Access Token.")
        owns=self._client is None; client=self._client or httpx.Client(timeout=self.timeout)
        query=dict(params or {}); query["page_access_token"] = self.token
        try: response=client.get(f"{self.BASE_URL}/pages/{self.page_id}/{path.lstrip('/')}", params=query)
        except httpx.RequestError as exc: raise PancakeApiError("Không thể kết nối Pancake. Hãy kiểm tra mạng và thử lại.") from exc
        finally:
            if owns: client.close()
        messages={401:"Page Token không hợp lệ hoặc đã hết hạn (401).",403:"Page Token không có quyền truy cập Fanpage này (403).",429:"Pancake đang giới hạn số lần gọi API (429). Vui lòng thử lại sau."}
        if response.status_code in messages: raise PancakeApiError(messages[response.status_code], response.status_code)
        if response.is_error: raise PancakeApiError(f"Pancake trả về lỗi HTTP {response.status_code}.", response.status_code)
        try: return response.json()
        except ValueError as exc: raise PancakeApiError("Pancake trả về dữ liệu không hợp lệ.") from exc
    def check_connection(self): self.request("conversations", {"page_size": 1}); return True
    def list_conversations(self, last_conversation_id=None):
        params={"page_size":60}
        if last_conversation_id: params["last_conversation_id"]=last_conversation_id
        return self.request("conversations", params)
    def list_messages(self, conversation_id): return self.request(f"conversations/{conversation_id}/messages")
    def list_tags(self): return self.request("tags")

class ConversationSyncService:
    PAGE_SIZE = 60
    def __init__(self, api: PancakeApiClient, min_interval=0.21): self.api=api; self.min_interval=min_interval; self._last_call=0.0
    def sync(self, cancel=None, start_cursor=None, max_pages=100):
        cursor=start_cursor; seen=set(); output=[]
        for _ in range(max_pages):
            if cancel and cancel(): break
            if cursor in seen: break
            seen.add(cursor)
            delay=self.min_interval-(time.monotonic()-self._last_call)
            if delay>0: time.sleep(delay)
            payload=self.api.list_conversations(cursor); self._last_call=time.monotonic()
            rows=payload.get("data", payload) if isinstance(payload,dict) else payload
            if isinstance(rows,dict): rows=rows.get("conversations", rows.get("data", []))
            if not isinstance(rows,list) or not rows: break
            unique={str(x.get("id")):x for x in rows if isinstance(x,dict) and x.get("id") is not None}
            output.extend(unique[k] for k in unique if k not in {str(x.get('id')) for x in output})
            next_cursor=payload.get("last_conversation_id") if isinstance(payload,dict) else None
            if not next_cursor or next_cursor==cursor or len(rows)<self.PAGE_SIZE: break
            cursor=str(next_cursor)
        return output, cursor

ConversationService = PancakeApiClient
MessageService = PancakeApiClient
TagService = PancakeApiClient
