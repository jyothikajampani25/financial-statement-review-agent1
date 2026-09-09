from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DISCLAIMER, RUNTIME_DIR, SAMPLE_DIR
from src.models import ReviewRequest
from src.services.health import check_health, trigger_down_alert
from src.services.review import apply_feedback, build_review_pack, run_review
from src.store import (
    available_years,
    list_companies,
    list_recent_uploads,
    notification_log_tail,
    parse_csv_bytes,
    save_upload,
)

st.set_page_config(page_title="FS Review Agent", page_icon="📊", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(180deg, #eef6f6 0%, #f7fafa 40%, #ffffff 100%); }
      h1, h2, h3 { color: #0f4c5c !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Financial Statement Review Agent")
st.caption(DISCLAIMER)

health = check_health()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Health", health.status.upper())
c2.metric("Env", health.env)
c3.metric("Store", "OK" if health.store_ok else "DOWN")
c4.metric("GenAI", "on" if health.openai_configured else "templates")
if health.status == "down":
    st.error(health.detail)
elif health.status == "degraded":
    st.warning(health.detail)
else:
    st.success(health.detail)

main_tab, upload_tab, ops_tab = st.tabs(
    ["1) Sample review", "2) Upload & process (realtime)", "3) Ops · storage · alerts"]
)


def render_pack(pack) -> None:
    st.subheader("Review pack (output)")
    a, b, c, d = st.columns(4)
    a.metric("Passed", pack.summary.passed)
    b.metric("Failed", pack.summary.failed)
    c.metric("Material YoY", pack.summary.material_variances)
    d.metric("Observations", len(pack.observations))
    st.caption(f"run `{pack.run_id}` · trace `{pack.trace_id}` · {pack.company_name}")

    tab_f, tab_v, tab_o, tab_n = st.tabs(
        ["Findings", "YoY variances", "Observations", "Notifications"]
    )
    with tab_f:
        for f in pack.findings:
            if f.status == "pass":
                st.success(f"**{f.check_id}** · {f.message}")
            elif f.status == "fail":
                st.error(
                    f"**{f.check_id}** · {f.message}  \n"
                    f"expected `{f.expected}` · actual `{f.actual}`"
                )
            else:
                st.warning(f"**{f.check_id}** · {f.message}")
    with tab_v:
        material = [v for v in pack.variances if v.material]
        if not material:
            st.write("No material variances above threshold.")
        for v in material:
            pct = "n/a" if v.pct_change is None else f"{v.pct_change * 100:.1f}%"
            st.write(
                f"**{v.line_name}** (`{v.line_code}`) · {pct} · "
                f"{v.prior:,.0f} → {v.current:,.0f}"
            )
    with tab_o:
        if not pack.observations:
            st.write("No observations.")
        for obs in pack.observations:
            st.markdown(f"**[{obs.severity}]** {obs.text}")
            st.caption("refs: " + ", ".join(obs.evidence_refs))
            b1, b2, _ = st.columns([1, 1, 4])
            if b1.button("Useful", key=f"up-{pack.run_id}-{obs.id}"):
                apply_feedback(obs.id, True)
                st.toast("Feedback recorded")
            if b2.button("Not useful", key=f"dn-{pack.run_id}-{obs.id}"):
                apply_feedback(obs.id, False)
                st.toast("Feedback recorded")
    with tab_n:
        for n in pack.notifications_sent or ["(none)"]:
            st.code(n)
        st.caption(f"Log file: `{RUNTIME_DIR / 'notifications.log'}`")


# ----- Tab 1: sample -----
with main_tab:
    st.info(
        "Sample packs are for quick demo. For a real run, use tab **Upload & process**."
    )
    companies = list_companies()
    company_ids = list(companies.keys())
    with st.sidebar:
        st.header("Sample pack")
        company_id = st.selectbox(
            "Company pack",
            company_ids,
            format_func=lambda c: f"{companies[c]['name']} ({c})",
        )
        years = available_years(company_id)
        current_year = st.selectbox("Current year", list(reversed(years)), index=0)
        prior_choices = [y for y in years if y < current_year] or [
            y for y in years if y != current_year
        ]
        prior_year = st.selectbox("Prior year", prior_choices, index=0)
        requested_by = st.text_input("Requested by", value="reviewer")
        run_btn = st.button("Run sample review", type="primary", use_container_width=True)
        st.markdown("---")
        st.markdown("**API**")
        st.code("POST /reviews\nPOST /reviews/upload\nGET /health\nPOST /alerts/health-down")

    if run_btn:
        with st.status("Realtime pipeline", expanded=True) as status:
            st.write("Load statement CSVs from store…")
            st.write("Validate math + Balance Sheet identity…")
            st.write("Compare YoY…")
            st.write("Write observations + notify…")
            pack = run_review(
                ReviewRequest(
                    company_id=company_id,
                    current_year=int(current_year),
                    prior_year=int(prior_year),
                    requested_by=requested_by,
                )
            )
            status.update(label="Review complete", state="complete")
        st.session_state["pack"] = pack

    if st.session_state.get("pack"):
        render_pack(st.session_state["pack"])
    else:
        st.write("Run a **sample** review, or switch to **Upload & process**.")


# ----- Tab 2: upload -----
with upload_tab:
    st.subheader("Upload statements and review (realtime)")
    st.markdown(
        """
**What to upload:** two CSV files (current year + prior year) with columns  
`code,name,statement,amount` — same format as sample test pack.

**About PDFs:** v1 does **not** OCR PDFs into numbers (that invents totals).  
You may still attach a PDF/statement scan for **audit storage**; the engine reviews the CSV figures.
"""
    )
    col_a, col_b = st.columns(2)
    with col_a:
        company_name = st.text_input("Company name", value="Uploaded Co")
        cur_year = st.number_input("Current year", min_value=2000, max_value=2100, value=2023)
        prior_y = st.number_input("Prior year", min_value=2000, max_value=2100, value=2022)
    with col_b:
        cur_file = st.file_uploader("Current year CSV (required)", type=["csv"], key="cur_csv")
        pri_file = st.file_uploader("Prior year CSV (required)", type=["csv"], key="pri_csv")
        pdf_file = st.file_uploader(
            "Optional supporting PDF (stored only)", type=["pdf"], key="pdf"
        )

    if st.button("Upload · store · run review", type="primary"):
        if not cur_file or not pri_file:
            st.error("Upload both current and prior CSV files.")
        elif int(prior_y) >= int(cur_year):
            st.error("Prior year must be earlier than current year.")
        else:
            try:
                with st.status("Realtime processing", expanded=True) as status:
                    st.write("1. Save uploads to `data/runtime/uploads/` …")
                    cur_bytes = cur_file.getvalue()
                    pri_bytes = pri_file.getvalue()
                    cur_path = save_upload(cur_file.name, cur_bytes, kind="csv")
                    pri_path = save_upload(pri_file.name, pri_bytes, kind="csv")
                    st.write(f"Saved `{cur_path.name}` and `{pri_path.name}`")

                    pdf_path = None
                    if pdf_file is not None:
                        st.write("2. Store supporting PDF under `data/runtime/documents/` …")
                        pdf_path = save_upload(pdf_file.name, pdf_file.getvalue(), kind="doc")
                        st.write(f"Stored document `{pdf_path.name}` (not OCR’d)")

                    st.write("3. Parse CSV → statement lines…")
                    cid = "upload_" + company_name.lower().replace(" ", "_")[:24]
                    current = parse_csv_bytes(
                        cur_bytes,
                        company_id=cid,
                        company_name=company_name,
                        year=int(cur_year),
                    )
                    prior = parse_csv_bytes(
                        pri_bytes,
                        company_id=cid,
                        company_name=company_name,
                        year=int(prior_y),
                    )
                    st.write(
                        f"Parsed {len(current.lines)} current lines · {len(prior.lines)} prior lines"
                    )

                    st.write("4. Rules: math → consistency → YoY…")
                    st.write("5. Observations + notifications + audit pack…")
                    pack = build_review_pack(current, prior, requested_by="uploader")
                    status.update(label="Pipeline finished", state="complete")

                st.session_state["pack"] = pack
                st.success(
                    f"Processed. Audit pack: `data/runtime/runs/{pack.run_id}.json`"
                    + (f" · PDF stored: `{pdf_path.name}`" if pdf_path else "")
                )
                render_pack(pack)
            except Exception as exc:
                st.error(f"Upload/process failed: {exc}")

    st.markdown("**Quick test:** upload files from `data/SAMPLE-TEST-PACK/input/`")
    st.code(
        "acme_broken_2023.csv  → current\nacme_broken_2022.csv  → prior",
        language="text",
    )


# ----- Tab 3: ops -----
with ops_tab:
    st.subheader("Where things are stored")
    st.markdown(
        f"""
| What | Location |
|------|----------|
| Sample statement CSVs | `{SAMPLE_DIR}` |
| Your uploads (CSV) | `{RUNTIME_DIR / 'uploads'}` |
| Supporting PDFs (audit only) | `{RUNTIME_DIR / 'documents'}` |
| Review packs (JSON audit) | `{RUNTIME_DIR / 'runs'}` |
| Alerts / notify log | `{RUNTIME_DIR / 'notifications.log'}` |
| Feedback votes | `{RUNTIME_DIR / 'feedback.jsonl'}` |
"""
    )
    st.subheader("How we process (realtime)")
    st.code(
        "Upload/store → Parse lines → Validate math+identity → YoY → "
        "Observations → Notify (log/email/webhook) → Save run JSON",
        language="text",
    )
    st.subheader("If the service is down — alerts")
    st.write(
        "Health probe: `GET /health`. If store is missing → status `down`. "
        "Ops can trigger an alert anytime (writes `notifications.log`; emails if SMTP configured)."
    )
    reason = st.text_input(
        "Alert reason",
        value="Demo: review service unreachable / health probe failed",
    )
    if st.button("Trigger health-down alert now", type="primary"):
        msg = trigger_down_alert(reason)
        st.success(f"Alert fired → {msg}")

    st.subheader("Live notification log (tail)")
    log_lines = notification_log_tail(40)
    if log_lines:
        st.code("\n".join(log_lines))
    else:
        st.write("Log empty — run a review or trigger an alert.")

    st.subheader("Recent uploads")
    ups = list_recent_uploads()
    if ups:
        st.dataframe(ups, use_container_width=True)
    else:
        st.write("No uploads yet.")
