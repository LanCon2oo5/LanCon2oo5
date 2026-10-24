"""Secure storage for page-scoped Pancake access tokens."""

import keyring


SERVICE_NAME = "PancakeDesktopToolkit"


def _username(page_id: str) -> str:
    value = str(page_id).strip()
    if not value:
        raise ValueError("Page ID không được để trống.")
    return f"page_access_token:{value}"


def save_page_token(page_id: str, token: str) -> None:
    value = str(token).strip()
    if not value:
        raise ValueError("Page Token không được để trống.")
    try:
        keyring.set_password(SERVICE_NAME, _username(page_id), value)
    except Exception as exc:
        raise RuntimeError("Không thể lưu Page Token vào Windows Credential Manager.") from exc


def get_page_token(page_id: str) -> str | None:
    try:
        return keyring.get_password(SERVICE_NAME, _username(page_id))
    except Exception as exc:
        raise RuntimeError("Không thể đọc Page Token từ Windows Credential Manager.") from exc


def delete_page_token(page_id: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, _username(page_id))
    except keyring.errors.PasswordDeleteError:
        return
    except Exception as exc:
        raise RuntimeError("Không thể xóa Page Token khỏi Windows Credential Manager.") from exc
