from __future__ import annotations

from src.config import EPSILON, IDENTITY_LEFT, IDENTITY_RIGHT, MATH_RULES
from src.models import Evidence, Finding, LineItem, StatementBundle
from src.store import lines_by_code


def _ev(line: LineItem, year: int) -> Evidence:
    return Evidence(
        line_code=line.code,
        line_name=line.name,
        year=year,
        amount=line.amount,
    )


def validate_math(bundle: StatementBundle) -> list[Finding]:
    """Rule engine: parent totals must equal sum of children."""
    by_code = lines_by_code(bundle)
    findings: list[Finding] = []

    for parent, children in MATH_RULES.items():
        if parent not in by_code or any(c not in by_code for c in children):
            continue

        expected = sum(by_code[c].amount for c in children)
        actual = by_code[parent].amount
        ok = abs(expected - actual) <= EPSILON
        evidence = [_ev(by_code[c], bundle.year) for c in children] + [
            _ev(by_code[parent], bundle.year)
        ]
        findings.append(
            Finding(
                check_id=f"MATH-{parent}",
                status="pass" if ok else "fail",
                message=(
                    f"{by_code[parent].name} adds correctly."
                    if ok
                    else f"{by_code[parent].name} does not equal sum of components."
                ),
                expected=round(expected, 2),
                actual=round(actual, 2),
                evidence=evidence,
            )
        )
    return findings


def validate_consistency(bundle: StatementBundle) -> list[Finding]:
    """Balance Sheet identity: Assets = Liabilities + Equity."""
    by_code = lines_by_code(bundle)
    if IDENTITY_LEFT not in by_code or any(c not in by_code for c in IDENTITY_RIGHT):
        return []

    left = by_code[IDENTITY_LEFT]
    right_sum = sum(by_code[c].amount for c in IDENTITY_RIGHT)
    diff = left.amount - right_sum
    ok = abs(diff) <= EPSILON
    evidence = [_ev(left, bundle.year)] + [
        _ev(by_code[c], bundle.year) for c in IDENTITY_RIGHT
    ]
    return [
        Finding(
            check_id="CONS-01",
            status="pass" if ok else "fail",
            message=(
                "Balance Sheet identity holds: Assets = Liabilities + Equity."
                if ok
                else "Balance Sheet does not balance: Assets ≠ Liabilities + Equity."
            ),
            expected=0.0,
            actual=round(diff, 2),
            evidence=evidence,
        )
    ]


def validate_all(bundle: StatementBundle) -> list[Finding]:
    return validate_math(bundle) + validate_consistency(bundle)
