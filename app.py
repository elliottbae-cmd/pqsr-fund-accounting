"""PQSR Fund I — Accounting Automation App"""

import streamlit as st
from database.db import init_db, get_posted_periods, get_next_expected_month

# Initialize database on app load
init_db()

st.set_page_config(
    page_title="PQSR Fund I | Accounting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("PQSR Fund I, LLC")
st.subheader("Accounting & Investor Reporting")

# Override sidebar label (Streamlit uses filename by default)
st.sidebar.markdown("# Accounting")

st.markdown("---")

# Show current status
posted = get_posted_periods()
next_month = get_next_expected_month()

col1, col2 = st.columns(2)
with col1:
    st.metric("Periods Posted", len(posted))
with col2:
    st.metric("Next Period", next_month.strftime("%B %Y"))

st.markdown("---")

st.markdown("""
### Welcome

This app automates the monthly accounting and quarterly investor reporting for PQSR Fund I.

**Workflow:**

1. **Upload Bank Data** — Upload your monthly bank export (CSV or Excel)
2. **Review Journal Entries** — Confirm auto-classified transactions and post to the ledger
3. **Financial Statements** — View the rolled-forward Balance Sheet, Income Statement, and cash flow metrics
4. **Generate Reports** — Download the quarterly investor PDF and updated Excel workbook
5. **Financial History** — Browse all posted periods with full workbook-style views

**Status:** {} period(s) posted through {}. Next up: **{}**.

**Baseline:** Financials are anchored to the 12/31/2025 year-end workbook.
Monthly bank uploads roll forward from there.
""".format(
    len(posted),
    posted[-1]["period_date"] if posted else "baseline (12/31/2025)",
    next_month.strftime("%B %Y"),
))

# Show recent posting history
if posted:
    st.markdown("##### Recent Activity")
    import pandas as pd
    from datetime import date
    recent = posted[-6:]  # Last 6 periods
    rows = []
    for p in reversed(recent):
        pd_obj = date.fromisoformat(p["period_date"])
        rows.append({
            "Period": pd_obj.strftime("%B %Y"),
            "Posted": p["posted_at"][:10],
            "Type": "Quarter End" if p["quarter_end"] else "Month End",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# Initialize session state
if "classified_transactions" not in st.session_state:
    st.session_state.classified_transactions = []
if "journal_entries" not in st.session_state:
    st.session_state.journal_entries = []
if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False
