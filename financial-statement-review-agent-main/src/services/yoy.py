from __future__ import annotations

from src.config import YOY_ABS_FLOOR, YOY_PCT_THRESHOLD
from src.models import Evidence, Finding, StatementBundle, Variance
from src.store import lines_by_code

# Headline lines get observations; full variance list still returned for analysis.
HEADLINE_CODES = {
    "REVENUE",
    "GROSS_PROFIT",
    "OPERATING_INCOME",
    "NET_INCOME",
    "TOTAL_ASSETS",
    "TOTAL_LIAB",
    "EQUITY",
}


def compare_yoy(
    current: StatementBundle,
    prior: StatementBundle,
    *,
    pct_threshold: float | None = None,
    abs_floor: float | None = None,
) -> tuple[list[Variance], list[Finding]]:
    """Year-on-year compare; material rows become findings for observations."""
    pct_threshold = YOY_PCT_THRESHOLD if pct_threshold is None else pct_threshold
    abs_floor = YOY_ABS_FLOOR if abs_floor is None else abs_floor

    cur = lines_by_code(current)
    pri = lines_by_code(prior)
    variances: list[Variance] = []
    findings: list[Finding] = []

    for code in sorted(set(cur) & set(pri)):
        c_line, p_line = cur[code], pri[code]
        abs_chg = c_line.amount - p_line.amount
        if abs(p_line.amount) <= 1e-9:
            pct = None
            material = abs(abs_chg) >= abs_floor
        else:
            pct = abs_chg / abs(p_line.amount)
            material = abs(pct) >= pct_threshold or abs(abs_chg) >= abs_floor

        variances.append(
            Variance(
                line_code=code,
                line_name=c_line.name,
                prior=p_line.amount,
                current=c_line.amount,
                abs_change=round(abs_chg, 2),
                pct_change=None if pct is None else round(pct, 4),
                material=material,
            )
        )

        if not material or code not in HEADLINE_CODES:
            continue

        pct_txt = "n/a" if pct is None else f"{pct * 100:.1f}%"
        findings.append(
            Finding(
                check_id=f"YOY-{code}",
                status="material",
                message=(
                    f"{c_line.name} moved {pct_txt} YoY "
                    f"({p_line.amount:,.0f} → {c_line.amount:,.0f})."
                ),
                expected=p_line.amount,
                actual=c_line.amount,
                evidence=[
                    Evidence(
                        line_code=code,
                        line_name=p_line.name,
                        year=prior.year,
                        amount=p_line.amount,
                    ),
                    Evidence(
                        line_code=code,
                        line_name=c_line.name,
                        year=current.year,
                        amount=c_line.amount,
                    ),
                ],
            )
        )

    return variances, findings
