# Financial Statement Review Agent

Hackathon Project 2 — GenAI / Financial Analytics.

**Rules own the numbers. GenAI only explains evidence. API-first so any environment can integrate.**

## Documents
| Doc | File |
|-----|------|
| BRD v1.1 | [docs/BRD-Financial-Statement-Review-Agent.pdf](docs/BRD-Financial-Statement-Review-Agent.pdf) |
| HLD v1.1 | [docs/HLD-Financial-Statement-Review-Agent.pdf](docs/HLD-Financial-Statement-Review-Agent.pdf) |
| Diagrams · algorithms · platform | [docs/Phase2-Diagrams-Algorithms-Pseudocode.pdf](docs/Phase2-Diagrams-Algorithms-Pseudocode.pdf) |
| Demo script (2–3 min) | [docs/DEMO-SCRIPT.pdf](docs/DEMO-SCRIPT.pdf) |
| Use case explained (simple) | [docs/USE-CASE-EXPLAINED.pdf](docs/USE-CASE-EXPLAINED.pdf) |
| Tech · services · prod | [docs/TECH-SERVICES-AND-PROD.pdf](docs/TECH-SERVICES-AND-PROD.pdf) |
| Roadmap · estimation | [docs/ROADMAP-AND-ESTIMATION.pdf](docs/ROADMAP-AND-ESTIMATION.pdf) |
| Input vs output | [docs/INPUT-OUTPUT-EXPLAINED.pdf](docs/INPUT-OUTPUT-EXPLAINED.pdf) |

## What it does
- Validates Balance Sheet / P&L math totals
- Checks Assets = Liabilities + Equity
- Flags material year-on-year variances
- Writes review observations with evidence (templates, or OpenAI if keyed)
- Upload realtime path (2 CSVs + optional PDF store)
- Notifies on complete / critical fail; health-down alert for ops
- Same review pack via REST — UI is one client, not the only door

## Quick start

```bash
cd financial-statement-review-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python -m src.ingest
pytest -q

# UI
streamlit run ui/app.py

# API (another terminal)
uvicorn api.main:app --reload --port 8000
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a **GitHub** repo (root = this project).
2. Go to [https://share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Repo = yours · Branch = `main` · **Main file path = `ui/app.py`**.
4. Deploy. Optional **Secrets**:
   ```
   OPENAI_API_KEY = "sk-..."
   ```
5. Public URL looks like `https://<you>-<app>.streamlit.app`

App works **without** OpenAI (templates). Add the secret only if you want GenAI wording.

## Demo path (for judges)
1. Tab **Sample review** → **Acme Demo Co (broken)** → Run  
2. Or tab **Upload & process** → upload `data/SAMPLE-TEST-PACK/input/acme_broken_2023.csv` + `_2022.csv`  
3. Show MATH + CONS fails · YoY · Observations · Ops alert log  
4. Practice with [docs/DEMO-SCRIPT.pdf](docs/DEMO-SCRIPT.pdf)

## Architecture (MVC + services)

| Layer | Path |
|-------|------|
| View | `ui/app.py` |
| Controller | `api/main.py` |
| Services | `src/services/` validation · yoy · observation · notify · review · health |
| Model / store | `src/models.py` · `src/store.py` · `data/sample/` |
| Config / envs | `src/config.py` · `.env` |
| Audit / notify log | `data/runtime/` (gitignored; created at runtime) |
| CI | `.github/workflows/ci.yml` |

## Integration surface
```
POST /reviews              → run review, return pack
POST /reviews/upload       → upload CSVs (+ optional PDF)
GET  /reviews/{run_id}     → fetch pack by id
GET  /health               → ops probe
POST /alerts/health-down   → fire downtime alert
POST /feedback             → observation useful / not useful
```

## Disclaimer
Assistive review tool. Not a statutory audit opinion.
