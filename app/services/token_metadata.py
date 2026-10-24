"""Non-secret token expiry metadata helpers."""

from datetime import date, datetime, timedelta


ESTIMATED_TOKEN_LIFETIME_DAYS = 30


def estimated_expiry(entered_at: str | datetime) -> str:
    if isinstance(entered_at, datetime):
        entered = entered_at
    else:
        entered = datetime.fromisoformat(str(entered_at).replace("Z", "+00:00"))
    return (entered.date() + timedelta(days=ESTIMATED_TOKEN_LIFETIME_DAYS)).isoformat()


def expiry_info(expires_at: str | date | None, today: date | None = None) -> dict[str, object]:
    if not expires_at:
        return {"expired": False, "days_remaining": None, "warning": None}
    expiry = expires_at if isinstance(expires_at, date) else date.fromisoformat(str(expires_at)[:10])
    current = today or date.today()
    days = (expiry - current).days
    if days < 0:
        return {"expired": True, "days_remaining": days, "warning": "Đã hết hạn"}
    warning = None
    if days <= 3:
        warning = "Hết hạn trong 3 ngày"
    elif days <= 7:
        warning = "Hết hạn trong 7 ngày"
    elif days <= 14:
        warning = "Hết hạn trong 14 ngày"
    return {"expired": False, "days_remaining": days, "warning": warning}
