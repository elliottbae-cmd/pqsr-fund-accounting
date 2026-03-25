"""Page 3: View rolled-forward financial statements."""

import streamlit as st
import pandas as pd
from datetime import date
from engine.financial_engine import roll_forward, compute_totals, compute_cash_flow_metrics
from engine.loan_amortization import (
    generate_amortization_schedule, get_payments_for_quarter,
    get_ending_balance_at_date, get_total_principal_paid,
)
from config.fund_config import FUND_NAME, INVESTORS, FIXED_ASSETS

st.header("Financial Statements")

if not st.session_state.get("journal_entries"):
    st.info("Please generate and post journal entries first.")
    st.stop()

entries = st.session_state.journal_entries

# Determine as-of date from the latest entry
as_of_date = max(e["date"] for e in entries)
quarter = (as_of_date.month - 1) // 3 + 1
year = as_of_date.year

st.subheader(f"As of {as_of_date.strftime('%m/%d/%Y')}")

# Roll forward
bs, is_accounts = roll_forward(entries, as_of_date)
totals = compute_totals(bs)

# Loan info
amort_schedule = generate_amortization_schedule()
quarterly_payments = get_payments_for_quarter(amort_schedule, year, quarter)
quarterly_principal = sum(p["principal"] for p in quarterly_payments)
quarterly_interest = sum(p["interest"] for p in quarterly_payments)
loan_balance = get_ending_balance_at_date(amort_schedule, as_of_date)

# Cash flow metrics
cash_flow = compute_cash_flow_metrics(is_accounts, quarterly_principal)

# Store for report generation
st.session_state.bs = bs
st.session_state.is_accounts = is_accounts
st.session_state.totals = totals
st.session_state.cash_flow = cash_flow
st.session_state.as_of_date = as_of_date
st.session_state.loan_balance = loan_balance
st.session_state.quarterly_principal = quarterly_principal

# Display
tab1, tab2, tab3 = st.tabs(["Balance Sheet", "Income Statement", "Cash Flow"])

with tab1:
    st.markdown(f"**{FUND_NAME} | Balance Sheet | {as_of_date.strftime('%m/%d/%Y')}**")

    # Assets
    st.markdown("##### ASSETS")
    assets_data = [["Cash", f"${bs['Cash']:,.2f}"]]
    st.dataframe(pd.DataFrame(assets_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.markdown("##### FIXED ASSETS")
    fa_data = []
    for asset in ["Land", "Building", "Land Improvements", "F&F", "Equipment", "Signage"]:
        label = "Furniture & Fixtures" if asset == "F&F" else asset
        fa_data.append([label, f"${bs[asset]:,.2f}"])
    for asset in ["Building", "Land Improvements", "F&F", "Equipment", "Signage"]:
        label = f"{asset} - Accum. Depreciation"
        fa_data.append([label, f"$({abs(bs[f'{asset} A/D']):,.2f})"])
    fa_data.append(["**Total Fixed Assets (Net)**", f"**${totals['total_fa_net']:,.2f}**"])
    st.dataframe(pd.DataFrame(fa_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.markdown("##### OTHER ASSETS")
    oa_data = [
        ["Capitalized Origination Fee", f"${bs['Capitalized Origination Fee']:,.2f}"],
        ["Accumulated Amortization", f"$({abs(bs['Accumulated Amortization']):,.2f})"],
        ["**Total Other Assets**", f"**${totals['total_other_assets']:,.2f}**"],
    ]
    st.dataframe(pd.DataFrame(oa_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.metric("Total Assets", f"${totals['total_assets']:,.2f}")

    st.markdown("---")
    st.markdown("##### LIABILITIES")
    liab_data = [
        ["Note Payable - BBV", f"${bs['Note Payable - BBV']:,.2f}"],
        ["Due to PSP Investments, LLC", f"${bs['Due to PSP Investments, LLC']:,.2f}"],
        ["**Total Liabilities**", f"**${totals['total_liabilities']:,.2f}**"],
    ]
    st.dataframe(pd.DataFrame(liab_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.markdown("##### MEMBERS' EQUITY")
    eq_data = []
    for inv_key in INVESTORS:
        eq_data.append([f"Contributions - {inv_key}", f"${bs[f'Contributions - {inv_key}']:,.2f}"])
    for inv_key in INVESTORS:
        val = bs[f"Distributions - {inv_key}"]
        eq_data.append([f"Distributions - {inv_key}", f"$({abs(val):,.2f})"])
    eq_data.append(["CY Net Income", f"$({abs(bs['CY Net Income']):,.2f})" if bs['CY Net Income'] < 0 else f"${bs['CY Net Income']:,.2f}"])
    eq_data.append(["Retained Earnings", f"$({abs(bs['Retained Earnings']):,.2f})" if bs['Retained Earnings'] < 0 else f"${bs['Retained Earnings']:,.2f}"])
    eq_data.append(["**Total Equity**", f"**${totals['total_equity']:,.2f}**"])
    st.dataframe(pd.DataFrame(eq_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.metric("Total Liabilities / Equity", f"${totals['total_liabilities_equity']:,.2f}")

    # Balance check
    diff = abs(totals["total_assets"] - totals["total_liabilities_equity"])
    if diff < 0.02:
        st.success("Balance Sheet is in balance!")
    else:
        st.error(f"Balance Sheet is OUT OF BALANCE by ${diff:,.2f}")

with tab2:
    st.markdown(f"**{FUND_NAME} | Income Statement | {as_of_date.strftime('%m/%d/%Y')}**")

    is_data = [
        ["**REVENUE**", ""],
        ["Rental Income", f"${is_accounts['Rental Income']:,.2f}"],
        ["", ""],
        ["**EXPENSES**", ""],
        ["Interest Expense", f"${is_accounts['Interest Expense']:,.2f}"],
        ["Accounting & Tax Fees", f"${is_accounts['Accounting & Tax Fees']:,.2f}" if is_accounts['Accounting & Tax Fees'] else "-"],
        ["Bank Fees", f"${is_accounts.get('Bank Fees', 0):,.2f}" if is_accounts.get('Bank Fees', 0) else "-"],
        ["Depreciation Expense", f"${is_accounts['Depreciation Expense']:,.2f}"],
    ]
    total_exp = sum(is_accounts[k] for k in is_accounts if k != "Rental Income")
    is_data.append(["**Total Expenses**", f"**${total_exp:,.2f}**"])
    net_inc = is_accounts["Rental Income"] - total_exp
    is_data.append(["**Net Income**", f"**${net_inc:,.2f}**"])
    st.dataframe(pd.DataFrame(is_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

with tab3:
    st.markdown(f"**Cash Flow Metrics | Q{quarter} {year}**")

    cf_data = [
        ["EBITDA", f"${cash_flow['EBITDA']:,.2f}"],
        ["Less: Interest Expense", f"$({cash_flow['Interest Expense']:,.2f})"],
        ["Less: Principal Payments", f"$({cash_flow['Principal Payments']:,.2f})"],
        ["**Free Cash Flow (FCF)**", f"**${cash_flow['FCF']:,.2f}**"],
    ]
    st.dataframe(pd.DataFrame(cf_data, columns=["Metric", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.metric("DSCR", f"{cash_flow['DSCR']:.2f}x")
    st.metric("Loan Balance", f"${loan_balance:,.2f}")
    st.metric("Total Principal Paid", f"${get_total_principal_paid(amort_schedule, as_of_date):,.2f}")
