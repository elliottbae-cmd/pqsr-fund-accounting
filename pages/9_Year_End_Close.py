"""Page 9: Year-End Close — Review and lock annual financial close."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange, month_name
from database.db import (
    get_posted_periods, get_closed_years, is_year_closed,
    save_year_close, get_year_close_prerequisites,
    load_balance_sheet, load_income_statement, load_totals,
)
from config.fund_config import FUND_NAME, INVESTORS, FIXED_ASSETS
from config.baseline_data import BALANCE_SHEET
from engine.financial_engine import roll_forward, compute_totals
from database.db import load_all_journal_entries_through
from config.styles import (
    inject_custom_css, show_sidebar_branding, styled_page_header,
    styled_section_header, styled_divider, format_currency,
)

inject_custom_css()
show_sidebar_branding()
styled_page_header("Year-End Close", "Annual Financial Close Process")

# --- Show history of closed years with collapsible AJEs ---
closed_years = get_closed_years()
if closed_years:
    styled_section_header("Closed Years")
    history_rows = []
    for cy in closed_years:
        history_rows.append({
            "Year": cy["year"],
            "Closed": cy["closed_at"][:10],
            "CY Net Income": "${:,.2f}".format(cy["cy_net_income"]),
            "RE Before": "${:,.2f}".format(cy["retained_earnings_before"]),
            "RE After": "${:,.2f}".format(cy["retained_earnings_after"]),
            "Locked": "Yes" if cy["locked"] else "No",
        })
    st.dataframe(pd.DataFrame(history_rows), hide_index=True, use_container_width=True)

    # Collapsible AJE for each closed year
    for cy in closed_years:
        cy_ni = cy["cy_net_income"]
        with st.expander("{} Closeout AJE".format(cy["year"]), expanded=False):
            aje_rows = []
            if cy_ni < 0:
                # Loss: Dr Retained Earnings / Cr CY Net Income
                aje_rows.append({
                    "GL Account": "Retained Earnings",
                    "Debit": "${:,.2f}".format(abs(cy_ni)),
                    "Credit": "",
                })
                aje_rows.append({
                    "GL Account": "    CY Net Income",
                    "Debit": "",
                    "Credit": "${:,.2f}".format(abs(cy_ni)),
                })
            else:
                # Profit: Dr CY Net Income / Cr Retained Earnings
                aje_rows.append({
                    "GL Account": "CY Net Income",
                    "Debit": "${:,.2f}".format(cy_ni),
                    "Credit": "",
                })
                aje_rows.append({
                    "GL Account": "    Retained Earnings",
                    "Debit": "",
                    "Credit": "${:,.2f}".format(cy_ni),
                })
            # Totals
            aje_rows.append({
                "GL Account": "Totals",
                "Debit": "${:,.2f}".format(abs(cy_ni)),
                "Credit": "${:,.2f}".format(abs(cy_ni)),
            })
            st.dataframe(
                pd.DataFrame(aje_rows),
                hide_index=True, use_container_width=True,
            )
            st.success("Variance: $0.00 — Entry is in balance")

            # Before/After summary
            st.markdown("**Impact:**")
            st.markdown(
                "- CY Net Income: ${:,.2f} → $0.00\n"
                "- Retained Earnings: ${:,.2f} → ${:,.2f}".format(
                    cy_ni,
                    cy["retained_earnings_before"],
                    cy["retained_earnings_after"],
                )
            )

    styled_divider()

# --- Determine which year can be closed ---
posted = get_posted_periods()
if not posted:
    st.info("No periods have been posted yet. Upload and process bank data first.")
    st.stop()

# Find years that have posted data
posted_years = sorted(set(
    date.fromisoformat(p["period_date"]).year for p in posted
))

# Filter out already-closed years
eligible_years = [y for y in posted_years if not is_year_closed(y)]

if not eligible_years:
    st.success("All fiscal years with posted data have been closed.")
    st.stop()

# Select year to close
if len(eligible_years) == 1:
    selected_year = eligible_years[0]
    st.info("**{}** is ready for year-end review.".format(selected_year))
else:
    selected_year = st.selectbox(
        "Select Year to Close",
        eligible_years,
        format_func=lambda y: "Fiscal Year {}".format(y),
    )

styled_divider()

# --- Prerequisites Check ---
styled_section_header("Prerequisites Check")

prereqs = get_year_close_prerequisites(selected_year)

# Display months status
col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Monthly Periods")
    if not prereqs["months_missing"]:
        st.success("All 12 months posted")
    else:
        posted_names = [month_name[m] for m in prereqs["months_posted"]]
        missing_names = [month_name[m] for m in prereqs["months_missing"]]
        st.markdown("**Posted ({}/12):** {}".format(
            len(prereqs["months_posted"]),
            ", ".join(posted_names) if posted_names else "None"
        ))
        st.error("**Missing:** {}".format(", ".join(missing_names)))

with col2:
    st.markdown("##### Quarterly Depreciation")
    if not prereqs["depreciation_missing"]:
        st.success("All 4 quarters booked")
    else:
        if prereqs["depreciation_posted"]:
            st.markdown("**Booked:** {}".format(
                ", ".join(prereqs["depreciation_posted"])
            ))
        st.error("**Missing:** {}".format(
            ", ".join(prereqs["depreciation_missing"])
        ))

if not prereqs["ready"]:
    st.warning(
        "Cannot close {} — all 12 months and all 4 quarters of depreciation "
        "must be posted before the year-end close.".format(selected_year)
    )
    st.stop()

styled_divider()

# --- Load December data for the closing entry ---
dec_period = date(selected_year, 12, 1)
dec_end = date(selected_year, 12, 31)

bs = load_balance_sheet(dec_period)
is_accounts = load_income_statement(dec_period)
totals_data = load_totals(dec_period)

if not bs:
    st.error("Could not load December {} financial data.".format(selected_year))
    st.stop()

cy_net_income = bs.get("CY Net Income", 0)
retained_earnings = bs.get("Retained Earnings", 0)
re_after_close = retained_earnings + cy_net_income

# --- Preview the Closing Entry ---
styled_section_header("Closing Journal Entry")

st.markdown(
    "**{} | Year-End Close | 12/31/{}**".format(FUND_NAME, selected_year)
)
st.markdown(
    "This entry closes the current year net income/(loss) to retained earnings, "
    "zeroing out the P&L for the new fiscal year."
)

# Build the AJE display
aje_rows = []
if cy_net_income < 0:
    # Loss: Dr Retained Earnings / Cr CY Net Income
    aje_rows.append({
        "GL Account": "Retained Earnings",
        "Debit": "${:,.2f}".format(abs(cy_net_income)),
        "Credit": "",
    })
    aje_rows.append({
        "GL Account": "    CY Net Income",
        "Debit": "",
        "Credit": "${:,.2f}".format(abs(cy_net_income)),
    })
else:
    # Profit: Dr CY Net Income / Cr Retained Earnings
    aje_rows.append({
        "GL Account": "CY Net Income",
        "Debit": "${:,.2f}".format(cy_net_income),
        "Credit": "",
    })
    aje_rows.append({
        "GL Account": "    Retained Earnings",
        "Debit": "",
        "Credit": "${:,.2f}".format(cy_net_income),
    })

# Totals
aje_rows.append({
    "GL Account": "Totals",
    "Debit": "${:,.2f}".format(abs(cy_net_income)),
    "Credit": "${:,.2f}".format(abs(cy_net_income)),
})

st.dataframe(
    pd.DataFrame(aje_rows),
    hide_index=True, use_container_width=True,
)

# Variance check
st.success("Variance: $0.00 — Entry is in balance")

styled_divider()

# --- Before / After Comparison ---
styled_section_header("Balance Sheet Impact")

comparison_rows = [
    {
        "Account": "CY Net Income",
        "Before Close": "${:,.2f}".format(cy_net_income),
        "After Close": "$0.00",
    },
    {
        "Account": "Retained Earnings",
        "Before Close": "${:,.2f}".format(retained_earnings),
        "After Close": "${:,.2f}".format(re_after_close),
    },
    {
        "Account": "Total Equity (unchanged)",
        "Before Close": "${:,.2f}".format(totals_data.get("total_equity", 0)),
        "After Close": "${:,.2f}".format(totals_data.get("total_equity", 0)),
    },
]

st.dataframe(
    pd.DataFrame(comparison_rows),
    hide_index=True, use_container_width=True,
)

st.caption(
    "Total equity does not change — the CY Net Income is simply reclassified "
    "into Retained Earnings. The P&L resets to zero for {}.".format(
        selected_year + 1
    )
)

styled_divider()

# --- Income Statement Summary ---
styled_section_header("{} Income Statement Summary".format(selected_year))

if is_accounts:
    rental_inc = is_accounts.get("Rental Income", 0)
    expense_cats = [
        "Interest Expense", "Appraisals", "Accounting & Tax Fees",
        "Bank Fees", "Taxes & Licenses", "Survey Fees",
        "Origination Fee - Amort", "Depreciation Expense", "Other",
    ]
    total_exp = sum(is_accounts.get(k, 0) for k in expense_cats)
    net_inc = rental_inc - total_exp

    is_rows = [
        {"Account": "Rental Income", "Amount": "${:,.2f}".format(rental_inc)},
    ]
    for cat in expense_cats:
        val = is_accounts.get(cat, 0)
        if val:
            is_rows.append({"Account": cat, "Amount": "${:,.2f}".format(val)})
    is_rows.append({"Account": "Total Expenses", "Amount": "${:,.2f}".format(total_exp)})
    is_rows.append({"Account": "Net Income / (Loss)", "Amount": "${:,.2f}".format(net_inc)})

    st.dataframe(
        pd.DataFrame(is_rows),
        hide_index=True, use_container_width=True,
    )

styled_divider()

# --- Book the Close ---
st.markdown("### Confirm Year-End Close")
st.markdown(
    "By clicking below, you will:\n\n"
    "1. Close the {} P&L to Retained Earnings\n"
    "2. **Lock all {} periods** — no further changes will be allowed to {}\n"
    "3. The {} fiscal year will begin with a fresh P&L".format(
        selected_year, selected_year, selected_year, selected_year + 1
    )
)

if st.button(
    "Close Fiscal Year {}".format(selected_year),
    type="primary",
):
    with st.spinner("Processing year-end close..."):
        # Save the year-end close record (this locks the year)
        save_year_close(
            year=selected_year,
            cy_net_income=cy_net_income,
            re_before=retained_earnings,
            re_after=re_after_close,
        )

        st.success(
            "Fiscal Year {} has been closed and locked.\n\n"
            "- CY Net Income of ${:,.2f} closed to Retained Earnings\n"
            "- Retained Earnings: ${:,.2f} → ${:,.2f}\n"
            "- All {} periods are now locked".format(
                selected_year,
                cy_net_income,
                retained_earnings,
                re_after_close,
                selected_year,
            )
        )
