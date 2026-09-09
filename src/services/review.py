from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config import RUNTIME_DIR
from src.models import Observation, ReviewPack, ReviewRequest, ReviewSummary, StatementBundle
from src.services.notify import notify_review_events
from src.services.observation import write_observations
from src.services.validation import validate_all
from src.services.yoy import compare_yoy
from src.store import load_statement


def _audit_dir() -> Path:
    path = RUNTIME_DIR / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _feedback_path() -> Path:
    return RUNTIME_DIR / "feedback.jsonl"


def save_pack(pack: ReviewPack) -> None:
    path = _audit_dir() / f"{pack.run_id}.json"
    path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")


def load_pack(run_id: str) -> ReviewPack | None:
    path = _audit_dir() / f"{run_id}.json"
    if not path.exists():
        return None
    return ReviewPack.model_validate_json(path.read_text(encoding="utf-8"))


def list_recent_runs(limit: int = 20) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(_audit_dir().glob("*.json"), reverse=True)[:limit]:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "run_id": data.get("run_id"),
                "company_id": data.get("company_id"),
                "company_name": data.get("company_name"),
                "current_year": data.get("current_year"),
                "summary": data.get("summary"),
            }
        )
    return rows


def apply_feedback(observation_id: str, useful: bool) -> Observation | None:
    for path in _audit_dir().glob("*.json"):
        pack = ReviewPack.model_validate_json(path.read_text(encoding="utf-8"))
        for obs in pack.observations:
            if obs.id != observation_id:
                continue
            if useful:
                obs.useful_votes += 1
            else:
                obs.not_useful_votes += 1
            with _feedback_path().open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "run_id": pack.run_id,
                            "observation_id": observation_id,
                            "useful": useful,
                        }
                    )
                    + "\n"
                )
            save_pack(pack)
            return obs
    return None


def build_review_pack(
    current: StatementBundle,
    prior: StatementBundle,
    *,
    requested_by: str = "reviewer",
) -> ReviewPack:
    """Realtime pipeline: validate → YoY → observations → notify → audit."""
    _ = requested_by
    findings = validate_all(current)
    variances, yoy_findings = compare_yoy(current, prior)
    findings.extend(yoy_findings)

    observations = write_observations(findings)
    summary = ReviewSummary(
        passed=sum(1 for f in findings if f.status == "pass"),
        failed=sum(1 for f in findings if f.status == "fail"),
        material_variances=sum(1 for v in variances if v.material),
    )

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    trace_id = f"trc-{uuid.uuid4().hex[:12]}"
    pack = ReviewPack(
        run_id=run_id,
        trace_id=trace_id,
        company_id=current.company_id,
        company_name=current.company_name,
        current_year=current.year,
        prior_year=prior.year,
        summary=summary,
        findings=findings,
        variances=variances,
        observations=observations,
    )
    pack.notifications_sent = notify_review_events(pack)
    save_pack(pack)
    return pack


def run_review(req: ReviewRequest) -> ReviewPack:
    current = load_statement(req.company_id, req.current_year)
    prior = load_statement(req.company_id, req.prior_year)
    return build_review_pack(current, prior, requested_by=req.requested_by)
