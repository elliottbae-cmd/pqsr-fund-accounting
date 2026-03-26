"""Page 5: Financials - Quarterly — Q1-Q4 sub-reports with partial quarter support."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from database.db import (
    get_posted_periods, load_all_balance_sheets, load_all_income_statements,
    load_all_cash_flows, load_all_totals, load_all_distributions,
)
from config.fund_config import (
    FUND_NAME, INVESTORS, INVESTOR_REPORT_NAMES, FIXED_ASSETS, LOAN,
)
from config.baseline_data import BALANCE_SHEET, INCOME_STATEMENT_2025, CASH_FLOW_2025
from engine.loan_amortization import (
    generate_amortization_schedule, get_ending_balance_at_date,
    get_payments_for_quarter,
)
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_section_header, styled_divider, format_currency
from reports.excel_export import export_quarterly_financials

inject_custom_css()
show_sidebar_branding()
styled_page_header("Financials - Quarterly", "Q1-Q4 Period Reports")

posted = get_posted_periods()
if not posted:
    st.info("No periods posted yet. Upload and process bank data first.")
    st.stop()

# Load all data
all_bs = load_all_balance_sheets()
all_is = load_all_income_statements()
all_cf = load_all_cash_flows()
all_totals = load_all_totals()

period_keys = sorted(all_bs.keys())
if not period_keys:
    st.info("No financial data available yet.")
    st.stop()

# Year filter
years = sorted(set(date.fromisoformat(pk).year for pk in period_keys))
selected_year = st.selectbox("Year", years, index=len(years) - 1)

# Group periods by quarter
QUARTER_MONTHS = {
    1: [1, 2, 3],
    2: [4, 5, 6],
    3: [7, 8, 9],
    4: [10, 11, 12],
}

quarter_data = {}  # {1: {"periods": [...], "last_period": "..."}, ...}
for pk in period_keys:
    pd_obj = date.fromisoformat(pk)
    if pd_obj.year != selected_year:
        continue
    q = (pd_obj.month - 1) // 3 + 1
    if q not in quarter_data:
        quarter_data[q] = {"periods": [], "months_posted": []}
    quarter_data[q]["periods"].append(pk)
    quarter_data[q]["months_posted"].append(pd_obj.strftime("%b"))

if not quarter_data:
    st.info("No data for {}.".format(selected_year))
    st.stop()

# Baseline IS for computing deltas
baseline_is = INCOME_STATEMENT_2025


def _fmt(v):
    if v is None or v == 0:
        return "-"
    if v < 0:
        return "$({:,.2f})".format(abs(v))
    return "${:,.2f}".format(v)


def _get_quarter_end_period(qtr_periods):
    """Get the last posted period in a quarter (used for BS snapshot)."""
    return max(qtr_periods)


def _get_prior_quarter_end(quarter_num, year_val, all_period_keys):
    """Get the last period of the prior quarter, or None for Q1."""
    if quarter_num == 1:
        # Prior is 12/31 of prior year, or baseline
        prior_year_periods = [
            pk for pk in all_period_keys
            if date.fromisoformat(pk).year == year_val - 1
        ]
        if prior_year_periods:
            return max(prior_year_periods)
        return None  # Use baseline
    else:
        # Prior quarter's last month
        prior_q = quarter_num - 1
        prior_months = QUARTER_MONTHS[prior_q]
        candidates = [
            pk for pk in all_period_keys
            if date.fromisoformat(pk).year == year_val
            and date.fromisoformat(pk).month in prior_months
        ]
        if candidates:
            return max(candidates)
        # Fallback: use prior year's last posted period
        prior_year_periods = [
            pk for pk in all_period_keys
            if date.fromisoformat(pk).year == year_val - 1
        ]
        if prior_year_periods:
            return max(prior_year_periods)
        return None  # Use baseline


def _compute_quarter_is_delta(qtr_end_pk, prior_pk, all_is_data, baseline):
    """Compute the IS activity for a quarter = end cumulative - prior cumulative."""
    current = all_is_data.get(qtr_end_pk, {})
    if prior_pk:
        prior = all_is_data.get(prior_pk, {})
    else:
        prior = baseline

    delta = {}
    all_accounts = set(list(current.keys()) + list(prior.keys()))
    for acct in all_accounts:
        delta[acct] = current.get(acct, 0) - prior.get(acct, 0)
    return delta


# Build quarter export data and Excel export — above tabs
amort_schedule = generate_amortization_schedule()

quarter_exports = []
for q_num_exp in range(1, 5):
    if q_num_exp not in quarter_data:
        continue
    qd_exp = quarter_data[q_num_exp]
    qtr_end_pk_exp = max(qd_exp["periods"])
    prior_pk_exp = _get_prior_quarter_end(q_num_exp, selected_year, period_keys)
    qtr_end_date_obj_exp = date.fromisoformat(qtr_end_pk_exp)
    qtr_end_dt_exp = date(
        qtr_end_date_obj_exp.year, qtr_end_date_obj_exp.month,
        monthrange(qtr_end_date_obj_exp.year, qtr_end_date_obj_exp.month)[1]
    )
    is_delta_exp = _compute_quarter_is_delta(qtr_end_pk_exp, prior_pk_exp, all_is, baseline_is)
    if prior_pk_exp:
        bs_prior_exp = all_bs.get(prior_pk_exp, {})
        prior_lbl_exp = date.fromisoformat(prior_pk_exp).strftime("%m/%d/%Y")
    else:
        bs_prior_exp = BALANCE_SHEET
        prior_lbl_exp = "12/31/2025"
    quarter_exports.append({
        "q_num": q_num_exp,
        "months_posted": qd_exp["months_posted"],
        "is_complete": len(qd_exp["periods"]) == 3,
        "bs_end": all_bs.get(qtr_end_pk_exp, {}),
        "totals_end": all_totals.get(qtr_end_pk_exp, {}),
        "is_delta": is_delta_exp,
        "cf_end": all_cf.get(qtr_end_pk_exp, {}),
        "prior_label": prior_lbl_exp,
        "end_label": qtr_end_dt_exp.strftime("%m/%d/%Y"),
        "bs_prior": bs_prior_exp,
    })

if quarter_exports:
    excel_buffer = export_quarterly_financials(
        quarter_exports=quarter_exports,
        fund_name=FUND_NAME,
        selected_year=selected_year,
    )
    st.download_button(
        label="Export to Excel",
        data=excel_buffer,
        file_name="PQSR_Financials_Quarterly_{}.xlsx".format(selected_year),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    styled_divider()

# Create Q1-Q4 tabs
tab_labels = []
for q in range(1, 5):
    if q in quarter_data:
        months = ", ".join(quarter_data[q]["months_posted"])
        complete = len(quarter_data[q]["periods"]) == 3
        status = "Complete" if complete else "Partial"
        tab_labels.append("Q{} ({} - {})".format(q, months, status))
    else:
        tab_labels.append("Q{} (No Data)".format(q))

tabs = st.tabs(tab_labels)

for q_idx, q_num in enumerate(range(1, 5)):
    with tabs[q_idx]:
        if q_num not in quarter_data:
            st.info("No data posted for Q{} {}.".format(q_num, selected_year))
            continue

        qd = quarter_data[q_num]
        qtr_end_pk = _get_quarter_end_period(qd["periods"])
        prior_pk = _get_prior_quarter_end(q_num, selected_year, period_keys)
        is_complete = len(qd["periods"]) == 3

        qtr_end_date_obj = date.fromisoformat(qtr_end_pk)
        qtr_end_date = date(
            qtr_end_date_obj.year, qtr_end_date_obj.month,
            monthrange(qtr_end_date_obj.year, qtr_end_date_obj.month)[1]
        )

        # Status banner
        if is_complete:
            st.success(
                "Q{} {} — Complete ({})".format(
                    q_num, selected_year,
                    ", ".join(qd["months_posted"])
                )
            )
        else:
            st.warning(
                "Q{} {} — Partial ({} of 3 months: {})".format(
                    q_num, selected_year, len(qd["periods"]),
                    ", ".join(qd["months_posted"])
                )
            )

        # Get snapshots
        bs_end = all_bs.get(qtr_end_pk, {})
        totals_end = all_totals.get(qtr_end_pk, {})
        cf_end = all_cf.get(qtr_end_pk, {})

        # IS delta for the quarter
        is_delta = _compute_quarter_is_delta(
            qtr_end_pk, prior_pk, all_is, baseline_is
        )

        # Prior BS for comparison
        if prior_pk:
            bs_prior = all_bs.get(prior_pk, {})
        else:
            bs_prior = BALANCE_SHEET

        prior_label = (
            date.fromisoformat(prior_pk).strftime("%m/%d/%Y") if prior_pk
            else "12/31/2025"
        )
        end_label = qtr_end_date.strftime("%m/%d/%Y")

        # Sub-tabs for each report
        sub_bs, sub_is, sub_cf, sub_dist = st.tabs([
            "Balance Sheet", "Income Statement", "Cash Flow", "Distributions"
        ])

        # ---------- Balance Sheet ----------
        with sub_bs:
            st.markdown(
                "**{} | Balance Sheet | Q{} {} (as of {})**".format(
                    FUND_NAME, q_num, selected_year, end_label
                )
            )

            bs_accounts = [
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
                bs_accounts.append((
                    "Contributions - {}".format(inv_key),
                    "Contributions - {}".format(inv_key),
                ))
            for inv_key in INVESTORS:
                bs_accounts.append((
                    "Distributions - {}".format(inv_key),
                    "Distributions - {}".format(inv_key),
                ))
            bs_accounts.extend([
                ("CY Net Income", "CY Net Income"),
                ("Retained Earnings", "Retained Earnings"),
            ])

            bs_rows = []
            for label, acct_key in bs_accounts:
                row = {"Account": label}
                if acct_key:
                    prior_val = bs_prior.get(acct_key, 0)
                    end_val = bs_end.get(acct_key, 0)
                    row[prior_label] = _fmt(prior_val)
                    row[end_label] = _fmt(end_val)
                    row["Change"] = _fmt(end_val - prior_val)
                else:
                    row[prior_label] = ""
                    row[end_label] = ""
                    row["Change"] = ""
                bs_rows.append(row)

            # Totals
            for total_label, total_key in [
                ("**Total Assets**", "total_assets"),
                ("**Total Liabilities**", "total_liabilities"),
                ("**Total Equity**", "total_equity"),
                ("**Total L + E**", "total_liabilities_equity"),
            ]:
                row = {"Account": total_label}
                end_val = totals_end.get(total_key, 0)
                row[prior_label] = ""
                row[end_label] = _fmt(end_val)
                row["Change"] = ""
                bs_rows.append(row)

            st.dataframe(
                pd.DataFrame(bs_rows),
                hide_index=True, use_container_width=True, height=700,
            )

            # Balance check
            diff = abs(
                totals_end.get("total_assets", 0)
                - totals_end.get("total_liabilities_equity", 0)
            )
            if diff < 0.02:
                st.success("Balance Sheet is in balance.")
            else:
                st.error("OUT OF BALANCE by ${:,.2f}".format(diff))

        # ---------- Income Statement ----------
        with sub_is:
            st.markdown(
                "**{} | Income Statement | Q{} {} Activity**".format(
                    FUND_NAME, q_num, selected_year
                )
            )
            if not is_complete:
                st.caption(
                    "Partial quarter: showing combined activity for {}.".format(
                        ", ".join(qd["months_posted"])
                    )
                )

            is_order = [
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
            for label, acct_key in is_order:
                row = {"Account": label}
                if acct_key:
                    row["Q{} Activity".format(q_num)] = _fmt(
                        is_delta.get(acct_key, 0)
                    )
                else:
                    row["Q{} Activity".format(q_num)] = ""
                is_rows.append(row)

            # Total Expenses
            total_exp = sum(
                is_delta.get(k, 0) for k in is_delta if k != "Rental Income"
            )
            is_rows.append({
                "Account": "**Total Expenses**",
                "Q{} Activity".format(q_num): _fmt(total_exp),
            })

            # Net Income
            net_inc = is_delta.get("Rental Income", 0) - total_exp
            is_rows.append({
                "Account": "**Net Income**",
                "Q{} Activity".format(q_num): _fmt(net_inc),
            })

            st.dataframe(
                pd.DataFrame(is_rows),
                hide_index=True, use_container_width=True,
            )

        # ---------- Cash Flow ----------
        with sub_cf:
            st.markdown(
                "**{} | Cash Flow | Q{} {}**".format(
                    FUND_NAME, q_num, selected_year
                )
            )

            # Use the quarter-end cash flow snapshot
            ebitda = cf_end.get("EBITDA", 0)
            interest = cf_end.get("Interest Expense", 0)
            principal = cf_end.get("Principal Payments", 0)
            fcf = cf_end.get("FCF", 0)
            dscr = cf_end.get("DSCR", 0)

            cf_rows = [
                {"Metric": "EBITDA", "Amount": _fmt(ebitda)},
                {"Metric": "Less: Interest Expense", "Amount": _fmt(interest)},
                {"Metric": "Less: Principal Payments", "Amount": _fmt(principal)},
                {"Metric": "**Free Cash Flow (FCF)**", "Amount": "**{}**".format(_fmt(fcf))},
            ]
            st.dataframe(
                pd.DataFrame(cf_rows),
                hide_index=True, use_container_width=True,
            )

            col1, col2 = st.columns(2)
            col1.metric("DSCR", "{:.4f}x".format(dscr) if dscr else "-")

            loan_bal = get_ending_balance_at_date(amort_schedule, qtr_end_date)
            col2.metric("Loan Balance", "${:,.2f}".format(loan_bal))

        # ---------- Distributions ----------
        with sub_dist:
            st.markdown(
                "**{} | Distributions | Q{} {}**".format(
                    FUND_NAME, q_num, selected_year
                )
            )

            if not is_complete:
                st.info(
                    "Distributions are calculated at quarter-end. "
                    "Q{} is not yet complete.".format(q_num)
                )

            # Show projected/actual distributions
            rental_income = is_delta.get("Rental Income", 0)
            quarterly_payments = get_payments_for_quarter(
                amort_schedule, selected_year, q_num
            )
            total_loan = sum(p["payment"] for p in quarterly_payments)

            distributable = rental_income - total_loan
            if distributable < 0:
                distributable = 0

            status_label = "Actual" if is_complete else "Projected"
            st.markdown("##### {} Distribution — Q{} {}".format(
                status_label, q_num, selected_year
            ))

            dist_rows = []
            for inv_key, inv in INVESTORS.items():
                inv_dist = distributable * inv["ownership_pct"]
                dist_rows.append({
                    "Investor": inv["full_name"],
                    "Ownership %": "{:.2%}".format(inv["ownership_pct"]),
                    "Distribution": "${:,.2f}".format(inv_dist),
                })
            dist_rows.append({
                "Investor": "**Total**",
                "Ownership %": "100.00%",
                "Distribution": "**${:,.2f}**".format(distributable),
            })
            st.dataframe(
                pd.DataFrame(dist_rows),
                hide_index=True, use_container_width=True,
            )


# ==================== Cross-Quarter Summary ====================
st.markdown("---")
st.markdown("### {} Year Summary".format(selected_year))

summary_rows = []
for q_num in range(1, 5):
    if q_num not in quarter_data:
        summary_rows.append({
            "Quarter": "Q{}".format(q_num),
            "Status": "No Data",
            "Months Posted": "-",
            "Rental Income": "-",
            "Net Income": "-",
            "FCF": "-",
            "DSCR": "-",
        })
        continue

    qd = quarter_data[q_num]
    qtr_end_pk = _get_quarter_end_period(qd["periods"])
    prior_pk = _get_prior_quarter_end(q_num, selected_year, period_keys)
    is_delta = _compute_quarter_is_delta(qtr_end_pk, prior_pk, all_is, baseline_is)
    cf_qtr = all_cf.get(qtr_end_pk, {})

    total_exp = sum(is_delta.get(k, 0) for k in is_delta if k != "Rental Income")
    net_inc = is_delta.get("Rental Income", 0) - total_exp

    is_complete = len(qd["periods"]) == 3

    summary_rows.append({
        "Quarter": "Q{}".format(q_num),
        "Status": "Complete" if is_complete else "Partial ({}/3)".format(
            len(qd["periods"])
        ),
        "Months Posted": ", ".join(qd["months_posted"]),
        "Rental Income": _fmt(is_delta.get("Rental Income", 0)),
        "Net Income": _fmt(net_inc),
        "FCF": _fmt(cf_qtr.get("FCF", 0)),
        "DSCR": "{:.4f}x".format(cf_qtr.get("DSCR", 0)) if cf_qtr.get("DSCR") else "-",
    })

st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)
