from __future__ import annotations

import csv
import io
import json
import re
import uuid
from pathlib import Path

from src.config import RUNTIME_DIR, SAMPLE_DIR
from src.models import LineItem, StatementBundle

UPLOAD_DIR = RUNTIME_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = RUNTIME_DIR / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def list_companies() -> dict[str, dict]:
    path = SAMPLE_DIR / "companies.json"
    return json.loads(path.read_text())


def _parse_csv_text(text: str) -> list[LineItem]:
    lines: list[LineItem] = []
    reader = csv.DictReader(io.StringIO(text))
    required = {"code", "name", "statement", "amount"}
    if not reader.fieldnames or not required.issubset({f.strip() for f in reader.fieldnames}):
        raise ValueError("CSV must have columns: code,name,statement,amount")
    for row in reader:
        stmt = row["statement"].strip().upper()
        if stmt not in {"BS", "PL"}:
            raise ValueError(f"statement must be BS or PL, got {stmt}")
        lines.append(
            LineItem(
                code=row["code"].strip(),
                name=row["name"].strip(),
                statement=stmt,  # type: ignore[arg-type]
                amount=float(row["amount"]),
            )
        )
    if not lines:
        raise ValueError("CSV has no data rows")
    return lines


def parse_csv_bytes(data: bytes, *, company_id: str, company_name: str, year: int) -> StatementBundle:
    text = data.decode("utf-8-sig")
    return StatementBundle(
        company_id=company_id,
        company_name=company_name,
        year=year,
        lines=_parse_csv_text(text),
    )


def load_statement(company_id: str, year: int) -> StatementBundle:
    companies = list_companies()
    if company_id not in companies:
        raise KeyError(f"Unknown company_id: {company_id}")

    csv_path = SAMPLE_DIR / f"{company_id}_{year}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No statement file: {csv_path.name}")

    return parse_csv_bytes(
        csv_path.read_bytes(),
        company_id=company_id,
        company_name=companies[company_id]["name"],
        year=year,
    )


def lines_by_code(bundle: StatementBundle) -> dict[str, LineItem]:
    return {line.code: line for line in bundle.lines}


def store_ok() -> bool:
    return (SAMPLE_DIR / "companies.json").exists() and any(SAMPLE_DIR.glob("*.csv"))


def available_years(company_id: str) -> list[int]:
    years: list[int] = []
    for path in SAMPLE_DIR.glob(f"{company_id}_*.csv"):
        try:
            years.append(int(path.stem.rsplit("_", 1)[-1]))
        except ValueError:
            continue
    return sorted(years)


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)[:80]


def save_upload(filename: str, data: bytes, *, kind: str = "csv") -> Path:
    """Persist uploaded file under data/runtime/uploads (audit trail)."""
    folder = UPLOAD_DIR if kind == "csv" else DOCS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    stamp = uuid.uuid4().hex[:8]
    path = folder / f"{stamp}_{_safe_name(filename)}"
    path.write_bytes(data)
    return path


def list_recent_uploads(limit: int = 15) -> list[dict]:
    rows: list[dict] = []
    for folder, kind in ((UPLOAD_DIR, "statement-csv"), (DOCS_DIR, "document")):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.is_file():
                rows.append(
                    {
                        "kind": kind,
                        "name": path.name,
                        "path": str(path),
                        "size": path.stat().st_size,
                    }
                )
    rows.sort(key=lambda r: Path(r["path"]).stat().st_mtime, reverse=True)
    return rows[:limit]


def notification_log_tail(n: int = 30) -> list[str]:
    path = RUNTIME_DIR / "notifications.log"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-n:]
