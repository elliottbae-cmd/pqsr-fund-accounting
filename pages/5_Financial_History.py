"""Page 5: Financial History — mirrors the Excel workbook layout with roll-forward columns."""

import streamlit as st
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
    LOAN, DISTRIBUTION_HISTORY, TOTAL_MONTHLY_RENT,
)
from config.baseline_data import (
    BALANCE_SHEET, INCOME_STATEMENT_2025, CASH_FLOW_2025, QUARTERLY_NOI,
    TOTAL_DISTRIBUTIONS_THROUGH_BASELINE,
)
from engine.loan_amortization import (
    generate_amortization_schedule, get_ending_balance_at_date,
    get_total_principal_paid,
)

st.header("Financial History")

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

# Load data
bs = load_balance_sheet(selected_period)
is_accounts = load_income_statement(selected_period)
cf = load_cash_flow(selected_period)
totals = load_totals(selected_period)
ajes = load_journal_entries(selected_period)
txns = load_transactions(selected_period)

if not bs:
    st.warning("No data found for this period.")
    st.stop()

# Tab layout matching Excel workbook sheets
tabs = st.tabs([
    "BS (Consolidated)",
    "IS (Consolidated)",
    "AJEs",
    "Bank Activity",
    "Loan Amortization",
    "Distributions",
    "Investor Summary",
])

