"""Page 12: Manual Journal Entry — book an AJE to any BS or P&L account."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from calendar import monthrange
from engine.financial_engine import (
    roll_forward, compute_totals, compute_cash_flow_metrics, DEBIT_SIGN,
)
from engine.loan_amortization import (
    generate_amortization_schedule, get_ytd_principal_paid,
)
from database.db import (
    get_posted_periods, is_period_posted, is_year_closed,
    load_all_journal_entries_through, load_transactions, save_period,
    save_manual_journal_entry, delete_manual_journal_entry, load_manual_entries,
)
from config.styles import (
    inject_custom_css, show_sidebar_branding, styled_page_header,
    styled_section_header, styled_divider,
)

inject_custom_css()
show_sidebar_branding()
styled_page_header("Manual Journal Entry", "Book an adjusting entry to any account")

# --- Account list ---
# Balance sheet accounts come from the engine's DEBIT_SIGN map so the ledger
# can post to every one of them. "CY Net Income" is excluded on purpose:
# roll_forward recomputes it from the income statement after every entry, so a
# direct posting there would be silently overwritten — P&L adjustments belong
# on the P&L accounts below instead.
BS_ACCOUNTS = [a for a in DEBIT_SIGN if a != "CY Net Income"]
PL_ACCOUNTS = [
    "Rental Income", "Interest Expense", "Accounting & Tax Fees", "Bank Fees",
    "Appraisals", "Taxes & Licenses", "Survey Fees",
    "Origination Fee - Amort", "Depreciation Expense", "Other",
]
ACCOUNT_OPTIONS = BS_ACCOUNTS + PL_ACCOUNTS


def _recompute_posted_periods_from(start_period):
    """Re-roll and re-save snapshots for start_period and every later posted
    period. A journal entry changes the cumulative roll-forward, so all
    downstream months' stored BS/IS/cash-flow must be refreshed too."""
    amort_schedule = generate_amortization_schedule()
    recomputed = []
    for p in get_posted_periods():
        pd_obj = date.fromisoformat(p["period_date"])
        if pd_obj < start_period:
            continue
        last_day = date(
            pd_obj.year, pd_obj.month, monthrange(pd_obj.year, pd_obj.month)[1]
        )
        all_entries = load_all_journal_entries_through(pd_obj)
        bs, is_accounts = roll_forward(all_entries, last_day)
        totals = compute_totals(bs)
        ytd_principal = get_ytd_principal_paid(amort_schedule, pd_obj.year, last_day)
        cash_flow = compute_cash_flow_metrics(is_accounts, ytd_principal)
        existing_txns = load_transactions(pd_obj)
        # Only 'monthly' entries go back through save_period — depreciation and
        # manual entries are preserved in the DB and must not be re-inserted.
        period_entries = [
            e for e in all_entries
            if e["date"].year == pd_obj.year
            and e["date"].month == pd_obj.month
            and e.get("entry_type") == "monthly"
        ]
        save_period(
            period_date=pd_obj,
            transactions=existing_txns,
            journal_entries=period_entries,
            bs=bs,
            is_accounts=is_accounts,
            cash_flow=cash_flow,
            totals=totals,
        )
        recomputed.append(pd_obj.strftime("%B %Y"))
    return recomputed


# Flash message from a prior post/delete (survives the rerun that resets the form)
if st.session_state.get("manual_aje_flash"):
    st.success(st.session_state.pop("manual_aje_flash"))

st.markdown(
    "Build a balanced journal entry below. Each line posts to any balance-sheet "
    "or P&L account. Posting recomputes the stored financials for the entry's "
    "month **and every later posted month**, so all statements stay consistent."
)

# --- Entry form ---
col1, col2 = st.columns([1, 3])
with col1:
    # format="MM/DD/YYYY" so typed US-style dates (e.g. 9/30/2026) are accepted —
    # Streamlit's default is YYYY/MM/DD, which silently rejects US-style typing
    # and snaps back to today, making backdating look blocked. Explicit bounds
    # keep entries within the app's accounting life (post-baseline, not future).
    entry_date = st.date_input(
        "Entry Date",
        value=date.today(),
        min_value=date(2026, 1, 1),
        max_value=date.today(),
        format="MM/DD/YYYY",
        key="aje_date",
    )
with col2:
    description = st.text_input(
        "Description", key="aje_desc",
        placeholder="e.g. To reclass survey fee posted to Other",
    )

blank_rows = pd.DataFrame(
    [{"Account": None, "Debit": None, "Credit": None} for _ in range(4)]
)
edited = st.data_editor(
    blank_rows,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="aje_editor",
    column_config={
        "Account": st.column_config.SelectboxColumn(
            "Account", options=ACCOUNT_OPTIONS, width="large",
        ),
        "Debit": st.column_config.NumberColumn(
            "Debit", min_value=0.0, format="%.2f",
        ),
        "Credit": st.column_config.NumberColumn(
            "Credit", min_value=0.0, format="%.2f",
        ),
    },
)

