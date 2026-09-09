from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SAMPLE_DIR = DATA_DIR / "sample"
RUNTIME_DIR = DATA_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

APP_ENV = os.getenv("APP_ENV", "local")
YOY_PCT_THRESHOLD = float(os.getenv("YOY_PCT_THRESHOLD", "0.20"))
YOY_ABS_FLOOR = float(os.getenv("YOY_ABS_FLOOR", "1000"))
EPSILON = float(os.getenv("EPSILON", "0.01"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "fs-review-agent@localhost")
NOTIFY_WEBHOOK_URL = os.getenv("NOTIFY_WEBHOOK_URL", "").strip()

DISCLAIMER = (
    "Assistive review tool. Not a statutory audit opinion. "
    "Numbers come from statement rules; commentary cites that evidence only."
)

# Parent line = sum of children (COGS/OPEX/INTEREST/TAX stored as negatives)
MATH_RULES: dict[str, list[str]] = {
    "TOTAL_CA": ["CASH", "AR", "INVENTORY"],
    "TOTAL_ASSETS": ["TOTAL_CA", "FA"],
    "TOTAL_CL": ["AP", "ST_DEBT"],
    "TOTAL_LIAB": ["TOTAL_CL", "LT_DEBT"],
    "GROSS_PROFIT": ["REVENUE", "COGS"],
    "OPERATING_INCOME": ["GROSS_PROFIT", "OPEX"],
    "NET_INCOME": ["OPERATING_INCOME", "INTEREST", "TAX"],
}

IDENTITY_LEFT = "TOTAL_ASSETS"
IDENTITY_RIGHT = ["TOTAL_LIAB", "EQUITY"]
