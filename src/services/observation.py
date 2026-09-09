from __future__ import annotations

import json
import uuid
from typing import Iterable

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.models import Finding, Observation


def _severity(finding: Finding) -> str:
    if finding.status == "fail":
        return "critical" if finding.check_id.startswith("CONS") or finding.check_id.startswith("MATH") else "warning"
    if finding.status == "material":
        return "warning"
    return "info"


def _template_text(finding: Finding) -> str:
    bits = [finding.message]
    if finding.expected is not None and finding.actual is not None and finding.status == "fail":
        bits.append(f"Expected {finding.expected:,.2f}; actual {finding.actual:,.2f}.")
    if finding.evidence:
        ev = "; ".join(
            f"{e.line_name} {e.year}={e.amount:,.0f}" for e in finding.evidence[:4]
        )
        bits.append(f"Evidence: {ev}.")
    return " ".join(bits)


def _llm_text(finding: Finding) -> str | None:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        payload = {
            "check_id": finding.check_id,
            "status": finding.status,
            "message": finding.message,
            "expected": finding.expected,
            "actual": finding.actual,
            "evidence": [e.model_dump() for e in finding.evidence],
        }
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write short financial statement review observations. "
                        "Use ONLY numbers in the JSON. Never invent amounts. "
                        "One or two sentences. No audit opinion language."
                    ),
                },
                {"role": "user", "content": json.dumps(payload)},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None


def write_observations(findings: Iterable[Finding]) -> list[Observation]:
    """GenAI or templates — amounts must come from findings only."""
    out: list[Observation] = []
    for finding in findings:
        if finding.status == "pass":
            continue
        text = _llm_text(finding) or _template_text(finding)
        out.append(
            Observation(
                id=f"obs-{uuid.uuid4().hex[:10]}",
                text=text,
                severity=_severity(finding),  # type: ignore[arg-type]
                evidence_refs=[finding.check_id],
            )
        )
    return out
