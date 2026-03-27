"""Page 8: Financial History — mirrors the Excel workbook layout with roll-forward columns."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from database.db import (
    get_posted_periods, load_balance_sheet, load_income_statement,
    load_cash_flow, load_totals, load_journal_entries, load_transactions,
    load_all_distributions,
)
from config.fund_config import (
    FUND_NAME, INVESTORS, INVESTOR_REPORT_NAMES, FIXED_ASSETS,
    LOAN, DISTRIBUTION_HISTORY,
)
from config.baseline_data import (
    BALANCE_SHEET, INCOME_STATEMENT_2025, CASH_FLOW_2025, QUARTERLY_NOI,
    TOTAL_DISTRIBUTIONS_THROUGH_BASELINE,
)
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_section_header, styled_divider, format_currency

inject_custom_css()
show_sidebar_branding()
styled_page_header("Financial History", "Full Workbook-Style Period Views")

posted = get_posted_periods()
if not posted:
    st.info("No periods have been posted yet. Process bank data to build history.")
    st.stop()

# Build available period-end dates
period_dates = []
for p in posted:
    pd_obj = date.fromisoformat(p["period_date"])
    last_day = date(pd_obj.year, pd_obj.month,
                    monthrange(pd_obj.year, pd_obj.month)[1])
    period_dates.append((pd_obj, last_day, p))

# Period selector
period_labels = [
    "{} ({})".format(
        pd_obj.strftime("%B %Y"),
        "Quarter End" if p["quarter_end"] else "Month End"
    )
    for pd_obj, _, p in period_dates
]
period_labels.reverse()
period_dates_rev = list(reversed(period_dates))

selected_idx = st.selectbox(
    "Select Period to View",
    range(len(period_labels)),
    format_func=lambda i: period_labels[i],
)
selected_period, selected_end, selected_meta = period_dates_rev[selected_idx]

# Load core data (cached by db.py)
bs = load_balance_sheet(selected_period)
is_accounts = load_income_statement(selected_period)
cf = load_cash_flow(selected_period)
totals = load_totals(selected_period)

if not bs:
    st.warning("No data found for this period.")
    st.stop()

# Excel Export — LAZY: only generate when button is clicked
def _generate_excel():
    """Generate Excel only on demand."""
    from engine.loan_amortization import generate_amortization_schedule, get_ending_balance_at_date
    from reports.excel_export import export_financial_history
    amort_sched = generate_amortization_schedule()
    loan_bal = get_ending_balance_at_date(amort_sched, selected_end)
    ajes_for_export = load_journal_entries(selected_period)
    txns_for_export = load_transactions(selected_period)
    return export_financial_history(
        bs=bs, is_accounts=is_accounts, cf=cf, totals=totals,
        ajes=ajes_for_export, txns=txns_for_export,
        baseline_bs=BALANCE_SHEET, baseline_is=INCOME_STATEMENT_2025,
        baseline_cf=CASH_FLOW_2025, selected_end=selected_end,
        fund_name=FUND_NAME, investors=INVESTORS,
        investor_report_names=INVESTOR_REPORT_NAMES,
        distribution_history=DISTRIBUTION_HISTORY,
        db_dists=load_all_distributions(),
        amort_schedule=amort_sched, loan_balance=loan_bal,
    )

if st.button("Export to Excel"):
    with st.spinner("Generating Excel..."):
        excel_buffer = _generate_excel()
        st.download_button(
            label="Download Excel",
            data=excel_buffer,
            file_name="PQSR_Financial_History_{}.xlsx".format(selected_end.strftime("%m_%d_%Y")),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

styled_divider()

# Tab layout matching Excel workbook sheets
tabs = st.tabs([
    "BS (Consolidated)",
    "IS (Consolidated)",
    "AJEs",
    "Bank Activity",
    "Loan Amortization",
    "Fixed Asset Schedule",
    "Distributions",
    "Investor Summary",
])


def _fmt_val(v):
    if v is None or v == 0:
        return "-"
    if v < 0:
        return "$({:,.2f})".format(abs(v))
    return "${:,.2f}".format(v)


# ==================== BS_CONS ====================
with tabs[0]:
    st.markdown(
        "### {} | Balance Sheet | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    baseline = BALANCE_SHEET

    bs_rows = []
    accounts = [
        ("ASSETS", None),
        ("Cash", "Cash"),
        ("", None),
        ("FIXED ASSETS", None),
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
        ("**Total Fixed Assets (Net)**", None),
        ("", None),
        ("OTHER ASSETS", None),
        ("Capitalized Origination Fee", "Capitalized Origination Fee"),
        ("Accumulated Amortization", "Accumulated Amortization"),
        ("**Total Other Assets**", None),
        ("", None),
        ("**Total Assets**", None),
        ("", None),
        ("LIABILITIES", None),
        ("Note Payable - BBV", "Note Payable - BBV"),
        ("Due to PSP Investments, LLC", "Due to PSP Investments, LLC"),
        ("Deferred Rental Revenue", "Deferred Rental Revenue"),
        ("**Total Liabilities**", None),
        ("", None),
        ("MEMBERS' EQUITY", None),
    ]

    for inv_key in INVESTORS:
        accounts.append(
            ("Contributions - {}".format(inv_key),
             "Contributions - {}".format(inv_key))
        )
    for inv_key in INVESTORS:
        accounts.append(
            ("Distributions - {}".format(inv_key),
             "Distributions - {}".format(inv_key))
        )
    accounts.extend([
        ("CY Net Income", "CY Net Income"),
        ("Retained Earnings", "Retained Earnings"),
        ("**Total Equity**", None),
        ("", None),
        ("**Total Liabilities / Equity**", None),
    ])

    # Pre-compute baseline totals once
    fa_keys = ["Land", "Building", "Land Improvements", "F&F", "Equipment", "Signage",
               "Building A/D", "Land Improvements A/D", "F&F A/D", "Equipment A/D", "Signage A/D"]
    liab_keys = ["Note Payable - BBV", "Due to PSP Investments, LLC", "Deferred Rental Revenue"]
    fa_beg = sum(baseline.get(k, 0) for k in fa_keys)
    oa_beg = baseline.get("Capitalized Origination Fee", 0) + baseline.get("Accumulated Amortization", 0)
    ta_beg = baseline.get("Cash", 0) + fa_beg + oa_beg
    tl_beg = sum(baseline.get(k, 0) for k in liab_keys)
    te_beg = (
        sum(baseline.get("Contributions - {}".format(k), 0) for k in INVESTORS)
        + sum(baseline.get("Distributions - {}".format(k), 0) for k in INVESTORS)
        + baseline.get("CY Net Income", 0) + baseline.get("Retained Earnings", 0)
    )
    tle_beg = tl_beg + te_beg

    computed_totals = {
        "**Total Fixed Assets (Net)**": (fa_beg, totals.get("total_fa_net", 0)),
        "**Total Other Assets**": (oa_beg, totals.get("total_other_assets", 0)),
        "**Total Assets**": (ta_beg, totals.get("total_assets", 0)),
        "**Total Liabilities**": (tl_beg, totals.get("total_liabilities", 0)),
        "**Total Equity**": (te_beg, totals.get("total_equity", 0)),
        "**Total Liabilities / Equity**": (tle_beg, totals.get("total_liabilities_equity", 0)),
    }

    end_col = selected_end.strftime("%m/%d/%Y")
    for label, acct_key in accounts:
        if acct_key:
            beg = baseline.get(acct_key, 0)
            end = bs.get(acct_key, 0)
            bs_rows.append({"Account": label, "12/31/2025": _fmt_val(beg), end_col: _fmt_val(end), "Change": _fmt_val(end - beg)})
        elif label in computed_totals:
            beg, end = computed_totals[label]
            bs_rows.append({"Account": label, "12/31/2025": _fmt_val(beg), end_col: _fmt_val(end), "Change": _fmt_val(end - beg)})
        else:
            display = "**{}**".format(label) if label and not label.startswith("**") else label
            bs_rows.append({"Account": display, "12/31/2025": "", end_col: "", "Change": ""})

    st.dataframe(pd.DataFrame(bs_rows), hide_index=True, use_container_width=True, height=800)

    diff = abs(totals.get("total_assets", 0) - totals.get("total_liabilities_equity", 0))
    if diff < 0.02:
        st.success("Balance Sheet is in balance!")
    else:
        st.error("OUT OF BALANCE by ${:,.2f}".format(diff))


# ==================== IS_CONS ====================
with tabs[1]:
    st.markdown(
        "### {} | Income Statement | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    is_2025 = INCOME_STATEMENT_2025
    end_col = selected_end.strftime("%m/%d/%Y")
    is_rows = [
        {"Account": "**REVENUE**", "12/31/2025": "", end_col: "", "Change": ""},
        {
            "Account": "Rental Income",
            "12/31/2025": _fmt_val(is_2025.get("Rental Income", 0)),
            end_col: _fmt_val(is_accounts.get("Rental Income", 0)),
            "Change": _fmt_val(is_accounts.get("Rental Income", 0) - is_2025.get("Rental Income", 0)),
        },
        {"Account": "", "12/31/2025": "", end_col: "", "Change": ""},
        {"Account": "**EXPENSES**", "12/31/2025": "", end_col: "", "Change": ""},
    ]

    for exp in ["Interest Expense", "Appraisals", "Accounting & Tax Fees",
                "Bank Fees", "Taxes & Licenses", "Survey Fees",
                "Origination Fee - Amort", "Depreciation Expense"]:
        beg = is_2025.get(exp, 0)
        end = is_accounts.get(exp, 0)
        is_rows.append({"Account": exp, "12/31/2025": _fmt_val(beg), end_col: _fmt_val(end), "Change": _fmt_val(end - beg)})

    total_exp_beg = sum(v for k, v in is_2025.items() if k != "Rental Income")
    total_exp_end = sum(is_accounts.get(k, 0) for k in is_accounts if k != "Rental Income")
    is_rows.append({"Account": "**Total Expenses**", "12/31/2025": _fmt_val(total_exp_beg), end_col: _fmt_val(total_exp_end), "Change": _fmt_val(total_exp_end - total_exp_beg)})

    ni_beg = is_2025.get("Rental Income", 0) - total_exp_beg
    ni_end = is_accounts.get("Rental Income", 0) - total_exp_end
    is_rows.append({"Account": "**Net Income**", "12/31/2025": _fmt_val(ni_beg), end_col: _fmt_val(ni_end), "Change": _fmt_val(ni_end - ni_beg)})

    is_rows.append({"Account": "", "12/31/2025": "", end_col: "", "Change": ""})
    cf_2025 = CASH_FLOW_2025
    for metric in ["EBITDA", "Interest Expense", "Principal Payments", "FCF"]:
        beg = cf_2025.get(metric, 0)
        end = cf.get(metric, 0)
        label = "Less: {}".format(metric) if metric in ("Interest Expense", "Principal Payments") else metric
        is_rows.append({"Account": label, "12/31/2025": _fmt_val(beg), end_col: _fmt_val(end), "Change": _fmt_val(end - beg)})

    dscr_beg = cf_2025.get("DSCR", 0)
    dscr_end = cf.get("DSCR", 0)
    is_rows.append({
        "Account": "**DSCR**",
        "12/31/2025": "{:.4f}x".format(dscr_beg) if dscr_beg else "-",
        end_col: "{:.4f}x".format(dscr_end) if dscr_end else "-",
        "Change": "",
    })

    st.dataframe(pd.DataFrame(is_rows), hide_index=True, use_container_width=True, height=600)


# ==================== AJEs ====================
with tabs[2]:
    st.markdown(
        "### {} | Journal Entries | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    # Lazy-load AJEs only when this tab is viewed
    ajes = load_journal_entries(selected_period)

    if not ajes:
        st.info("No journal entries for this period.")
    else:
        grand_total_dr = 0.0
        grand_total_cr = 0.0

        for i, entry in enumerate(ajes):
            edate = entry["date"].strftime("%m/%d/%Y")
            desc = entry["description"]
            entry_dr = sum(entry["debits"].values())
            entry_cr = sum(entry["credits"].values())
            grand_total_dr += entry_dr
            grand_total_cr += entry_cr

            with st.expander(
                "AJE {}: {} ({})".format(i + 1, desc, edate),
                expanded=(i < 3),
            ):
                aje_rows = []
                for acct, amt in entry["debits"].items():
                    aje_rows.append({"GL Account": acct, "Debit": "${:,.2f}".format(amt), "Credit": ""})
                for acct, amt in entry["credits"].items():
                    aje_rows.append({"GL Account": "    {}".format(acct), "Debit": "", "Credit": "${:,.2f}".format(amt)})
                aje_rows.append({"GL Account": "**Totals**", "Debit": "**${:,.2f}**".format(entry_dr), "Credit": "**${:,.2f}**".format(entry_cr)})

                st.dataframe(pd.DataFrame(aje_rows), hide_index=True, use_container_width=True)

                net = entry_dr - entry_cr
                if abs(net) < 0.01:
                    st.success("Variance: $0.00 — In Balance")
                else:
                    st.error("Variance: ${:,.2f} — OUT OF BALANCE".format(net))

        st.markdown("---")
        st.markdown("##### Period Totals")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Debits", "${:,.2f}".format(grand_total_dr))
        col2.metric("Total Credits", "${:,.2f}".format(grand_total_cr))
        grand_net = grand_total_dr - grand_total_cr
        col3.metric("Net", "${:,.2f}".format(grand_net))
        if abs(grand_net) < 0.01:
            st.success("All journal entries net to zero.")
        else:
            st.error("Period AJEs are OUT OF BALANCE by ${:,.2f}".format(grand_net))


# ==================== Bank Activity ====================
with tabs[3]:
    st.markdown(
        "### {} | Bank Activity | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    # Lazy-load transactions
    txns = load_transactions(selected_period)

    if not txns:
        st.info("No transactions for this period.")
    else:
        txn_rows = []
        for t in txns:
            txn_rows.append({
                "Date": t["post_date"][:10] if t["post_date"] else "",
                "Description": t["description"],
                "Debit": "${:,.2f}".format(t["debit"]) if t["debit"] else "",
                "Credit": "${:,.2f}".format(t["credit"]) if t["credit"] else "",
                "Category": t["details"] or t["category"] or "",
            })
        st.dataframe(pd.DataFrame(txn_rows), hide_index=True, use_container_width=True)

        total_debits = sum(t["debit"] or 0 for t in txns)
        total_credits = sum(t["credit"] or 0 for t in txns)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Debits", "${:,.2f}".format(total_debits))
        col2.metric("Total Credits", "${:,.2f}".format(total_credits))
        col3.metric("Net", "${:,.2f}".format(total_credits - total_debits))


# ==================== Loan Amortization ====================
with tabs[4]:
    st.markdown(
        "### {} | Amortization Schedule | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    # Cache amort schedule in session state to avoid recalculating
    if "amort_schedule_cache" not in st.session_state:
        from engine.loan_amortization import generate_amortization_schedule
        st.session_state.amort_schedule_cache = generate_amortization_schedule()
    amort_schedule = st.session_state.amort_schedule_cache

    from engine.loan_amortization import get_ending_balance_at_date, get_total_principal_paid

    loan_balance_amort = get_ending_balance_at_date(amort_schedule, selected_end)
    total_principal = get_total_principal_paid(amort_schedule, selected_end)
    total_interest = sum(e["interest"] for e in amort_schedule if e["payment_date"] <= selected_end)
    total_payments = sum(e["payment"] for e in amort_schedule if e["payment_date"] <= selected_end)
    payments_made = sum(1 for e in amort_schedule if e["payment_date"] <= selected_end)
    payments_remaining = len(amort_schedule) - payments_made

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Balance", "${:,.0f}".format(loan_balance_amort))
    col2.metric("Total Principal Paid", "${:,.0f}".format(total_principal))
    col3.metric("Total Interest Paid", "${:,.0f}".format(total_interest))
    col4, col5, col6 = st.columns(3)
    col4.metric("Total Payments", "${:,.0f}".format(total_payments))
    col5.metric("Payments Made", str(payments_made))
    col6.metric("Payments Remaining", str(payments_remaining))

    st.markdown("---")

    st.markdown("##### Balance Sheet Tie-Out")
    bs_note_payable = bs.get("Note Payable - BBV", 0)
    tie_diff = abs(loan_balance_amort - bs_note_payable)
    tie_col1, tie_col2, tie_col3 = st.columns(3)
    tie_col1.metric("Amort Schedule", "${:,.0f}".format(loan_balance_amort))
    tie_col2.metric("BS: Note Payable", "${:,.0f}".format(bs_note_payable))
    tie_col3.metric("Difference", "${:,.2f}".format(tie_diff))
    if tie_diff < 0.02:
        st.success("Amortization schedule ties to the Balance Sheet.")
    else:
        st.error("DOES NOT TIE — difference: ${:,.2f}".format(tie_diff))

    st.markdown("---")

    st.markdown("##### Annual Summary")
    annual_data = {}
    for entry in amort_schedule:
        yr = entry["payment_date"].year
        if yr not in annual_data:
            annual_data[yr] = {"interest": 0, "principal": 0, "total": 0}
        annual_data[yr]["interest"] += entry["interest"]
        annual_data[yr]["principal"] += entry["principal"]
        annual_data[yr]["total"] += entry["payment"]

    annual_rows = []
    for yr in sorted(annual_data.keys()):
        d = annual_data[yr]
        annual_rows.append({
            "Year": str(yr),
            "Interest": "${:,.2f}".format(d["interest"]),
            "Principal": "${:,.2f}".format(d["principal"]),
            "Total": "${:,.2f}".format(d["total"]),
            "Status": "Current" if yr == selected_end.year else (
                "Complete" if yr < selected_end.year else ""
            ),
        })
    st.dataframe(pd.DataFrame(annual_rows), hide_index=True, use_container_width=True, height=300)

    st.markdown("---")

    st.markdown("##### Monthly Detail")
    show_option = st.radio("Show payments:", ["Through current period", "Full schedule"], horizontal=True)

    amort_rows = []
    for entry in amort_schedule:
        if show_option == "Through current period" and entry["payment_date"] > selected_end:
            continue
        amort_rows.append({
            "Date": entry["payment_date"].strftime("%m/%d/%Y"),
            "Year": str(entry["payment_date"].year),
            "Beg. Bal.": "${:,.2f}".format(entry["beginning_balance"]),
            "Interest": "${:,.2f}".format(entry["interest"]),
            "Principal": "${:,.2f}".format(entry["principal"]),
            "Payment": "${:,.2f}".format(entry["payment"]),
            "End. Bal.": "${:,.2f}".format(entry["ending_balance"]),
            "Status": "Paid" if entry["payment_date"] <= selected_end else "",
        })

    if amort_rows:
        st.dataframe(pd.DataFrame(amort_rows), hide_index=True, use_container_width=True, height=500)


# ==================== Fixed Asset Schedule ====================
with tabs[5]:
    st.markdown(
        "### {} | Fixed Asset Schedule | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    from engine.depreciation import generate_fa_schedule
    fa_data = generate_fa_schedule(selected_end)
    years = fa_data["years"]
    year_labels = ["12/31/{}".format(y) for y in years]

    styled_section_header("Depreciation Expense")
    st.markdown("**Total Purchase Price: ${:,.2f}**".format(fa_data["total_purchase_price"]))

    depr_rows = []
    yearly_totals = {y: 0 for y in years}
    for ac in fa_data["asset_classes"]:
        row = {
            "Class": ac["class"],
            "Cost Seg %": "{:.2%}".format(ac["cost_seg_pct"]),
            "Amount": "${:,.2f}".format(ac["amount"]),
            "Useful Life": str(ac["useful_life"]) if ac["useful_life"] != "N/A" else "N/A",
        }
        for y in years:
            depr_val = fa_data["depreciation_by_year"].get(y, {}).get(ac["class"], 0)
            row["12/31/{}".format(y)] = "${:,.2f}".format(depr_val) if depr_val else "-"
            yearly_totals[y] += depr_val
        depr_rows.append(row)

    total_row = {"Class": "Total", "Cost Seg %": "100.00%", "Amount": "${:,.2f}".format(fa_data["total_purchase_price"]), "Useful Life": ""}
    for y in years:
        total_row["12/31/{}".format(y)] = "${:,.2f}".format(yearly_totals[y])
    depr_rows.append(total_row)
    st.dataframe(pd.DataFrame(depr_rows), hide_index=True, use_container_width=True)

    styled_divider()
    styled_section_header("Accumulated Depreciation")

    ad_rows = []
    ad_yearly_totals = {y: 0 for y in years}
    for ac in fa_data["asset_classes"]:
        row = {"Class": ac["class"]}
        for y in years:
            ad_val = fa_data["accum_depr_by_year"].get(y, {}).get(ac["class"], 0)
            row["12/31/{}".format(y)] = "$({:,.2f})".format(ad_val) if ad_val else "-"
            ad_yearly_totals[y] += ad_val
        ad_rows.append(row)

    ad_total_row = {"Class": "Total A/D"}
    for y in years:
        ad_total_row["12/31/{}".format(y)] = "$({:,.2f})".format(ad_yearly_totals[y])
    ad_rows.append(ad_total_row)
    st.dataframe(pd.DataFrame(ad_rows), hide_index=True, use_container_width=True)

    styled_divider()
    styled_section_header("Net Book Value & Balance Sheet Tie-Out")

    summary_rows = []
    total_cost = 0
    total_ad = 0
    total_nbv = 0
    for s in fa_data["summary"]:
        summary_rows.append({
            "Asset Class": s["class"],
            "Cost Basis": "${:,.2f}".format(s["amount"]),
            "Accum. Depr.": "$({:,.2f})".format(s["current_ad"]) if s["current_ad"] else "-",
            "Net Book Value": "${:,.2f}".format(s["nbv"]),
        })
        total_cost += s["amount"]
        total_ad += s["current_ad"]
        total_nbv += s["nbv"]

    summary_rows.append({
        "Asset Class": "Total",
        "Cost Basis": "${:,.2f}".format(total_cost),
        "Accum. Depr.": "$({:,.2f})".format(total_ad),
        "Net Book Value": "${:,.2f}".format(total_nbv),
    })
    st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

    bs_fa_net = totals.get("total_fa_net", 0)
    fa_diff = abs(bs_fa_net - total_nbv)
    col1, col2, col3 = st.columns(3)
    col1.metric("FA Schedule NBV", "${:,.0f}".format(total_nbv))
    col2.metric("BS: Fixed Assets (Net)", "${:,.0f}".format(bs_fa_net))
    col3.metric("Difference", "${:,.2f}".format(fa_diff))
    if fa_diff < 1.00:
        st.success("Fixed Asset Schedule ties to the Balance Sheet.")
    else:
        st.warning("Difference of ${:,.2f} between FA Schedule and BS.".format(fa_diff))


# ==================== Distributions ====================
with tabs[6]:
    st.markdown(
        "### {} | Distributions | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    st.markdown("##### Investor Ownership")
    own_rows = []
    for inv_key, inv in INVESTORS.items():
        own_rows.append({
            "Investor": inv["full_name"],
            "Ownership %": "{:.2%}".format(inv["ownership_pct"]),
            "Contribution": "${:,.2f}".format(inv["contribution"]),
        })
    st.dataframe(pd.DataFrame(own_rows), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Distribution History")
    inv_keys = list(INVESTORS.keys())

    dist_rows = []
    for label, amounts in DISTRIBUTION_HISTORY.items():
        row = {"Quarter": label, "Total": "${:,.2f}".format(amounts["total"])}
        for k in inv_keys:
            row[INVESTOR_REPORT_NAMES.get(k, k)] = "${:,.2f}".format(amounts.get(k, 0))
        dist_rows.append(row)

    db_dists = load_all_distributions()
    for pd_str, amounts in db_dists.items():
        pd_obj = date.fromisoformat(pd_str)
        quarter = (pd_obj.month - 1) // 3 + 1
        label = "Q{} {}".format(quarter, pd_obj.year)
        total = sum(amounts.values())
        row = {"Quarter": label, "Total": "${:,.2f}".format(total)}
        for k in inv_keys:
            row[INVESTOR_REPORT_NAMES.get(k, k)] = "${:,.2f}".format(amounts.get(k, 0))
        dist_rows.append(row)

    if dist_rows:
        grand_total = 0.0
        grand_by_investor = {k: 0.0 for k in inv_keys}
        for label, amounts in DISTRIBUTION_HISTORY.items():
            grand_total += amounts["total"]
            for k in inv_keys:
                grand_by_investor[k] += amounts.get(k, 0)
        for pd_str, amounts in db_dists.items():
            grand_total += sum(amounts.values())
            for k in inv_keys:
                grand_by_investor[k] += amounts.get(k, 0)

        totals_row = {"Quarter": "Total Distributions", "Total": "${:,.2f}".format(grand_total)}
        for k in inv_keys:
            totals_row[INVESTOR_REPORT_NAMES.get(k, k)] = "${:,.2f}".format(grand_by_investor[k])
        dist_rows.append(totals_row)

        st.table(pd.DataFrame(dist_rows))


# ==================== Investor Summary ====================
with tabs[7]:
    st.markdown(
        "### {} | Investor Summary | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    book_basis = sum(FIXED_ASSETS[k]["amount"] for k in FIXED_ASSETS)

    # Get loan balance from amort cache
    if "amort_schedule_cache" not in st.session_state:
        from engine.loan_amortization import generate_amortization_schedule
        st.session_state.amort_schedule_cache = generate_amortization_schedule()
    from engine.loan_amortization import get_ending_balance_at_date
    loan_balance = get_ending_balance_at_date(st.session_state.amort_schedule_cache, selected_end)

    st.markdown("##### Book Value")
    bv_rows = [
        {"Metric": "Book Basis of Assets Held", "Amount": "${:,.2f}".format(book_basis)},
        {"Metric": "Outstanding Debt Balance", "Amount": "${:,.2f}".format(loan_balance)},
        {"Metric": "**Net Book Value**", "Amount": "**${:,.2f}**".format(book_basis - loan_balance)},
    ]
    st.dataframe(pd.DataFrame(bv_rows), hide_index=True, use_container_width=True)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Loan Balance", "${:,.2f}".format(loan_balance))
        st.metric("Maturity Date", LOAN["maturity_date"].strftime("%m/%d/%Y"))
        st.metric("Interest Rate", "{:.2%}".format(LOAN["annual_rate"]))
    with col2:
        st.metric("EBITDA", "${:,.2f}".format(cf.get("EBITDA", 0)))
        st.metric("FCF", "${:,.2f}".format(cf.get("FCF", 0)))
        st.metric("DSCR", "{:.2f}x".format(cf.get("DSCR", 0)))
