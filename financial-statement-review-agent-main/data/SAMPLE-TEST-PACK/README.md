# Sample test pack — INPUT vs OUTPUT

## Important (read this first)

**This project does NOT upload PDF statements for AI to “read P&L”.**

| | What we do |
|---|---|
| **Input** | Structured Balance Sheet + Profit & Loss **numbers** (CSV) for **2 years** |
| **Process** | **Rules** check math + consistency + YoY; **AI/templates** only write comments from those results |
| **Output** | Review pack: pass/fail findings, variances, observations with evidence, run/trace ids |

Uploading a PDF and asking AI to invent P&L would be unsafe (hallucinated totals).  
Our design: **numbers first (rules) → wording second (AI)**.

**Two years is correct** for v1: current year + prior year (YoY compare). That matches the BRD.

---

## Folder layout

```
SAMPLE-TEST-PACK/
  input/                 ← what you feed the agent
  output-examples/       ← what you get back (JSON review packs)
  README.md              ← this file
```

App also loads the same CSVs from `data/sample/` (used by UI dropdown).

---

## INPUT (test files)

Each company needs **two CSV files** (one per year):

| File | Meaning |
|------|---------|
| `acme_good_2022.csv` | Clean company — prior year |
| `acme_good_2023.csv` | Clean company — current year (math OK) |
| `acme_broken_2022.csv` | Broken company — prior year |
| `acme_broken_2023.csv` | Broken company — current year (**math + BS identity broken**) |
| `companies.json` | Company ids shown in the UI |

### CSV columns (required)

```text
code,name,statement,amount
```

- `code` — standard line id (e.g. `REVENUE`, `TOTAL_ASSETS`)
- `name` — display name
- `statement` — `BS` (Balance Sheet) or `PL` (Profit & Loss)
- `amount` — number (expenses often negative)

**Example (P&L lines):**

```csv
REVENUE,Revenue,PL,140000
COGS,Cost of goods sold,PL,-80000
GROSS_PROFIT,Gross profit,PL,60000
NET_INCOME,Net income,PL,27000
```

So: **input is already the Balance Sheet + P&L figures**, not a PDF.

---

## OUTPUT (what the agent returns)

See `output-examples/`:

| File | Shows |
|------|--------|
| `OUTPUT-clean-review-pack.json` | All math/identity pass; material YoY notes |
| `OUTPUT-broken-review-pack.json` | MATH fail + CONS-01 fail + observations |

### Output contains

1. **summary** — passed / failed / material YoY counts  
2. **findings** — each check (`MATH-*`, `CONS-01`, `YOY-*`) with expected/actual + evidence lines  
3. **variances** — year-on-year changes  
4. **observations** — short review comments (templates or GenAI) citing check ids  
5. **run_id / trace_id** — audit trail  

**UI** shows the same pack as tabs. **API** `POST /reviews` returns the same JSON.

---

## How to test in the UI

1. Sidebar → **Acme Demo Co (clean)** → Run → expect Failed = 0  
2. Sidebar → **Acme Demo Co (broken)** → Run → expect Failed ≥ 2 (red findings)  
3. Open **Observations** + **YoY variances**

Years: keep **2023** (current) and **2022** (prior). That is the intended demo.

---

## Future (not in this demo)

PDF / Excel upload → extract tables → map to same CSV codes → same review engine.  
Same output. We skipped PDF OCR so the hackathon demo stays accurate and evidence-safe.
