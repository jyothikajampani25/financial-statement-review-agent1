from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DISCLAIMER
from src.models import FeedbackRequest, HealthResponse, ReviewPack, ReviewRequest
from src.services.health import check_health, trigger_down_alert
from src.services.review import (
    apply_feedback,
    build_review_pack,
    list_recent_runs,
    load_pack,
    run_review,
)
from src.store import available_years, list_companies, parse_csv_bytes, save_upload

app = FastAPI(
    title="Financial Statement Review Agent",
    version="1.2",
    description="Rules for numbers · upload pipeline · health alerts · API-first",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(alert: bool = False) -> HealthResponse:
    return check_health(alert_if_down=alert)


@app.post("/alerts/health-down")
def alert_health_down(reason: str = "Health probe failed / service unreachable") -> dict:
    """Ops: fire downtime alert (log always; email if SMTP configured)."""
    result = trigger_down_alert(reason)
    return {"ok": True, "result": result, "reason": reason}


@app.get("/companies")
def companies() -> dict:
    data = list_companies()
    return {
        cid: {**meta, "years": available_years(cid)}
        for cid, meta in data.items()
    }


@app.post("/reviews", response_model=ReviewPack)
def create_review(body: ReviewRequest) -> ReviewPack:
    try:
        return run_review(body)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/reviews/upload", response_model=ReviewPack)
async def create_review_upload(
    current_csv: UploadFile = File(..., description="Current year statement CSV"),
    prior_csv: UploadFile = File(..., description="Prior year statement CSV"),
    company_name: str = Form("Uploaded Co"),
    current_year: int = Form(2023),
    prior_year: int = Form(2022),
    supporting_pdf: UploadFile | None = File(None),
) -> ReviewPack:
    """Realtime upload path: store files → parse → review pack."""
    if prior_year >= current_year:
        raise HTTPException(status_code=400, detail="prior_year must be < current_year")
    try:
        cur_bytes = await current_csv.read()
        pri_bytes = await prior_csv.read()
        save_upload(current_csv.filename or "current.csv", cur_bytes, kind="csv")
        save_upload(prior_csv.filename or "prior.csv", pri_bytes, kind="csv")
        if supporting_pdf is not None:
            save_upload(
                supporting_pdf.filename or "statement.pdf",
                await supporting_pdf.read(),
                kind="doc",
            )
        cid = "upload_" + company_name.lower().replace(" ", "_")[:24]
        current = parse_csv_bytes(
            cur_bytes, company_id=cid, company_name=company_name, year=current_year
        )
        prior = parse_csv_bytes(
            pri_bytes, company_id=cid, company_name=company_name, year=prior_year
        )
        return build_review_pack(current, prior, requested_by="api-upload")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/reviews/{run_id}", response_model=ReviewPack)
def get_review(run_id: str) -> ReviewPack:
    pack = load_pack(run_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="run not found")
    return pack


@app.get("/reviews")
def recent_reviews(limit: int = 20) -> list[dict]:
    return list_recent_runs(limit=limit)


@app.post("/feedback")
def feedback(body: FeedbackRequest) -> dict:
    obs = apply_feedback(body.observation_id, body.useful)
    if obs is None:
        raise HTTPException(status_code=404, detail="observation not found")
    return {
        "observation_id": obs.id,
        "useful_votes": obs.useful_votes,
        "not_useful_votes": obs.not_useful_votes,
    }


@app.get("/")
def root() -> dict:
    return {
        "service": "financial-statement-review-agent",
        "disclaimer": DISCLAIMER,
        "docs": "/docs",
        "health": "/health",
        "upload": "POST /reviews/upload",
        "alert": "POST /alerts/health-down",
    }
