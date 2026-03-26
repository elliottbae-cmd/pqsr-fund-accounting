"""Page 6: Depreciation — Review and book quarterly depreciation entries."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from engine.journal_entries import generate_depreciation_aje
from engine.financial_engine import roll_forward, compute_totals, compute_cash_flow_metrics
from engine.loan_amortization import generate_amortization_schedule, get_payments_for_quarter
from config.fund_config import FUND_NAME, FIXED_ASSETS, TOTAL_QUARTERLY_DEPRECIATION
from database.db import (
    get_posted_periods, is_depreciation_posted, get_posted_depreciation,
    save_depreciation_posted, save_depreciation_journal_entry,
    load_all_journal_entries_through, save_period, load_balance_sheet,
    load_income_statement, load_cash_flow, load_totals, is_period_posted,
    load_transactions,
)
from config.styles import (
    inject_custom_css, show_sidebar_branding, styled_page_header,
    styled_section_header, styled_divider, format_currency,
)

inject_custom_css()
show_sidebar_branding()
styled_page_header("Depreciation", "Quarterly Depreciation Entries")

# --- Show depreciation history ---
posted_depr = get_posted_depreciation()
if posted_depr:
    styled_section_header("Posted Depreciation")
    depr_history = []
    for d in posted_depr:
        depr_history.append({
            "Quarter": d["quarter_key"],
            "Total Depreciation": "${:,.2f}".format(d["total_depreciation"]),
            "Posted": d["posted_at"][:10],
        })
    st.dataframe(pd.DataFrame(depr_history), hide_index=True, use_container_width=True)
    styled_divider()

# --- Determine which quarter needs depreciation ---
posted_periods = get_posted_periods()
if not posted_periods:
    st.info("No periods have been posted yet. Upload and process bank data first.")
    st.stop()

# Find quarter-end months that have been posted but don't have depreciation booked
from database.db import is_year_closed
eligible_quarters = []
for p in posted_periods:
    pd_obj = date.fromisoformat(p["period_date"])
    if pd_obj.month in (3, 6, 9, 12):
        # Skip quarters in closed years
        if is_year_closed(pd_obj.year):
            continue
        quarter = (pd_obj.month - 1) // 3 + 1
        quarter_key = "Q{} {}".format(quarter, pd_obj.year)
        if not is_depreciation_posted(quarter_key):
            last_day = date(pd_obj.year, pd_obj.month,
                            monthrange(pd_obj.year, pd_obj.month)[1])
            eligible_quarters.append({
                "quarter_key": quarter_key,
                "quarter": quarter,
                "year": pd_obj.year,
                "period_date": pd_obj,
                "quarter_end": last_day,
            })

if not eligible_quarters:
    st.success("All quarterly depreciation entries are up to date.")
    st.markdown(
        "Depreciation will be available to book after the next quarter-end "
        "month is posted (March, June, September, or December)."
    )
    st.stop()

# Let user select which quarter to book
if len(eligible_quarters) == 1:
    selected = eligible_quarters[0]
    st.info("**{}** depreciation is ready to book.".format(selected["quarter_key"]))
else:
    quarter_options = [q["quarter_key"] for q in eligible_quarters]
    selected_key = st.selectbox("Select Quarter", quarter_options)
    selected = next(q for q in eligible_quarters if q["quarter_key"] == selected_key)

styled_divider()

# --- Generate the depreciation AJE ---
styled_section_header("{} Depreciation Entry".format(selected["quarter_key"]))

depr_entry = generate_depreciation_aje(selected["quarter_end"])

# Display the AJE in a professional table
st.markdown(
    "**{} | {} | {}**".format(
        FUND_NAME,
        depr_entry["description"],
        selected["quarter_end"].strftime("%m/%d/%Y"),
    )
)

aje_rows = []
for acct, amt in depr_entry["debits"].items():
    aje_rows.append({
        "GL Account": acct,
        "Debit": "${:,.2f}".format(amt),
        "Credit": "",
    })
for acct, amt in depr_entry["credits"].items():
    aje_rows.append({
        "GL Account": "    {}".format(acct),
        "Debit": "",
        "Credit": "${:,.2f}".format(amt),
    })

total_dr = sum(depr_entry["debits"].values())
total_cr = sum(depr_entry["credits"].values())

aje_rows.append({
    "GL Account": "Totals",
    "Debit": "${:,.2f}".format(total_dr),
    "Credit": "${:,.2f}".format(total_cr),
})

st.dataframe(
    pd.DataFrame(aje_rows),
    hide_index=True, use_container_width=True,
)

# Variance check
net = total_dr - total_cr
if abs(net) < 0.01:
    st.success("Variance: $0.00 — Entry is in balance")
else:
    st.error("Variance: ${:,.2f} — OUT OF BALANCE".format(net))

styled_divider()

# --- Asset class breakdown ---
styled_section_header("Depreciation by Asset Class")

breakdown_rows = []
for asset_class, info in FIXED_ASSETS.items():
    if info["quarterly_depreciation"] > 0:
        breakdown_rows.append({
            "Asset Class": asset_class,
            "Cost Basis": "${:,.2f}".format(info["amount"]),
            "Useful Life": "{} years".format(info["useful_life"]),
            "Annual Depr.": "${:,.2f}".format(info["annual_depreciation"]),
            "Quarterly Depr.": "${:,.2f}".format(info["quarterly_depreciation"]),
        })

breakdown_rows.append({
    "Asset Class": "Total",
    "Cost Basis": "",
    "Useful Life": "",
    "Annual Depr.": "${:,.2f}".format(
        sum(info["annual_depreciation"] for info in FIXED_ASSETS.values())
    ),
    "Quarterly Depr.": "${:,.2f}".format(TOTAL_QUARTERLY_DEPRECIATION),
})

st.dataframe(
    pd.DataFrame(breakdown_rows),
    hide_index=True, use_container_width=True,
)

styled_divider()

# --- Book the entry ---
if st.button(
    "Book {} Depreciation".format(selected["quarter_key"]),
    type="primary",
):
    with st.spinner("Booking depreciation and recalculating financials..."):
        # 1. Save the depreciation journal entry to DB
        save_depreciation_journal_entry(selected["quarter_end"], depr_entry)

        # 2. Mark depreciation as posted
        save_depreciation_posted(selected["quarter_key"], total_dr)

        # 3. Recalculate financials for the quarter-end period
        # Load all journal entries through this period (now includes depreciation)
        all_entries = load_all_journal_entries_through(selected["period_date"])

        last_day = selected["quarter_end"]
        bs, is_accounts = roll_forward(all_entries, last_day)
        totals = compute_totals(bs)

        # Recalculate cash flow
        amort_schedule = generate_amortization_schedule()
        quarterly_payments = get_payments_for_quarter(
            amort_schedule, selected["year"], selected["quarter"]
        )
        quarterly_principal = sum(p["principal"] for p in quarterly_payments)
        cash_flow = compute_cash_flow_metrics(is_accounts, quarterly_principal)

        # Load existing transactions for this period (don't overwrite them)
        existing_txns = load_transactions(selected["period_date"])

        # Load existing NON-DEPRECIATION journal entries for this period.
        # Depreciation was already saved by save_depreciation_journal_entry() above,
        # so we exclude it here to prevent save_period() from creating a duplicate.
        period_entries = [
            e for e in all_entries
            if hasattr(e.get("date"), "year")
            and e["date"].year == selected["period_date"].year
            and e["date"].month == selected["period_date"].month
            and e.get("entry_type") != "depreciation"
        ]

        # Re-save the period with updated financials
        save_period(
            period_date=selected["period_date"],
            transactions=existing_txns,
            journal_entries=period_entries,
            bs=bs,
            is_accounts=is_accounts,
            cash_flow=cash_flow,
            totals=totals,
        )

        st.success(
            "{} depreciation of ${:,.2f} has been booked and financials updated.".format(
                selected["quarter_key"], total_dr
            )
        )
