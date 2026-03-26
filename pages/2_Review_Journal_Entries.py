"""Page 2: Review generated journal entries before posting — with DB persistence."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from engine.journal_entries import generate_monthly_ajes, generate_depreciation_aje
from engine.financial_engine import roll_forward, compute_totals, compute_cash_flow_metrics
from engine.loan_amortization import (
    generate_amortization_schedule, get_payments_for_quarter,
    get_ending_balance_at_date, get_total_principal_paid,
)
from engine.distributions import calculate_quarterly_distribution
from config.fund_config import INVESTORS, DISTRIBUTION_HISTORY
from config.baseline_data import TOTAL_DISTRIBUTIONS_THROUGH_BASELINE
from database.db import (
    save_period, is_period_posted, load_all_journal_entries_through,
    get_posted_periods,
)
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_section_header, styled_divider, format_currency

inject_custom_css()
show_sidebar_branding()
styled_page_header("Review Journal Entries", "Verify & Post to Ledger")

if not st.session_state.get("classified_transactions"):
    st.info("Please upload and classify bank data first.")
    st.stop()

classified = st.session_state.classified_transactions
processing_month = st.session_state.get("processing_month")

if not processing_month:
    st.error("Processing month not set. Go back to Upload Bank Data.")
    st.stop()

month_label = processing_month.strftime("%B %Y")
st.subheader("Period: {}".format(month_label))

if is_period_posted(processing_month):
    st.warning(
        "{} has already been posted. Re-posting will overwrite the existing data.".format(
            month_label
        )
    )

# Generate journal entries for this month
month_date = date(processing_month.year, processing_month.month, 1)
entries = generate_monthly_ajes(classified, month_date)

# Check if this month ends a quarter
is_qtr_end = processing_month.month in (3, 6, 9, 12)
if is_qtr_end:
    st.info(
        "This is a quarter-end month. After posting, go to the "
        "**Depreciation** page to review and book the quarterly depreciation entry."
    )

st.session_state.journal_entries = entries

# Display entries
grand_total_dr = 0.0
grand_total_cr = 0.0

for i, entry in enumerate(entries):
    desc = entry["description"]
    edate = entry["date"].strftime("%m/%d/%Y")
    entry_dr = sum(entry["debits"].values())
    entry_cr = sum(entry["credits"].values())
    grand_total_dr += entry_dr
    grand_total_cr += entry_cr

    with st.expander(
        "AJE {}: {} ({})".format(i + 1, desc, edate),
        expanded=True,
    ):
        # Build GL Account / Debit / Credit table
        aje_rows = []
        for acct, amt in entry["debits"].items():
            aje_rows.append({
                "GL Account": acct,
                "Debit": "${:,.2f}".format(amt),
                "Credit": "",
            })
        for acct, amt in entry["credits"].items():
            aje_rows.append({
                "GL Account": "    {}".format(acct),
                "Debit": "",
                "Credit": "${:,.2f}".format(amt),
            })
        # Totals row
        aje_rows.append({
            "GL Account": "**Totals**",
            "Debit": "**${:,.2f}**".format(entry_dr),
            "Credit": "**${:,.2f}**".format(entry_cr),
        })

        st.dataframe(
            pd.DataFrame(aje_rows),
            hide_index=True, use_container_width=True,
        )

        # Balance check
        net = entry_dr - entry_cr
        if abs(net) < 0.01:
            st.success("Variance: $0.00 — In Balance")
        else:
            st.error("Variance: ${:,.2f} — OUT OF BALANCE".format(net))

# Summary
st.markdown("---")
st.subheader("Summary")
st.metric("Total Journal Entries", len(entries))

col1, col2, col3 = st.columns(3)
col1.metric("Total Debits", "${:,.2f}".format(grand_total_dr))
col2.metric("Total Credits", "${:,.2f}".format(grand_total_cr))
grand_net = grand_total_dr - grand_total_cr
col3.metric("Net", "${:,.2f}".format(grand_net))
if abs(grand_net) < 0.01:
    st.success("All journal entries net to zero.")
else:
    st.error("AJEs are OUT OF BALANCE by ${:,.2f}".format(grand_net))

# Post button
if st.button("Post Journal Entries & Save to Database", type="primary"):
    with st.spinner("Posting and calculating financials..."):
        # Get ALL journal entries through this period (prior + current)
        prior_entries = load_all_journal_entries_through(
            date(processing_month.year, processing_month.month, 1)
        )
        # Filter out any entries from the current month (in case of re-post)
        prior_entries = [
            e for e in prior_entries
            if not (e["date"].year == processing_month.year
                    and e["date"].month == processing_month.month)
        ]
        all_entries = prior_entries + entries

        # Roll forward from baseline
        last_day = date(
            processing_month.year, processing_month.month,
            monthrange(processing_month.year, processing_month.month)[1]
        )
        bs, is_accounts = roll_forward(all_entries, last_day)
        totals = compute_totals(bs)

        # Loan / cash flow — use only months posted in this quarter
        amort_schedule = generate_amortization_schedule()
        quarter = (processing_month.month - 1) // 3 + 1
        year = processing_month.year
        quarter_start_month = (quarter - 1) * 3 + 1
        # Count how many months of this quarter have been posted
        posted_months_in_qtr = []
        for m in range(quarter_start_month, processing_month.month + 1):
            if is_period_posted(date(year, m, 1)) or m == processing_month.month:
                posted_months_in_qtr.append(m)
        # Only sum principal for posted months (not full quarter)
        quarterly_payments = get_payments_for_quarter(amort_schedule, year, quarter)
        relevant_payments = [
            p for p in quarterly_payments
            if p["payment_date"].month in posted_months_in_qtr
        ]
        period_principal = sum(p["principal"] for p in relevant_payments)
        cash_flow = compute_cash_flow_metrics(is_accounts, period_principal)

        # Distributions (quarter-end only)
        distributions = None
        if is_qtr_end:
            distributions = calculate_quarterly_distribution(
                is_accounts["Rental Income"],
                sum(p["payment"] for p in quarterly_payments),
            )

        # Save everything to database
        save_period(
            period_date=processing_month,
            transactions=classified,
            journal_entries=entries,
            bs=bs,
            is_accounts=is_accounts,
            cash_flow=cash_flow,
            totals=totals,
            distributions=distributions,
        )

        # Also store in session state for downstream pages
        st.session_state.bs = bs
        st.session_state.is_accounts = is_accounts
        st.session_state.totals = totals
        st.session_state.cash_flow = cash_flow
        st.session_state.as_of_date = last_day
        st.session_state.entries_posted = True

        st.success(
            "{} posted and saved to database! "
            "Navigate to 'Financial Statements' or 'Financial History' to view.".format(
                month_label
            )
        )
