from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    code: str
    name: str
    amount: float
    statement: Literal["BS", "PL"]


class StatementBundle(BaseModel):
    company_id: str
    company_name: str
    year: int
    currency: str = "USD"
    lines: list[LineItem]


class Evidence(BaseModel):
    line_code: str
    line_name: str
    year: int
    amount: float


class Finding(BaseModel):
    check_id: str
    status: Literal["pass", "fail", "material"]
    message: str
    expected: float | None = None
    actual: float | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class Variance(BaseModel):
    line_code: str
    line_name: str
    prior: float
    current: float
    abs_change: float
    pct_change: float | None
    material: bool


class Observation(BaseModel):
    id: str
    text: str
    severity: Literal["info", "warning", "critical"]
    evidence_refs: list[str] = Field(default_factory=list)
    useful_votes: int = 0
    not_useful_votes: int = 0


class ReviewSummary(BaseModel):
    passed: int
    failed: int
    material_variances: int


class ReviewPack(BaseModel):
    run_id: str
    trace_id: str
    company_id: str
    company_name: str
    current_year: int
    prior_year: int
    summary: ReviewSummary
    findings: list[Finding]
    variances: list[Variance]
    observations: list[Observation]
    notifications_sent: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    company_id: str = "acme_good"
    current_year: int = 2023
    prior_year: int = 2022
    requested_by: str = "reviewer"


class FeedbackRequest(BaseModel):
    observation_id: str
    useful: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    env: str
    store_ok: bool
    openai_configured: bool
    detail: str = ""