# ==================== BS_CONS ====================
with tabs[0]:
    st.markdown(
        "### {} | Balance Sheet | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    # Roll-forward format: Beginning | Dr. | Cr. | Ending
    # Beginning = baseline (12/31/2025)
    baseline = BALANCE_SHEET

    def _fmt_val(v):
        if v is None or v == 0:
            return "-"
        if v < 0:
            return "$({:,.2f})".format(abs(v))
        return "${:,.2f}".format(v)

    def _calc_dr_cr(acct):
        """Calculate total debits and credits for an account from AJEs through this period."""
        all_ajes_through = []
        for pd_obj, _, _ in period_dates:
            if pd_obj <= selected_period:
                all_ajes_through.extend(load_journal_entries(pd_obj))
        total_dr = 0.0
        total_cr = 0.0
        for entry in all_ajes_through:
            total_dr += entry["debits"].get(acct, 0)
            total_cr += entry["credits"].get(acct, 0)
        return total_dr, total_cr

    # Build BS rows
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

    # Add investor accounts
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

    for label, acct_key in accounts:
        if acct_key:
            beg = baseline.get(acct_key, 0)
            end = bs.get(acct_key, 0)
            bs_rows.append({
                "Account": label,
                "12/31/2025": _fmt_val(beg),
                selected_end.strftime("%m/%d/%Y"): _fmt_val(end),
                "Change": _fmt_val(end - beg),
            })
        elif label.startswith("**Total Fixed"):
            fa_beg = sum(baseline.get(k, 0) for k in [
                "Land", "Building", "Land Improvements", "F&F", "Equipment", "Signage",
                "Building A/D", "Land Improvements A/D", "F&F A/D",
                "Equipment A/D", "Signage A/D"
            ])
            fa_end = totals.get("total_fa_net", 0)
            bs_rows.append({
                "Account": label,
                "12/31/2025": _fmt_val(fa_beg),
                selected_end.strftime("%m/%d/%Y"): _fmt_val(fa_end),
                "Change": _fmt_val(fa_end - fa_beg),
            })
        elif label.startswith("**Total Other"):
            oa_beg = baseline.get("Capitalized Origination Fee", 0) + baseline.get("Accumulated Amortization", 0)
            oa_end = totals.get("total_other_assets", 0)
            bs_rows.append({
                "Account": label,
                "12/31/2025": _fmt_val(oa_beg),
                selected_end.strftime("%m/%d/%Y"): _fmt_val(oa_end),
                "Change": _fmt_val(oa_end - oa_beg),
            })
        elif label.startswith("**Total Assets"):
            ta_beg = (
                baseline.get("Cash", 0)
                + sum(baseline.get(k, 0) for k in [
                    "Land", "Building", "Land Improvements", "F&F", "Equipment", "Signage",
                    "Building A/D", "Land Improvements A/D", "F&F A/D",
                    "Equipment A/D", "Signage A/D"
                ])
                + baseline.get("Capitalized Origination Fee", 0)
                + baseline.get("Accumulated Amortization", 0)
            )
            ta_end = totals.get("total_assets", 0)
            bs_rows.append({
                "Account": label,
                "12/31/2025": _fmt_val(ta_beg),
                selected_end.strftime("%m/%d/%Y"): _fmt_val(ta_end),
                "Change": _fmt_val(ta_end - ta_beg),
            })
        elif label.startswith("**Total Liab") and "Equity" not in label:
            tl_beg = sum(baseline.get(k, 0) for k in [
                "Note Payable - BBV", "Due to PSP Investments, LLC", "Deferred Rental Revenue"
            ])
            tl_end = totals.get("total_liabilities", 0)
            bs_rows.append({
                "Account": label,
                "12/31/2025": _fmt_val(tl_beg),
                selected_end.strftime("%m/%d/%Y"): _fmt_val(tl_end),
                "Change": _fmt_val(tl_end - tl_beg),
            })
        elif label.startswith("**Total Equity"):
            te_beg = (
                sum(baseline.get("Contributions - {}".format(k), 0) for k in INVESTORS)
                + sum(baseline.get("Distributions - {}".format(k), 0) for k in INVESTORS)
                + baseline.get("CY Net Income", 0)
                + baseline.get("Retained Earnings", 0)
            )
            te_end = totals.get("total_equity", 0)
            bs_rows.append({
                "Account": label,
                "12/31/2025": _fmt_val(te_beg),
                selected_end.strftime("%m/%d/%Y"): _fmt_val(te_end),
                "Change": _fmt_val(te_end - te_beg),
            })
        elif label.startswith("**Total Liabilities / Equity"):
            tle_beg = (
                sum(baseline.get(k, 0) for k in [
                    "Note Payable - BBV", "Due to PSP Investments, LLC", "Deferred Rental Revenue"
                ])
                + sum(baseline.get("Contributions - {}".format(k), 0) for k in INVESTORS)
                + sum(baseline.get("Distributions - {}".format(k), 0) for k in INVESTORS)
                + baseline.get("CY Net Income", 0)
                + baseline.get("Retained Earnings", 0)
            )
            tle_end = totals.get("total_liabilities_equity", 0)
            bs_rows.append({
                "Account": label,
                "12/31/2025": _fmt_val(tle_beg),
                selected_end.strftime("%m/%d/%Y"): _fmt_val(tle_end),
                "Change": _fmt_val(tle_end - tle_beg),
            })
        else:
            # Section header or blank
            bs_rows.append({
                "Account": "**{}**".format(label) if label and not label.startswith("**") else label,
                "12/31/2025": "",
                selected_end.strftime("%m/%d/%Y"): "",
                "Change": "",
            })

    bs_df = pd.DataFrame(bs_rows)
    st.dataframe(bs_df, hide_index=True, use_container_width=True, height=800)

    # Balance check
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
    is_rows = [
        {"Account": "**REVENUE**", "12/31/2025": "", selected_end.strftime("%m/%d/%Y"): "", "Change": ""},
        {
            "Account": "Rental Income",
            "12/31/2025": _fmt_val(is_2025.get("Rental Income", 0)),
            selected_end.strftime("%m/%d/%Y"): _fmt_val(is_accounts.get("Rental Income", 0)),
            "Change": _fmt_val(
                is_accounts.get("Rental Income", 0) - is_2025.get("Rental Income", 0)
            ),
        },
        {"Account": "", "12/31/2025": "", selected_end.strftime("%m/%d/%Y"): "", "Change": ""},
        {"Account": "**EXPENSES**", "12/31/2025": "", selected_end.strftime("%m/%d/%Y"): "", "Change": ""},
    ]

    for exp in ["Interest Expense", "Appraisals", "Accounting & Tax Fees",
                "Bank Fees", "Taxes & Licenses", "Survey Fees",
                "Origination Fee - Amort", "Depreciation Expense"]:
        beg = is_2025.get(exp, 0)
        end = is_accounts.get(exp, 0)
        is_rows.append({
            "Account": exp,
            "12/31/2025": _fmt_val(beg),
            selected_end.strftime("%m/%d/%Y"): _fmt_val(end),
            "Change": _fmt_val(end - beg),
        })

    total_exp_beg = sum(v for k, v in is_2025.items() if k != "Rental Income")
    total_exp_end = sum(
        is_accounts.get(k, 0) for k in is_accounts if k != "Rental Income"
    )
    is_rows.append({
        "Account": "**Total Expenses**",
        "12/31/2025": _fmt_val(total_exp_beg),
        selected_end.strftime("%m/%d/%Y"): _fmt_val(total_exp_end),
        "Change": _fmt_val(total_exp_end - total_exp_beg),
    })

    ni_beg = is_2025.get("Rental Income", 0) - total_exp_beg
    ni_end = is_accounts.get("Rental Income", 0) - total_exp_end
    is_rows.append({
        "Account": "**Net Income**",
        "12/31/2025": _fmt_val(ni_beg),
        selected_end.strftime("%m/%d/%Y"): _fmt_val(ni_end),
        "Change": _fmt_val(ni_end - ni_beg),
    })

    # Cash flow metrics
    is_rows.append({"Account": "", "12/31/2025": "", selected_end.strftime("%m/%d/%Y"): "", "Change": ""})
    cf_2025 = CASH_FLOW_2025
    for metric in ["EBITDA", "Interest Expense", "Principal Payments", "FCF"]:
        beg = cf_2025.get(metric, 0)
        end = cf.get(metric, 0)
        label = metric
        if metric in ("Interest Expense", "Principal Payments"):
            label = "Less: {}".format(metric)
        is_rows.append({
            "Account": label,
            "12/31/2025": _fmt_val(beg),
            selected_end.strftime("%m/%d/%Y"): _fmt_val(end),
            "Change": _fmt_val(end - beg),
        })

    dscr_beg = cf_2025.get("DSCR", 0)
    dscr_end = cf.get("DSCR", 0)
    is_rows.append({
        "Account": "**DSCR**",
        "12/31/2025": "{:.4f}x".format(dscr_beg) if dscr_beg else "-",
        selected_end.strftime("%m/%d/%Y"): "{:.4f}x".format(dscr_end) if dscr_end else "-",
        "Change": "",
    })

    is_df = pd.DataFrame(is_rows)
    st.dataframe(is_df, hide_index=True, use_container_width=True, height=600)


# ==================== AJEs ====================
with tabs[2]:
    st.markdown(
        "### {} | Journal Entries | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    if not ajes:
        st.info("No journal entries for this period.")
    else:
        for i, entry in enumerate(ajes):
            edate = entry["date"].strftime("%m/%d/%Y")
            desc = entry["description"]
            with st.expander(
                "AJE {}: {} ({})".format(i + 1, desc, edate),
                expanded=(i < 3),
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Debits:**")
                    for acct, amt in entry["debits"].items():
                        st.text("  {}: ${:,.2f}".format(acct, amt))
                with col2:
                    st.markdown("**Credits:**")
                    for acct, amt in entry["credits"].items():
                        st.text("  {}: ${:,.2f}".format(acct, amt))

                total_dr = sum(entry["debits"].values())
                total_cr = sum(entry["credits"].values())
                if abs(total_dr - total_cr) < 0.01:
                    st.success("Balanced: ${:,.2f}".format(total_dr))
                else:
                    st.error(
                        "OUT OF BALANCE - DR: ${:,.2f} / CR: ${:,.2f}".format(
                            total_dr, total_cr
                        )
                    )


# ==================== Bank Activity ====================
with tabs[3]:
    st.markdown(
        "### {} | Bank Activity | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

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
        st.dataframe(
            pd.DataFrame(txn_rows),
            hide_index=True, use_container_width=True,
        )

        # Monthly summary
        total_debits = sum(t["debit"] or 0 for t in txns)
        total_credits = sum(t["credit"] or 0 for t in txns)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Debits", "${:,.2f}".format(total_debits))
        col2.metric("Total Credits", "${:,.2f}".format(total_credits))
        col3.metric("Net", "${:,.2f}".format(total_credits - total_debits))


# ==================== Loan Amortization ====================
with tabs[4]:
    st.markdown(
        "### {} | Loan Amortization | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    amort_schedule = generate_amortization_schedule()

    # Show schedule through the selected period
    amort_rows = []
    for entry in amort_schedule:
        if entry["payment_date"] <= selected_end:
            amort_rows.append({
                "Date": entry["payment_date"].strftime("%m/%d/%Y"),
                "Beg. Bal.": "${:,.2f}".format(entry["beginning_balance"]),
                "Interest": "${:,.2f}".format(entry["interest"]),
                "Principal": "${:,.2f}".format(entry["principal"]),
                "Payment": "${:,.2f}".format(entry["payment"]),
                "End. Bal.": "${:,.2f}".format(entry["ending_balance"]),
            })

    if amort_rows:
        st.dataframe(
            pd.DataFrame(amort_rows),
            hide_index=True, use_container_width=True, height=400,
        )

    # Summary metrics
    loan_balance = get_ending_balance_at_date(amort_schedule, selected_end)
    total_principal = get_total_principal_paid(amort_schedule, selected_end)
    total_interest = sum(
        e["interest"] for e in amort_schedule if e["payment_date"] <= selected_end
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Balance", "${:,.2f}".format(loan_balance))
    col2.metric("Total Principal Paid", "${:,.2f}".format(total_principal))
    col3.metric("Total Interest Paid", "${:,.2f}".format(total_interest))


# ==================== Distributions ====================
with tabs[5]:
    st.markdown(
        "### {} | Distributions | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    # Investor ownership
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

    # Distribution history
    st.markdown("##### Distribution History")
    inv_keys = list(INVESTORS.keys())

    dist_rows = []
    # Pre-baseline distributions
    for label, amounts in DISTRIBUTION_HISTORY.items():
        row = {"Quarter": label, "Total": "${:,.2f}".format(amounts["total"])}
        for k in inv_keys:
            row[INVESTOR_REPORT_NAMES.get(k, k)] = "${:,.2f}".format(
                amounts.get(k, 0)
            )
        dist_rows.append(row)

    # Post-baseline distributions from DB
    db_dists = load_all_distributions()
    for pd_str, amounts in db_dists.items():
        pd_obj = date.fromisoformat(pd_str)
        quarter = (pd_obj.month - 1) // 3 + 1
        label = "Q{} {}".format(quarter, pd_obj.year)
        total = sum(amounts.values())
        row = {"Quarter": label, "Total": "${:,.2f}".format(total)}
        for k in inv_keys:
            row[INVESTOR_REPORT_NAMES.get(k, k)] = "${:,.2f}".format(
                amounts.get(k, 0)
            )
        dist_rows.append(row)

    if dist_rows:
        st.dataframe(
            pd.DataFrame(dist_rows),
            hide_index=True, use_container_width=True,
        )


# ==================== Investor Summary ====================
with tabs[6]:
    st.markdown(
        "### {} | Investor Summary | {}".format(
            FUND_NAME, selected_end.strftime("%m/%d/%Y")
        )
    )

    amort_schedule = generate_amortization_schedule()
    loan_balance = get_ending_balance_at_date(amort_schedule, selected_end)
    book_basis = sum(FIXED_ASSETS[k]["amount"] for k in FIXED_ASSETS)

    # Book Value
    st.markdown("##### Book Value")
    bv_rows = [
        {"Metric": "Book Basis of Assets Held", "Amount": "${:,.2f}".format(book_basis)},
        {"Metric": "Outstanding Debt Balance", "Amount": "${:,.2f}".format(loan_balance)},
        {"Metric": "**Net Book Value**", "Amount": "**${:,.2f}**".format(book_basis - loan_balance)},
    ]
    st.dataframe(pd.DataFrame(bv_rows), hide_index=True, use_container_width=True)

    st.markdown("---")

    # Key metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Loan Balance", "${:,.2f}".format(loan_balance))
        st.metric("Maturity Date", LOAN["maturity_date"].strftime("%m/%d/%Y"))
        st.metric("Interest Rate", "{:.2%}".format(LOAN["annual_rate"]))
    with col2:
        st.metric("EBITDA", "${:,.2f}".format(cf.get("EBITDA", 0)))
        st.metric("FCF", "${:,.2f}".format(cf.get("FCF", 0)))
        st.metric("DSCR", "{:.2f}x".format(cf.get("DSCR", 0)))
