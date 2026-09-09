# Demo script (2–3 min)

**Pack:** Acme Demo Co (**broken**) · 2023 vs 2022

## Say + click

| Time | Say | Click |
|------|-----|-------|
| 0:00 | Manual FS review is slow; we built a review agent — rules for numbers, GenAI for wording with evidence, API for any system. | UI open |
| 0:25 | Rules own totals & BS identity. GenAI never invents amounts. UI is one client. | Point at Integration |
| 0:45 | On broken data we catch math fail and BS not balancing, with expected vs actual. | **broken** → Run → Findings (red) |
| 1:10 | Revenue +40% YoY is material; observations cite check ids; feedback improves quality. | YoY → Observations → Useful |
| 1:40 | Trace id, notify on critical, `/health` for ops, queue-ready under load. | Notifications or `/docs` |
| 2:00 | BRD→HLD→MVC→tests. Assistive tool, not an audit opinion. | Stop |

## Backup answers
- **DEGRADED** = no OpenAI key (templates OK)
- **Not an audit** = assistive only
- **Pure LLM?** = no — numbers must be rule-checked
