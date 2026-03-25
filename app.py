"""PQSR Fund I — Accounting Automation App"""

import streamlit as st

st.set_page_config(
    page_title="PQSR Fund I | Accounting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("PQSR Fund I, LLC")
st.subheader("Accounting & Investor Reporting")

st.markdown("---")

st.markdown("""
### Welcome

This app automates the monthly accounting and quarterly investor reporting for PQSR Fund I.

**Workflow:**

1. **Upload Bank Data** — Upload your monthly bank CSV export(s)
2. **Review Journal Entries** — Confirm auto-classified transactions and categorize unknowns
3. **Financial Statements** — View the rolled-forward Balance Sheet, Income Statement, and cash flow metrics
4. **Generate Reports** — Download the quarterly investor PDF and updated Excel workbook

**Baseline:** Financials are anchored to the 12/31/2025 year-end workbook. Upload bank CSVs for each month since then.
""")

# Initialize session state
if "classified_transactions" not in st.session_state:
    st.session_state.classified_transactions = []
if "journal_entries" not in st.session_state:
    st.session_state.journal_entries = []
if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False
