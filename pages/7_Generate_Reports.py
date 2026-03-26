"""Page 4: Generate and download investor report PDF and Excel workbook."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from config.fund_config import (
    FUND_NAME, INVESTORS, DISTRIBUTION_HISTORY, FMV_ASSETS,
    INVESTOR_REPORT_NAMES,
)
from config.baseline_data import QUARTERLY_NOI, TOTAL_DISTRIBUTIONS_THROUGH_BASELINE
from engine.loan_amortization import (
    generate_amortization_schedule, get_ending_balance_at_date,
    get_total_principal_paid, get_payments_for_quarter,
)
from engine.distributions import calculate_quarterly_distribution
from reports.investor_report_pdf import generate_investor_report
from reports.excel_workbook import generate_excel_workbook
from database.db import (
    get_posted_periods, load_balance_sheet, load_income_statement,
    load_cash_flow, load_totals, load_all_journal_entries_through,
    load_all_distributions,
)
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_section_header, styled_divider, format_currency

inject_custom_css()
show_sidebar_branding()
styled_page_header("Generate Reports", "Investor PDF & Excel Workbook")

# Select which period to generate reports for
posted = get_posted_periods()
quarter_ends = [
    p for p in posted if p["quarter_end"]
]

if not quarter_ends and not st.session_state.get("bs"):
    st.info(
        "No quarter-end periods posted yet. "
        "Reports are generated for quarter-end periods (March, June, September, December)."
    )
    st.stop()

# Build period options
period_options = []
for p in quarter_ends:
    pd_obj = date.fromisoformat(p["period_date"])
    period_options.append(pd_obj)

# Also allow session-state data if available
if st.session_state.get("as_of_date") and st.session_state.get("bs"):
    session_date = st.session_state.as_of_date
    if session_date.month in (3, 6, 9, 12):
        session_period = date(session_date.year, session_date.month, 1)
        if session_period not in period_options:
            period_options.append(session_period)

period_options.sort(reverse=True)

if not period_options:
    st.info("No quarter-end data available for report generation.")
    st.stop()

selected_period = st.selectbox(
    "Select Quarter End",
    period_options,
    format_func=lambda d: "Q{} {} ({})".format(
        (d.month - 1) // 3 + 1, d.year, d.strftime("%B %Y")
    ),
)

# Load data
bs = load_balance_sheet(selected_period)
is_accounts = load_income_statement(selected_period)
cash_flow = load_cash_flow(selected_period)
totals_data = load_totals(selected_period)

# Fall back to session state
if not bs and st.session_state.get("bs"):
    bs = st.session_state.bs
    is_accounts = st.session_state.is_accounts
    cash_flow = st.session_state.cash_flow
    totals_data = st.session_state.totals

if not bs:
    st.warning("No financial data found for this period.")
    st.stop()

# Compute dates
as_of_date = date(
    selected_period.year, selected_period.month,
    monthrange(selected_period.year, selected_period.month)[1]
)
quarter = (as_of_date.month - 1) // 3 + 1
year = as_of_date.year
quarter_label = "Q{} {}".format(quarter, year)

# Load journal entries for Excel workbook
journal_entries = load_all_journal_entries_through(selected_period)

# Loan info
amort_schedule = generate_amortization_schedule()
loan_balance = get_ending_balance_at_date(amort_schedule, as_of_date)
total_principal = get_total_principal_paid(amort_schedule, as_of_date)
quarterly_payments = get_payments_for_quarter(amort_schedule, year, quarter)
quarterly_principal = sum(p["principal"] for p in quarterly_payments)

# Distribution calculation
current_qtr_dist = calculate_quarterly_distribution(
    is_accounts.get("Rental Income", 0),
    sum(p["payment"] for p in quarterly_payments),
)

# Build distribution history including current quarter
dist_history = dict(DISTRIBUTION_HISTORY)

# Add any DB-stored distributions from prior quarters
db_dists = load_all_distributions()
for pd_str, amounts in db_dists.items():
    pd_obj = date.fromisoformat(pd_str)
    q = (pd_obj.month - 1) // 3 + 1
    label = "Q{} {}".format(q, pd_obj.year)
    if label not in dist_history:
        total = sum(amounts.values())
        dist_history[label] = {"total": total}
        dist_history[label].update(amounts)

dist_history[quarter_label] = current_qtr_dist

# Cumulative totals
cumulative_total = TOTAL_DISTRIBUTIONS_THROUGH_BASELINE + sum(
    sum(amounts.values()) for amounts in db_dists.values()
)
if quarter_label not in db_dists:
    cumulative_total += current_qtr_dist["total"]

cumulative_by_investor = {}
for inv_key in INVESTORS:
    prior = sum(d.get(inv_key, 0) for d in DISTRIBUTION_HISTORY.values())
    db_prior = sum(amounts.get(inv_key, 0) for amounts in db_dists.values())
    current = current_qtr_dist.get(inv_key, 0)
    cumulative_by_investor[inv_key] = prior + db_prior + (
        current if quarter_label not in db_dists else 0
    )

distribution_data = {
    "current_quarter": current_qtr_dist,
    "history": dist_history,
    "cumulative_total": cumulative_total,
    "cumulative_by_investor": cumulative_by_investor,
}

# NOI history — add current quarter
quarterly_noi = dict(QUARTERLY_NOI)
current_noi = cash_flow.get("EBITDA", 0)
quarterly_noi["Q{}'{}  NOI".format(quarter, str(year)[2:])] = current_noi  # noqa: key matches PDF layout

# Keep only last 4 quarters for T-12
if len(quarterly_noi) > 4:
    keys = list(quarterly_noi.keys())
    quarterly_noi = {k: quarterly_noi[k] for k in keys[-4:]}

# Investor notes (editable)
styled_section_header("Investor Notes")
st.markdown(
    "<p style='color: #797979; font-size: 0.9rem; margin-bottom: 16px;'>"
    "Edit the notes below before generating the report. "
    "These will appear on the final page of the investor PDF.</p>",
    unsafe_allow_html=True,
)

default_notes = [
    "1.) The Nacogdoches property had an uptick in inquiries in Q4 of 2025. "
    "Management will continue to hold firm on pricing. This tenant now has 83 units backing the lease.",
    "2.) Legacy Chicken (Popeyes NM Tenant) has opened one additional location in Q1 of 2026.",
    "3.) Fund expenses for Q{q} totaled ${amt:,.0f} for CBIZ tax prep fees.".format(
        q=quarter, amt=is_accounts.get("Accounting & Tax Fees", 0)
    ),
    "4.) As of {}, the fund has paid down ${:,.0f} in loan principal.".format(
        as_of_date.strftime("%m/%d/%Y"), total_principal
    ),
    "5.) The fund has a 6.65% fixed interest rate. Management will continue to monitor "
    "rates in {} to determine if it will be beneficial to refinance the note.".format(year),
    "6.) All leases are current.",
    "7.) Pending Litigation - N/A",
]

notes = []
st.markdown(
    "<div style='background: #FAFAFA; border: 1px solid #E8E8E8; "
    "border-left: 4px solid #F4A523; border-radius: 6px; "
    "padding: 16px 20px 4px 20px; margin-bottom: 20px;'>"
    "<p style='color: #494949; font-weight: 600; font-size: 0.85rem; "
    "margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;'>"
    "Editable Notes (7)</p></div>",
    unsafe_allow_html=True,
)
for i, note in enumerate(default_notes):
    label = "Note {}".format(i + 1)
    notes.append(st.text_area(
        label, value=note, height=60,
        key="note_{}".format(i),
    ))

# FMV override
st.subheader("Fair Market Value")
fmv_default = "{:,.0f}".format(FMV_ASSETS)
fmv_input = st.text_input(
    "Est. FMV of Assets Held",
    value=fmv_default,
    help="Enter dollar amount (commas optional)",
)
try:
    fmv = float(fmv_input.replace(",", "").replace("$", ""))
except ValueError:
    st.error("Please enter a valid number.")
    fmv = FMV_ASSETS

st.markdown("---")

# Generate buttons
col1, col2 = st.columns(2)

with col1:
    st.subheader("Investor Report PDF")
    if st.button("Generate PDF", type="primary"):
        with st.spinner("Generating investor report..."):
            try:
                pdf_buffer = generate_investor_report(
                    bs=bs,
                    is_accounts=is_accounts,
                    cash_flow=cash_flow,
                    totals=totals_data,
                    distribution_data=distribution_data,
                    as_of_date=as_of_date,
                    investor_notes=notes,
                    quarterly_noi_history=quarterly_noi,
                    loan_balance=loan_balance,
                    total_principal_paid=total_principal,
                )
                st.download_button(
                    label="Download Investor Report PDF",
                    data=pdf_buffer,
                    file_name="PQSR_Fund_I_Investor_Summary_{}.pdf".format(
                        as_of_date.strftime("%m_%d_%Y")
                    ),
                    mime="application/pdf",
                )
                st.success("PDF generated successfully!")
            except Exception as e:
                st.error("Error generating PDF: {}".format(e))
                import traceback
                st.code(traceback.format_exc())

with col2:
    st.subheader("Excel Workbook")
    if st.button("Generate Excel", type="primary"):
        with st.spinner("Generating Excel workbook..."):
            try:
                excel_buffer = generate_excel_workbook(
                    bs=bs,
                    is_accounts=is_accounts,
                    cash_flow=cash_flow,
                    totals=totals_data,
                    distribution_data=distribution_data,
                    journal_entries=journal_entries,
                    as_of_date=as_of_date,
                )
                st.download_button(
                    label="Download Excel Workbook",
                    data=excel_buffer,
                    file_name="PQSR_Accounting_Workbook_{}.xlsx".format(
                        as_of_date.strftime("%m.%d.%y")
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.success("Excel workbook generated successfully!")
            except Exception as e:
                st.error("Error generating Excel: {}".format(e))
                import traceback
                st.code(traceback.format_exc())

# Distribution summary
st.markdown("---")
st.subheader("{} Distribution Summary".format(quarter_label))

dist_df_data = []
for inv_key, inv in INVESTORS.items():
    own_pct = inv["ownership_pct"]
    inv_dist = current_qtr_dist.get(inv_key, 0)
    dist_df_data.append({
        "Investor": inv["full_name"],
        "Ownership %": "{:.2%}".format(own_pct),
        "Distribution": "${:,.2f}".format(inv_dist),
    })
total_dist = current_qtr_dist["total"]
dist_df_data.append({
    "Investor": "**Total**",
    "Ownership %": "100.00%",
    "Distribution": "**${:,.2f}**".format(total_dist),
})

st.dataframe(pd.DataFrame(dist_df_data), hide_index=True, use_container_width=True)
