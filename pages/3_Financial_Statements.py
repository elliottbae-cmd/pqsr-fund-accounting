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
    cash_val = bs["Cash"]
    assets_data = [["Cash", f"${cash_val:,.2f}"]]
    st.dataframe(pd.DataFrame(assets_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.markdown("##### FIXED ASSETS")
    fa_data = []
    for asset in ["Land", "Building", "Land Improvements", "F&F", "Equipment", "Signage"]:
        label = "Furniture & Fixtures" if asset == "F&F" else asset
        asset_val = bs[asset]
        fa_data.append([label, f"${asset_val:,.2f}"])
    for asset in ["Building", "Land Improvements", "F&F", "Equipment", "Signage"]:
        label = f"{asset} - Accum. Depreciation"
        ad_val = abs(bs[f"{asset} A/D"])
        fa_data.append([label, f"$({ad_val:,.2f})"])
    total_fa_net = totals["total_fa_net"]
    fa_data.append(["**Total Fixed Assets (Net)**", f"**${total_fa_net:,.2f}**"])
    st.dataframe(pd.DataFrame(fa_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.markdown("##### OTHER ASSETS")
    cap_orig_fee = bs["Capitalized Origination Fee"]
    accum_amort = abs(bs["Accumulated Amortization"])
    total_oa = totals["total_other_assets"]
    oa_data = [
        ["Capitalized Origination Fee", f"${cap_orig_fee:,.2f}"],
        ["Accumulated Amortization", f"$({accum_amort:,.2f})"],
        ["**Total Other Assets**", f"**${total_oa:,.2f}**"],
    ]
    st.dataframe(pd.DataFrame(oa_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    total_assets_val = totals["total_assets"]
    st.metric("Total Assets", f"${total_assets_val:,.2f}")

    st.markdown("---")
    st.markdown("##### LIABILITIES")
    note_payable = bs["Note Payable - BBV"]
    due_to_psp = bs["Due to PSP Investments, LLC"]
    total_liab = totals["total_liabilities"]
    liab_data = [
        ["Note Payable - BBV", f"${note_payable:,.2f}"],
        ["Due to PSP Investments, LLC", f"${due_to_psp:,.2f}"],
        ["**Total Liabilities**", f"**${total_liab:,.2f}**"],
    ]
    st.dataframe(pd.DataFrame(liab_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.markdown("##### MEMBERS' EQUITY")
    eq_data = []
    for inv_key in INVESTORS:
        contrib_val = bs[f"Contributions - {inv_key}"]
        eq_data.append([f"Contributions - {inv_key}", f"${contrib_val:,.2f}"])
    for inv_key in INVESTORS:
        val = bs[f"Distributions - {inv_key}"]
        eq_data.append([f"Distributions - {inv_key}", f"$({abs(val):,.2f})"])
    cy_ni = bs["CY Net Income"]
    eq_data.append(["CY Net Income", f"$({abs(cy_ni):,.2f})" if cy_ni < 0 else f"${cy_ni:,.2f}"])
    re_val = bs["Retained Earnings"]
    eq_data.append(["Retained Earnings", f"$({abs(re_val):,.2f})" if re_val < 0 else f"${re_val:,.2f}"])
    total_eq = totals["total_equity"]
    eq_data.append(["**Total Equity**", f"**${total_eq:,.2f}**"])
    st.dataframe(pd.DataFrame(eq_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

    total_le = totals["total_liabilities_equity"]
    st.metric("Total Liabilities / Equity", f"${total_le:,.2f}")

    # Balance check
    diff = abs(totals["total_assets"] - totals["total_liabilities_equity"])
    if diff < 0.02:
        st.success("Balance Sheet is in balance!")
    else:
        st.error(f"Balance Sheet is OUT OF BALANCE by ${diff:,.2f}")

with tab2:
    st.markdown(f"**{FUND_NAME} | Income Statement | {as_of_date.strftime('%m/%d/%Y')}**")

    rental_inc = is_accounts["Rental Income"]
    interest_exp = is_accounts["Interest Expense"]
    acct_tax = is_accounts["Accounting & Tax Fees"]
    bank_fees = is_accounts.get("Bank Fees", 0)
    depr_exp = is_accounts["Depreciation Expense"]
    is_data = [
        ["**REVENUE**", ""],
        ["Rental Income", f"${rental_inc:,.2f}"],
        ["", ""],
        ["**EXPENSES**", ""],
        ["Interest Expense", f"${interest_exp:,.2f}"],
        ["Accounting & Tax Fees", f"${acct_tax:,.2f}" if acct_tax else "-"],
        ["Bank Fees", f"${bank_fees:,.2f}" if bank_fees else "-"],
        ["Depreciation Expense", f"${depr_exp:,.2f}"],
    ]
    total_exp = sum(is_accounts[k] for k in is_accounts if k != "Rental Income")
    is_data.append(["**Total Expenses**", f"**${total_exp:,.2f}**"])
    net_inc = is_accounts["Rental Income"] - total_exp
    is_data.append(["**Net Income**", f"**${net_inc:,.2f}**"])
    st.dataframe(pd.DataFrame(is_data, columns=["Account", "Amount"]),
                 hide_index=True, use_container_width=True)

with tab3:
    st.markdown(f"**Cash Flow Metrics | Q{quarter} {year}**")

    cf_ebitda = cash_flow["EBITDA"]
    cf_interest = cash_flow["Interest Expense"]
    cf_principal = cash_flow["Principal Payments"]
    cf_fcf = cash_flow["FCF"]
    cf_dscr = cash_flow["DSCR"]
    cf_data = [
        ["EBITDA", f"${cf_ebitda:,.2f}"],
        ["Less: Interest Expense", f"$({cf_interest:,.2f})"],
        ["Less: Principal Payments", f"$({cf_principal:,.2f})"],
        ["**Free Cash Flow (FCF)**", f"**${cf_fcf:,.2f}**"],
    ]
    st.dataframe(pd.DataFrame(cf_data, columns=["Metric", "Amount"]),
                 hide_index=True, use_container_width=True)

    st.metric("DSCR", f"{cf_dscr:.2f}x")
    st.metric("Loan Balance", f"${loan_balance:,.2f}")
    st.metric("Total Principal Paid", f"${get_total_principal_paid(amort_schedule, as_of_date):,.2f}")
