"""Page 4: Generate and download investor report PDF and Excel workbook."""

import streamlit as st
from datetime import date
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

st.header("Generate Reports")

if not st.session_state.get("bs"):
    st.info("Please process financial statements first.")
    st.stop()

bs = st.session_state.bs
is_accounts = st.session_state.is_accounts
totals = st.session_state.totals
cash_flow = st.session_state.cash_flow
as_of_date = st.session_state.as_of_date
journal_entries = st.session_state.journal_entries

quarter = (as_of_date.month - 1) // 3 + 1
year = as_of_date.year
quarter_label = f"Q{quarter} {year}"

# Loan info
amort_schedule = generate_amortization_schedule()
loan_balance = get_ending_balance_at_date(amort_schedule, as_of_date)
total_principal = get_total_principal_paid(amort_schedule, as_of_date)
quarterly_payments = get_payments_for_quarter(amort_schedule, year, quarter)
quarterly_principal = sum(p["principal"] for p in quarterly_payments)

# Distribution calculation
current_qtr_dist = calculate_quarterly_distribution(
    is_accounts["Rental Income"],
    sum(p["payment"] for p in quarterly_payments),
)

# Build distribution history including current quarter
dist_history = dict(DISTRIBUTION_HISTORY)
dist_history[quarter_label] = current_qtr_dist

# Cumulative totals
cumulative_total = TOTAL_DISTRIBUTIONS_THROUGH_BASELINE + current_qtr_dist["total"]
cumulative_by_investor = {}
for inv_key in INVESTORS:
    prior = sum(
        d.get(inv_key, 0) for d in DISTRIBUTION_HISTORY.values()
    )
    cumulative_by_investor[inv_key] = prior + current_qtr_dist.get(inv_key, 0)

distribution_data = {
    "current_quarter": current_qtr_dist,
    "history": dist_history,
    "cumulative_total": cumulative_total,
    "cumulative_by_investor": cumulative_by_investor,
}

# NOI history — add current quarter
quarterly_noi = dict(QUARTERLY_NOI)
current_noi = cash_flow["EBITDA"]
quarterly_noi[f"Q{quarter}'{str(year)[2:]} NOI"] = current_noi

# Keep only last 4 quarters for T-12
if len(quarterly_noi) > 4:
    keys = list(quarterly_noi.keys())
    quarterly_noi = {k: quarterly_noi[k] for k in keys[-4:]}

# Investor notes (editable)
st.subheader("Investor Notes")
st.markdown("Edit the notes below before generating the report.")

default_notes = [
    f"1.) The Nacogdoches property had an uptick in inquiries in Q4 of 2025. Management will continue to hold firm on pricing. This tenant now has 83 units backing the lease.",
    f"2.) Legacy Chicken (Popeyes NM Tenant) has opened one additional location in Q1 of 2026.",
    f"3.) Fund expenses for Q{quarter} totaled ${is_accounts.get('Accounting & Tax Fees', 0):,.0f} for CBIZ tax prep fees.",
    f"4.) As of {as_of_date.strftime('%m/%d/%Y')}, the fund has paid down ${total_principal:,.0f} in loan principal.",
    f"5.) The fund has a 6.65% fixed interest rate. Management will continue to monitor rates in {year} to determine if it will be beneficial to refinance the note.",
    "6.) All leases are current.",
    "7.) Pending Litigation - N/A",
]

notes = []
for i, note in enumerate(default_notes):
    notes.append(st.text_area(f"Note {i+1}", value=note, height=60, key=f"note_{i}"))

# FMV override
st.subheader("Fair Market Value")
fmv = st.number_input("Est. FMV of Assets Held", value=FMV_ASSETS, step=1000.0, format="%.0f")

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
                    totals=totals,
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
                    file_name=f"PQSR_Fund_I_Investor_Summary_{as_of_date.strftime('%m_%d_%Y')}.pdf",
                    mime="application/pdf",
                )
                st.success("PDF generated successfully!")
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
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
                    totals=totals,
                    distribution_data=distribution_data,
                    journal_entries=journal_entries,
                    as_of_date=as_of_date,
                )
                st.download_button(
                    label="Download Excel Workbook",
                    data=excel_buffer,
                    file_name=f"PQSR_Accounting_Workbook_{as_of_date.strftime('%m.%d.%y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.success("Excel workbook generated successfully!")
            except Exception as e:
                st.error(f"Error generating Excel: {e}")
                import traceback
                st.code(traceback.format_exc())

# Distribution summary
st.markdown("---")
st.subheader(f"Q{quarter} {year} Distribution Summary")

dist_df_data = []
for inv_key, inv in INVESTORS.items():
    dist_df_data.append({
        "Investor": inv["full_name"],
        "Ownership %": f"{inv['ownership_pct']:.2%}",
        "Distribution": f"${current_qtr_dist.get(inv_key, 0):,.2f}",
    })
dist_df_data.append({
    "Investor": "**Total**",
    "Ownership %": "100.00%",
    "Distribution": f"**${current_qtr_dist['total']:,.2f}**",
})

import pandas as pd
st.dataframe(pd.DataFrame(dist_df_data), hide_index=True, use_container_width=True)
