"""Page 3: View rolled-forward financial statements — reads from DB or session."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from engine.financial_engine import roll_forward, compute_totals, compute_cash_flow_metrics
from engine.loan_amortization import (
    generate_amortization_schedule, get_payments_for_quarter,
    get_ending_balance_at_date, get_total_principal_paid,
)
from config.fund_config import FUND_NAME, INVESTORS, FIXED_ASSETS
from database.db import (
    get_posted_periods, load_balance_sheet, load_income_statement,
    load_cash_flow, load_totals,
)
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_section_header, styled_divider, format_currency

inject_custom_css()
show_sidebar_branding()
styled_page_header("Financial Statements", "Current Period View")

# Period selector — load from DB
posted = get_posted_periods()

if not posted and not st.session_state.get("bs"):
    st.info("No periods have been posted yet. Upload and process bank data first.")
    st.stop()

# Build period options
period_options = []
for p in posted:
    pd_obj = date.fromisoformat(p["period_date"])
    period_options.append(pd_obj)

# If we have session state from a just-posted period, add it if not already in list
if st.session_state.get("as_of_date"):
    session_date = st.session_state.as_of_date
    session_period = date(session_date.year, session_date.month, 1)
    if session_period not in period_options:
        period_options.append(session_period)

if not period_options:
    st.info("No periods available. Post journal entries first.")
    st.stop()

period_options.sort(reverse=True)

selected_period = st.selectbox(
    "Select Period",
    period_options,
    format_func=lambda d: d.strftime("%B %Y"),
)

# Load data — prefer DB, fall back to session state
bs = load_balance_sheet(selected_period)
is_accounts = load_income_statement(selected_period)
cash_flow_data = load_cash_flow(selected_period)
totals_data = load_totals(selected_period)

# Fall back to session state if DB is empty (just-posted, not yet committed)
if not bs and st.session_state.get("bs"):
    bs = st.session_state.bs
    is_accounts = st.session_state.is_accounts
    cash_flow_data = st.session_state.cash_flow
    totals_data = st.session_state.totals

if not bs:
    st.warning("No financial data found for this period.")
    st.stop()

# Compute as-of date
as_of_date = date(
    selected_period.year, selected_period.month,
    monthrange(selected_period.year, selected_period.month)[1]
)
quarter = (as_of_date.month - 1) // 3 + 1
year = as_of_date.year

# Loan info
amort_schedule = generate_amortization_schedule()
quarterly_payments = get_payments_for_quarter(amort_schedule, year, quarter)
quarterly_principal = sum(p["principal"] for p in quarterly_payments)
loan_balance = get_ending_balance_at_date(amort_schedule, as_of_date)

st.subheader("As of {}".format(as_of_date.strftime("%m/%d/%Y")))

# Display
tab1, tab2, tab3 = st.tabs(["Balance Sheet", "Income Statement", "Cash Flow"])

with tab1:
    st.markdown(
        "**{} | Balance Sheet | {}**".format(
            FUND_NAME, as_of_date.strftime("%m/%d/%Y")
        )
    )

    # Assets
    st.markdown("##### ASSETS")
    cash_val = bs.get("Cash", 0)
    assets_data = [["Cash", "${:,.2f}".format(cash_val)]]
    st.dataframe(
        pd.DataFrame(assets_data, columns=["Account", "Amount"]),
        hide_index=True, use_container_width=True,
    )

    st.markdown("##### FIXED ASSETS")
    fa_data = []
    for asset in ["Land", "Building", "Land Improvements", "F&F", "Equipment", "Signage"]:
        label = "Furniture & Fixtures" if asset == "F&F" else asset
        asset_val = bs.get(asset, 0)
        fa_data.append([label, "${:,.2f}".format(asset_val)])
    for asset in ["Building", "Land Improvements", "F&F", "Equipment", "Signage"]:
        ad_key = "{} A/D".format(asset)
        label = "{} - Accum. Depreciation".format(asset)
        ad_val = abs(bs.get(ad_key, 0))
        fa_data.append([label, "$({:,.2f})".format(ad_val)])
    total_fa_net = totals_data.get("total_fa_net", 0)
    fa_data.append(["**Total Fixed Assets (Net)**", "**${:,.2f}**".format(total_fa_net)])
    st.dataframe(
        pd.DataFrame(fa_data, columns=["Account", "Amount"]),
        hide_index=True, use_container_width=True,
    )

    st.markdown("##### OTHER ASSETS")
    cap_orig_fee = bs.get("Capitalized Origination Fee", 0)
    accum_amort = abs(bs.get("Accumulated Amortization", 0))
    total_oa = totals_data.get("total_other_assets", 0)
    oa_data = [
        ["Capitalized Origination Fee", "${:,.2f}".format(cap_orig_fee)],
        ["Accumulated Amortization", "$({:,.2f})".format(accum_amort)],
        ["**Total Other Assets**", "**${:,.2f}**".format(total_oa)],
    ]
    st.dataframe(
        pd.DataFrame(oa_data, columns=["Account", "Amount"]),
        hide_index=True, use_container_width=True,
    )

    total_assets_val = totals_data.get("total_assets", 0)
    st.metric("Total Assets", "${:,.2f}".format(total_assets_val))

    st.markdown("---")
    st.markdown("##### LIABILITIES")
    note_payable = bs.get("Note Payable - BBV", 0)
    due_to_psp = bs.get("Due to PSP Investments, LLC", 0)
    total_liab = totals_data.get("total_liabilities", 0)
    liab_data = [
        ["Note Payable - BBV", "${:,.2f}".format(note_payable)],
        ["Due to PSP Investments, LLC", "${:,.2f}".format(due_to_psp)],
        ["**Total Liabilities**", "**${:,.2f}**".format(total_liab)],
    ]
    st.dataframe(
        pd.DataFrame(liab_data, columns=["Account", "Amount"]),
        hide_index=True, use_container_width=True,
    )

    st.markdown("##### MEMBERS' EQUITY")
    eq_data = []
    for inv_key in INVESTORS:
        contrib_key = "Contributions - {}".format(inv_key)
        contrib_val = bs.get(contrib_key, 0)
        eq_data.append([contrib_key, "${:,.2f}".format(contrib_val)])
    for inv_key in INVESTORS:
        dist_key = "Distributions - {}".format(inv_key)
        val = bs.get(dist_key, 0)
        eq_data.append([dist_key, "$({:,.2f})".format(abs(val))])
    cy_ni = bs.get("CY Net Income", 0)
    if cy_ni < 0:
        eq_data.append(["CY Net Income", "$({:,.2f})".format(abs(cy_ni))])
    else:
        eq_data.append(["CY Net Income", "${:,.2f}".format(cy_ni)])
    re_val = bs.get("Retained Earnings", 0)
    if re_val < 0:
        eq_data.append(["Retained Earnings", "$({:,.2f})".format(abs(re_val))])
    else:
        eq_data.append(["Retained Earnings", "${:,.2f}".format(re_val)])
    total_eq = totals_data.get("total_equity", 0)
    eq_data.append(["**Total Equity**", "**${:,.2f}**".format(total_eq)])
    st.dataframe(
        pd.DataFrame(eq_data, columns=["Account", "Amount"]),
        hide_index=True, use_container_width=True,
    )

    total_le = totals_data.get("total_liabilities_equity", 0)
    st.metric("Total Liabilities / Equity", "${:,.2f}".format(total_le))

    # Balance check
    diff = abs(totals_data.get("total_assets", 0) - totals_data.get("total_liabilities_equity", 0))
    if diff < 0.02:
        st.success("Balance Sheet is in balance!")
    else:
        st.error("Balance Sheet is OUT OF BALANCE by ${:,.2f}".format(diff))

with tab2:
    st.markdown(
        "**{} | Income Statement | {}**".format(
            FUND_NAME, as_of_date.strftime("%m/%d/%Y")
        )
    )

    rental_inc = is_accounts.get("Rental Income", 0)
    interest_exp = is_accounts.get("Interest Expense", 0)
    acct_tax = is_accounts.get("Accounting & Tax Fees", 0)
    bank_fees = is_accounts.get("Bank Fees", 0)
    depr_exp = is_accounts.get("Depreciation Expense", 0)
    is_data = [
        ["**REVENUE**", ""],
        ["Rental Income", "${:,.2f}".format(rental_inc)],
        ["", ""],
        ["**EXPENSES**", ""],
        ["Interest Expense", "${:,.2f}".format(interest_exp)],
        ["Accounting & Tax Fees", "${:,.2f}".format(acct_tax) if acct_tax else "-"],
        ["Bank Fees", "${:,.2f}".format(bank_fees) if bank_fees else "-"],
        ["Depreciation Expense", "${:,.2f}".format(depr_exp)],
    ]
    total_exp = sum(
        is_accounts.get(k, 0) for k in is_accounts if k != "Rental Income"
    )
    is_data.append(["**Total Expenses**", "**${:,.2f}**".format(total_exp)])
    net_inc = rental_inc - total_exp
    is_data.append(["**Net Income**", "**${:,.2f}**".format(net_inc)])
    st.dataframe(
        pd.DataFrame(is_data, columns=["Account", "Amount"]),
        hide_index=True, use_container_width=True,
    )

with tab3:
    st.markdown("**Cash Flow Metrics | Q{} {}**".format(quarter, year))

    cf_ebitda = cash_flow_data.get("EBITDA", 0)
    cf_interest = cash_flow_data.get("Interest Expense", 0)
    cf_principal = cash_flow_data.get("Principal Payments", 0)
    cf_fcf = cash_flow_data.get("FCF", 0)
    cf_dscr = cash_flow_data.get("DSCR", 0)
    cf_data = [
        ["EBITDA", "${:,.2f}".format(cf_ebitda)],
        ["Less: Interest Expense", "$({:,.2f})".format(cf_interest)],
        ["Less: Principal Payments", "$({:,.2f})".format(cf_principal)],
        ["**Free Cash Flow (FCF)**", "**${:,.2f}**".format(cf_fcf)],
    ]
    st.dataframe(
        pd.DataFrame(cf_data, columns=["Metric", "Amount"]),
        hide_index=True, use_container_width=True,
    )

    st.metric("DSCR", "{:.2f}x".format(cf_dscr))
    st.metric("Loan Balance", "${:,.2f}".format(loan_balance))
    st.metric(
        "Total Principal Paid",
        "${:,.2f}".format(get_total_principal_paid(amort_schedule, as_of_date))
    )
