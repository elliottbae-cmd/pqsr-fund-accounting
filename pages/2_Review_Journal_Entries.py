"""Page 2: Review generated journal entries before posting."""

import streamlit as st
import pandas as pd
from datetime import date
from collections import defaultdict
from engine.journal_entries import generate_monthly_ajes, generate_depreciation_aje
from engine.depreciation import is_quarter_end
from calendar import monthrange

st.header("Review Journal Entries")

if not st.session_state.get("classified_transactions"):
    st.info("Please upload and classify bank data first.")
    st.stop()

classified = st.session_state.classified_transactions

# Group transactions by month
monthly_groups = defaultdict(list)
for txn in classified:
    d = txn["date"]
    if hasattr(d, 'year'):
        key = date(d.year, d.month, 1)
    else:
        key = date.today().replace(day=1)
    monthly_groups[key].append(txn)

# Generate journal entries
all_entries = []
quarters_processed = set()

for month_date in sorted(monthly_groups.keys()):
    month_txns = monthly_groups[month_date]
    entries = generate_monthly_ajes(month_txns, month_date)
    all_entries.extend(entries)

    # Check if this month ends a quarter
    last_day = date(month_date.year, month_date.month,
                    monthrange(month_date.year, month_date.month)[1])
    quarter = (month_date.month - 1) // 3 + 1
    quarter_key = (month_date.year, quarter)

    if month_date.month in (3, 6, 9, 12) and quarter_key not in quarters_processed:
        depr_entry = generate_depreciation_aje(last_day)
        all_entries.append(depr_entry)
        quarters_processed.add(quarter_key)

st.session_state.journal_entries = all_entries

# Display entries
for i, entry in enumerate(all_entries):
    desc = entry["description"]
    edate = entry["date"].strftime("%m/%d/%Y")
    with st.expander(
        f"AJE {i+1}: {desc} ({edate})",
        expanded=(i < 3),
    ):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Debits:**")
            for acct, amt in entry["debits"].items():
                st.text(f"  {acct}: ${amt:,.2f}")
        with col2:
            st.markdown("**Credits:**")
            for acct, amt in entry["credits"].items():
                st.text(f"  {acct}: ${amt:,.2f}")

        # Verify balanced
        total_dr = sum(entry["debits"].values())
        total_cr = sum(entry["credits"].values())
        if abs(total_dr - total_cr) < 0.01:
            st.success(f"Balanced: ${total_dr:,.2f}")
        else:
            st.error(f"OUT OF BALANCE - DR: ${total_dr:,.2f} / CR: ${total_cr:,.2f}")

# Summary
st.markdown("---")
st.subheader("Summary")
st.metric("Total Journal Entries", len(all_entries))

total_debits = sum(sum(e["debits"].values()) for e in all_entries)
total_credits = sum(sum(e["credits"].values()) for e in all_entries)
col1, col2 = st.columns(2)
col1.metric("Total Debits", f"${total_debits:,.2f}")
col2.metric("Total Credits", f"${total_credits:,.2f}")

if st.button("Post Journal Entries", type="primary"):
    st.session_state.entries_posted = True
    st.success("Journal entries posted! Navigate to 'Financial Statements' to view results.")
