from __future__ import annotations

import json
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib import request

from src.config import (
    NOTIFY_EMAIL_TO,
    NOTIFY_WEBHOOK_URL,
    RUNTIME_DIR,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from src.models import ReviewPack


def _log_path() -> Path:
    return RUNTIME_DIR / "notifications.log"


def _append_log(channel: str, subject: str, body: str) -> str:
    stamp = datetime.now(timezone.utc).isoformat()
    line = f"{stamp}\t{channel}\t{subject}\t{body.replace(chr(10), ' ')[:500]}\n"
    _log_path().parent.mkdir(parents=True, exist_ok=True)
    with _log_path().open("a", encoding="utf-8") as fh:
        fh.write(line)
    return f"{channel}:logged"


def _send_email(subject: str, body: str) -> str | None:
    if not NOTIFY_EMAIL_TO:
        return None
    if not SMTP_HOST:
        return _append_log("email-console", subject, body)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = NOTIFY_EMAIL_TO
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)
    return _append_log("email-smtp", subject, body)


def _send_webhook(payload: dict) -> str | None:
    if not NOTIFY_WEBHOOK_URL:
        return None
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        NOTIFY_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            _append_log("webhook", f"HTTP {resp.status}", json.dumps(payload)[:300])
            return f"webhook:{resp.status}"
    except Exception as exc:
        return _append_log("webhook-error", type(exc).__name__, str(exc))


def notify_review_events(pack: ReviewPack) -> list[str]:
    """Notify on complete + critical fails. Always leaves a local audit log."""
    sent: list[str] = []
    fails = [f for f in pack.findings if f.status == "fail"]
    subject_done = (
        f"[FS Review] complete · {pack.company_name} · {pack.current_year} · {pack.run_id}"
    )
    body_done = (
        f"trace={pack.trace_id}\n"
        f"passed={pack.summary.passed} failed={pack.summary.failed} "
        f"material={pack.summary.material_variances}\n"
    )
    sent.append(_append_log("review-complete", subject_done, body_done))
    mail = _send_email(subject_done, body_done)
    if mail:
        sent.append(mail)
    hook = _send_webhook(
        {
            "event": "review.completed",
            "run_id": pack.run_id,
            "trace_id": pack.trace_id,
            "company_id": pack.company_id,
            "summary": pack.summary.model_dump(),
        }
    )
    if hook:
        sent.append(hook)

    for finding in fails:
        subject = (
            f"[FS Review] CRITICAL {finding.check_id} · {pack.company_name} · {pack.run_id}"
        )
        body = (
            f"trace={pack.trace_id}\n"
            f"check={finding.check_id}\n"
            f"{finding.message}\n"
            f"expected={finding.expected} actual={finding.actual}\n"
        )
        sent.append(_append_log("critical", subject, body))
        mail = _send_email(subject, body)
        if mail:
            sent.append(mail)
        hook = _send_webhook(
            {
                "event": "review.critical",
                "run_id": pack.run_id,
                "trace_id": pack.trace_id,
                "check_id": finding.check_id,
                "message": finding.message,
            }
        )
        if hook:
            sent.append(hook)

    return sent


def notify_health_down(detail: str) -> str:
    subject = "[FS Review] HEALTH DOWN"
    body = f"Review service unhealthy.\n{detail}\n"
    _append_log("health-down", subject, body)
    mail = _send_email(subject, body)
    return mail or "health-down:logged"