# --- Parse + validate the grid ---
debits = {}
credits = {}
line_errors = []
for idx, row in edited.iterrows():
    acct = row["Account"]
    debit = 0.0 if pd.isna(row["Debit"]) else float(row["Debit"])
    credit = 0.0 if pd.isna(row["Credit"]) else float(row["Credit"])
    has_acct = isinstance(acct, str) and acct.strip() != ""
    if not has_acct and debit == 0 and credit == 0:
        continue  # untouched blank row
    if not has_acct:
        line_errors.append("Row {}: amount entered but no account selected.".format(idx + 1))
        continue
    if debit > 0 and credit > 0:
        line_errors.append("Row {} ({}): enter a debit OR a credit, not both.".format(idx + 1, acct))
        continue
    if debit == 0 and credit == 0:
        line_errors.append("Row {} ({}): no amount entered.".format(idx + 1, acct))
        continue
    if debit > 0:
        debits[acct] = debits.get(acct, 0) + debit
    else:
        credits[acct] = credits.get(acct, 0) + credit

total_dr = sum(debits.values())
total_cr = sum(credits.values())
variance = total_dr - total_cr

m1, m2, m3 = st.columns(3)
m1.metric("Total Debits", "${:,.2f}".format(total_dr))
m2.metric("Total Credits", "${:,.2f}".format(total_cr))
m3.metric("Variance", "${:,.2f}".format(variance))

if line_errors:
    for err in line_errors:
        st.warning(err)

balanced = abs(variance) < 0.005 and total_dr > 0

if st.button("Post Manual AJE", type="primary", disabled=bool(line_errors) or not balanced):
    if not description.strip():
        st.error("Please enter a description for the entry.")
        st.stop()
    if is_year_closed(entry_date.year):
        st.error(
            "Fiscal year {} is closed and locked. Cannot book entries there.".format(
                entry_date.year
            )
        )
        st.stop()

    with st.spinner("Booking entry and recalculating financials..."):
        save_manual_journal_entry(entry_date, description.strip(), debits, credits)
        period = date(entry_date.year, entry_date.month, 1)
        if is_period_posted(period):
            recomputed = _recompute_posted_periods_from(period)
            msg = (
                "Manual AJE posted ({}). Financials recomputed for: {}.".format(
                    entry_date.strftime("%m/%d/%Y"), ", ".join(recomputed)
                )
            )
        else:
            msg = (
                "Manual AJE saved for {}. That month is not posted yet — the "
                "entry will be included automatically when you post it.".format(
                    entry_date.strftime("%B %Y")
                )
            )

    # Reset the form and show the confirmation after rerun
    st.session_state["manual_aje_flash"] = msg
    for k in ("aje_editor", "aje_desc"):
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

if not balanced and (total_dr > 0 or total_cr > 0) and not line_errors:
    st.error("Entry is OUT OF BALANCE by ${:,.2f} — debits must equal credits.".format(abs(variance)))

# --- Existing manual entries ---
styled_divider()
styled_section_header("Booked Manual Entries")

manual_entries = load_manual_entries()
if not manual_entries:
    st.info("No manual journal entries have been booked yet.")
else:
    for entry in manual_entries:
        entry_dr = sum(entry["debits"].values())
        label = "{} | {} | ${:,.2f}".format(
            entry["date"].strftime("%m/%d/%Y"), entry["description"], entry_dr
        )
        with st.expander(label):
            rows = []
            for acct, amt in entry["debits"].items():
                rows.append({"GL Account": acct, "Debit": "${:,.2f}".format(amt), "Credit": ""})
            for acct, amt in entry["credits"].items():
                rows.append({"GL Account": "    {}".format(acct), "Debit": "", "Credit": "${:,.2f}".format(amt)})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

            if st.button("Delete This Entry", key="del_aje_{}".format(entry["id"])):
                with st.spinner("Deleting entry and recalculating financials..."):
                    try:
                        delete_manual_journal_entry(entry["id"])
                    except ValueError as e:
                        st.error(str(e))
                        st.stop()
                    period = date.fromisoformat(entry["period_date"])
                    if is_period_posted(period):
                        recomputed = _recompute_posted_periods_from(period)
                        msg = "Manual AJE deleted. Financials recomputed for: {}.".format(
                            ", ".join(recomputed)
                        )
                    else:
                        msg = "Manual AJE deleted."
                st.session_state["manual_aje_flash"] = msg
                st.rerun()
