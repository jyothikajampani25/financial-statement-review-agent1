from __future__ import annotations

from src.models import ReviewRequest
from src.services.health import check_health
from src.services.review import apply_feedback, run_review
from src.services.validation import validate_all
from src.services.yoy import compare_yoy
from src.store import load_statement


def test_good_pack_math_and_identity_pass():
    bundle = load_statement("acme_good", 2023)
    findings = validate_all(bundle)
    assert findings
    assert all(f.status == "pass" for f in findings if f.check_id.startswith("MATH"))
    cons = next(f for f in findings if f.check_id == "CONS-01")
    assert cons.status == "pass"


def test_broken_pack_detects_math_and_identity():
    bundle = load_statement("acme_broken", 2023)
    findings = validate_all(bundle)
    math_assets = next(f for f in findings if f.check_id == "MATH-TOTAL_ASSETS")
    cons = next(f for f in findings if f.check_id == "CONS-01")
    assert math_assets.status == "fail"
    assert math_assets.expected == 350000
    assert math_assets.actual == 351200
    assert cons.status == "fail"
    assert abs(cons.actual or 0) == 1200


def test_yoy_flags_revenue_material():
    cur = load_statement("acme_good", 2023)
    pri = load_statement("acme_good", 2022)
    variances, findings = compare_yoy(cur, pri)
    rev = next(v for v in variances if v.line_code == "REVENUE")
    assert rev.material
    assert rev.prior == 100000
    assert rev.current == 140000
    assert any(f.check_id == "YOY-REVENUE" for f in findings)


def test_run_review_pack_has_trace_and_evidence_observations():
    pack = run_review(
        ReviewRequest(company_id="acme_broken", current_year=2023, prior_year=2022)
    )
    assert pack.run_id.startswith("run-")
    assert pack.trace_id.startswith("trc-")
    assert pack.summary.failed >= 2
    assert pack.observations
    for obs in pack.observations:
        assert obs.evidence_refs
        assert obs.text


def test_feedback_and_health():
    pack = run_review(
        ReviewRequest(company_id="acme_good", current_year=2023, prior_year=2022)
    )
    assert pack.observations  # material YoY at least
    obs = pack.observations[0]
    updated = apply_feedback(obs.id, True)
    assert updated is not None
    assert updated.useful_votes >= 1

    health = check_health()
    assert health.store_ok is True
    assert health.status in {"ok", "degraded"}
