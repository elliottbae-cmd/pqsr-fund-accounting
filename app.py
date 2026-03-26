"""PQSR Fund I — Accounting Automation App"""

import streamlit as st

st.set_page_config(
    page_title="PQSR Fund I | Accounting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config.auth import check_password

# Password gate — must pass before anything else loads
if not check_password():
    st.stop()

from database.db import init_db, get_posted_periods, get_next_expected_month
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_divider

# Initialize database on app load
# NOTE: On Streamlit Community Cloud, the SQLite database is ephemeral —
# it resets on each redeployment. For production use, consider migrating
# to a cloud database (e.g., Supabase, PlanetScale) or exporting data
# via the Excel workbook before redeploying.
init_db()

# Inject professional styling and sidebar branding
inject_custom_css()
show_sidebar_branding()

styled_page_header("PQSR Fund I, LLC", "Accounting & Investor Reporting")

# Show current status
posted = get_posted_periods()
next_month = get_next_expected_month()

col1, col2 = st.columns(2)
with col1:
    st.metric("Periods Posted", len(posted))
with col2:
    st.metric("Next Period", next_month.strftime("%B %Y"))

styled_divider()

st.markdown("""
### Welcome

This app automates the monthly accounting and quarterly investor reporting for PQSR Fund I.

**Workflow:**

| Step | Page | Description |
|------|------|-------------|
| 1 | **Upload Bank Data** | Upload your monthly bank export (CSV or Excel) |
| 2 | **Review Journal Entries** | Confirm auto-classified transactions and post to the ledger |
| 3 | **Financials - Current** | View the latest Balance Sheet, Income Statement, and cash flow |
| 4 | **Financials - Monthly** | Side-by-side monthly comparison |
| 5 | **Financials - Quarterly** | Q1-Q4 views with partial quarter support |
| 6 | **Generate Reports** | Download the quarterly investor PDF and Excel workbook |
| 7 | **Financial History** | Browse all posted periods with full workbook-style views |

**Status:** {} period(s) posted through {}. Next up: **{}**.
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
