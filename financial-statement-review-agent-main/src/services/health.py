from __future__ import annotations

from src.config import APP_ENV, OPENAI_API_KEY
from src.models import HealthResponse
from src.services.notify import notify_health_down
from src.store import store_ok


def check_health(*, alert_if_down: bool = False) -> HealthResponse:
    ok_store = store_ok()
    openai_configured = bool(OPENAI_API_KEY)

    if not ok_store:
        detail = "Statement store missing (companies.json / sample CSV)."
        if alert_if_down:
            notify_health_down(detail)
        return HealthResponse(
            status="down",
            env=APP_ENV,
            store_ok=False,
            openai_configured=openai_configured,
            detail=detail,
        )

    status = "ok"
    detail = "Ready to run reviews."
    if not openai_configured:
        status = "degraded"
        detail = "OpenAI key not set — observations use evidence templates."

    return HealthResponse(
        status=status,  # type: ignore[arg-type]
        env=APP_ENV,
        store_ok=True,
        openai_configured=openai_configured,
        detail=detail,
    )


def trigger_down_alert(reason: str = "Manual / probe: service reported unavailable") -> str:
    """Ops action: force an alert (email if SMTP set, always write notifications.log)."""
    return notify_health_down(reason)
