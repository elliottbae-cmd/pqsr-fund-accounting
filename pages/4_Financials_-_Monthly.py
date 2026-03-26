"""Page 4: Financials - Monthly — side-by-side month columns for BS, IS, and Cash Flow."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from database.db import (
    get_posted_periods, load_all_balance_sheets, load_all_income_statements,
    load_all_cash_flows, load_all_totals,
)
from config.fund_config import FUND_NAME, INVESTORS, FIXED_ASSETS
from config.baseline_data import BALANCE_SHEET, INCOME_STATEMENT_2025
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_section_header, styled_divider, format_currency

inject_custom_css()
show_sidebar_branding()
styled_page_header("Financials - Monthly", "Side-by-Side Monthly Comparison")

posted = get_posted_periods()
if not posted:
    st.info("No periods posted yet. Upload and process bank data to see monthly financials.")
    st.stop()

# Load all snapshots
all_bs = load_all_balance_sheets()
all_is = load_all_income_statements()
all_cf = load_all_cash_flows()
all_totals = load_all_totals()

# Build sorted period list
period_keys = sorted(all_bs.keys())

if not period_keys:
    st.info("No financial data available yet.")
    st.stop()

# Year filter
years = sorted(set(date.fromisoformat(pk).year for pk in period_keys))
selected_year = st.selectbox("Year", years, index=len(years) - 1)

# Filter to selected year
year_periods = [
    pk for pk in period_keys
    if date.fromisoformat(pk).year == selected_year
]

if not year_periods:
    st.info("No data for {}.".format(selected_year))
    st.stop()

# Build month labels
month_labels = []
for pk in year_periods:
    pd_obj = date.fromisoformat(pk)
    month_labels.append(pd_obj.strftime("%b '%y"))


def _fmt(v):
    """Format a value for display."""
    if v is None or v == 0:
        return "-"
    if v < 0:
        return "$({:,.2f})".format(abs(v))
    return "${:,.2f}".format(v)


def _compute_monthly_delta_is(period_keys_list, all_is_data, baseline_is):
    """Compute per-month IS deltas from cumulative snapshots.

    Each month's column = that month's cumulative IS minus the prior month's.
    First month's delta = cumulative IS minus baseline (12/31/2025).
    """
    deltas = []
    for i, pk in enumerate(period_keys_list):
        current = all_is_data.get(pk, {})
        if i == 0:
            # Delta from baseline
            prior = baseline_is
        else:
            prior = all_is_data.get(period_keys_list[i - 1], {})

        delta = {}
        all_accounts = set(list(current.keys()) + list(prior.keys()))
        for acct in all_accounts:
            delta[acct] = current.get(acct, 0) - prior.get(acct, 0)
        deltas.append(delta)
    return deltas


def _compute_monthly_delta_bs(period_keys_list, all_bs_data, baseline_bs):
    """Compute per-month BS deltas (change from prior month)."""
    deltas = []
    for i, pk in enumerate(period_keys_list):
        current = all_bs_data.get(pk, {})
        if i == 0:
            prior = baseline_bs
        else:
            prior = all_bs_data.get(period_keys_list[i - 1], {})

        delta = {}
        all_accounts = set(list(current.keys()) + list(prior.keys()))
        for acct in all_accounts:
            delta[acct] = current.get(acct, 0) - prior.get(acct, 0)
        deltas.append(delta)
    return deltas


# Compute monthly deltas
monthly_is_deltas = _compute_monthly_delta_is(year_periods, all_is, INCOME_STATEMENT_2025)

# Tabs
tab_bs, tab_is, tab_cf = st.tabs(["Balance Sheet", "Income Statement", "Cash Flow"])

# ==================== BALANCE SHEET - Monthly Snapshots ====================
with tab_bs:
    st.markdown("### {} | Balance Sheet - Monthly | {}".format(FUND_NAME, selected_year))

    # BS accounts in display order
    bs_sections = [
        ("**ASSETS**", None),
        ("Cash", "Cash"),
        ("", None),
        ("**FIXED ASSETS**", None),
        ("Land", "Land"),
        ("Building", "Building"),
        ("Land Improvements", "Land Improvements"),
        ("Furniture & Fixtures", "F&F"),
        ("Equipment", "Equipment"),
        ("Signage", "Signage"),
        ("Building - A/D", "Building A/D"),
        ("Land Improvements - A/D", "Land Improvements A/D"),
        ("F&F - A/D", "F&F A/D"),
        ("Equipment - A/D", "Equipment A/D"),
        ("Signage - A/D", "Signage A/D"),
        ("", None),
        ("**OTHER ASSETS**", None),
        ("Capitalized Origination Fee", "Capitalized Origination Fee"),
        ("Accumulated Amortization", "Accumulated Amortization"),
        ("", None),
        ("**LIABILITIES**", None),
        ("Note Payable - BBV", "Note Payable - BBV"),
        ("Due to PSP Investments, LLC", "Due to PSP Investments, LLC"),
        ("", None),
        ("**MEMBERS' EQUITY**", None),
    ]
    for inv_key in INVESTORS:
        bs_sections.append(
            ("Contributions - {}".format(inv_key),
             "Contributions - {}".format(inv_key))
        )
    for inv_key in INVESTORS:
        bs_sections.append(
            ("Distributions - {}".format(inv_key),
             "Distributions - {}".format(inv_key))
        )
    bs_sections.extend([
        ("CY Net Income", "CY Net Income"),
        ("Retained Earnings", "Retained Earnings"),
    ])

    rows = []
    for label, acct_key in bs_sections:
        row = {"Account": label}
        # Baseline column
        if acct_key:
            row["12/31/2025"] = _fmt(BALANCE_SHEET.get(acct_key, 0))
        else:
            row["12/31/2025"] = ""
        # Monthly columns
        for i, pk in enumerate(year_periods):
            col_label = month_labels[i]
            if acct_key:
                row[col_label] = _fmt(all_bs.get(pk, {}).get(acct_key, 0))
            else:
                row[col_label] = ""
        rows.append(row)

    # Add total rows
    for total_label, total_key in [
        ("**Total Assets**", "total_assets"),
        ("**Total Liabilities**", "total_liabilities"),
        ("**Total Equity**", "total_equity"),
        ("**Total L + E**", "total_liabilities_equity"),
    ]:
        row = {"Account": total_label, "12/31/2025": ""}
        for i, pk in enumerate(year_periods):
            col_label = month_labels[i]
            row[col_label] = _fmt(all_totals.get(pk, {}).get(total_key, 0))
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=800)


# ==================== INCOME STATEMENT - Monthly Activity ====================
with tab_is:
    st.markdown(
        "### {} | Income Statement - Monthly Activity | {}".format(
            FUND_NAME, selected_year
        )
    )
    st.caption("Each column shows that month's activity only (not cumulative).")

    is_accounts_order = [
        ("**REVENUE**", None),
        ("Rental Income", "Rental Income"),
        ("", None),
        ("**EXPENSES**", None),
        ("Interest Expense", "Interest Expense"),
        ("Appraisals", "Appraisals"),
        ("Accounting & Tax Fees", "Accounting & Tax Fees"),
        ("Bank Fees", "Bank Fees"),
        ("Taxes & Licenses", "Taxes & Licenses"),
        ("Survey Fees", "Survey Fees"),
        ("Origination Fee - Amort", "Origination Fee - Amort"),
        ("Depreciation Expense", "Depreciation Expense"),
    ]

    is_rows = []
    for label, acct_key in is_accounts_order:
        row = {"Account": label}
        for i, pk in enumerate(year_periods):
            col_label = month_labels[i]
            if acct_key:
                row[col_label] = _fmt(monthly_is_deltas[i].get(acct_key, 0))
            else:
                row[col_label] = ""
        is_rows.append(row)

    # Total Expenses row
    row = {"Account": "**Total Expenses**"}
    for i, pk in enumerate(year_periods):
        col_label = month_labels[i]
        total_exp = sum(
            monthly_is_deltas[i].get(k, 0) for k in monthly_is_deltas[i]
            if k != "Rental Income"
        )
        row[col_label] = _fmt(total_exp)
    is_rows.append(row)

    # Net Income row
    row = {"Account": "**Net Income**"}
    for i, pk in enumerate(year_periods):
        col_label = month_labels[i]
        revenue = monthly_is_deltas[i].get("Rental Income", 0)
        total_exp = sum(
            monthly_is_deltas[i].get(k, 0) for k in monthly_is_deltas[i]
            if k != "Rental Income"
        )
        row[col_label] = _fmt(revenue - total_exp)
    is_rows.append(row)

    # YTD row
    row = {"Account": "**YTD Net Income**"}
    for i, pk in enumerate(year_periods):
        col_label = month_labels[i]
        cumulative_is = all_is.get(pk, {})
        ytd_revenue = cumulative_is.get("Rental Income", 0)
        ytd_exp = sum(cumulative_is.get(k, 0) for k in cumulative_is if k != "Rental Income")
        row[col_label] = _fmt(ytd_revenue - ytd_exp)
    is_rows.append(row)

    st.dataframe(pd.DataFrame(is_rows), hide_index=True, use_container_width=True, height=600)


# ==================== CASH FLOW - Monthly ====================
with tab_cf:
    st.markdown(
        "### {} | Cash Flow - Monthly | {}".format(FUND_NAME, selected_year)
    )
    st.caption("Cash flow metrics are cumulative through the quarter containing each month.")

    cf_metrics = ["EBITDA", "Interest Expense", "Principal Payments", "FCF", "DSCR"]
    cf_rows = []
    for metric in cf_metrics:
        row = {"Metric": metric}
        for i, pk in enumerate(year_periods):
            col_label = month_labels[i]
            val = all_cf.get(pk, {}).get(metric, 0)
            if metric == "DSCR":
                row[col_label] = "{:.4f}x".format(val) if val else "-"
            elif metric in ("Interest Expense", "Principal Payments"):
                row[col_label] = _fmt(val)
            else:
                row[col_label] = _fmt(val)
        cf_rows.append(row)

    st.dataframe(pd.DataFrame(cf_rows), hide_index=True, use_container_width=True)
