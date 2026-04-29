"""Page 1: Upload and classify bank transactions — monthly processing."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date, datetime
from engine.transaction_classifier import classify_bank_data
from config.fund_config import EXPENSE_CATEGORIES, PROPERTIES
from database.db import get_next_expected_month, get_posted_periods, is_period_posted
from config.styles import inject_custom_css, show_sidebar_branding, styled_page_header, styled_section_header, styled_divider, format_currency

inject_custom_css()
show_sidebar_branding()
styled_page_header("Upload Bank Data", "Monthly Transaction Processing")

# Show posted period history
posted = get_posted_periods()
if posted:
    st.markdown("##### Posted Periods")
    period_rows = []
    for p in posted:
        pd_obj = date.fromisoformat(p["period_date"])
        period_rows.append({
            "Period": pd_obj.strftime("%B %Y"),
            "Posted": p["posted_at"][:10],
            "Quarter End": "Yes" if p["quarter_end"] else "",
        })
    st.dataframe(pd.DataFrame(period_rows), hide_index=True, use_container_width=True)
    st.markdown("---")

# Auto-detect next month
next_month = get_next_expected_month()

# Year-lock check
from database.db import is_year_closed
if is_year_closed(next_month.year):
    st.error(
        "Fiscal year {} is closed and locked. "
        "Cannot upload data for closed periods.".format(next_month.year)
    )
    st.stop()

st.info(
    "**Next period to process:** {}\n\n"
    "Upload bank activity that includes transactions for {}. "
    "The system will filter to only this month's transactions.".format(
        next_month.strftime("%B %Y"),
        next_month.strftime("%B %Y"),
    )
)

st.markdown("""
Upload your bank export for the month. Accepts CSV or Excel (.xlsx/.xls) files.
The app will auto-classify rent, loan payments, and distributions.
Unrecognized transactions will be flagged for your review.
""")

uploaded_files = st.file_uploader(
    "Upload bank file(s)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
    help="Export from your bank portal. Expected columns: Post Date, Description, Debit, Credit, Balance"
)

if uploaded_files:
    all_transactions = []

    for uploaded_file in uploaded_files:
        try:
            filename = uploaded_file.name.lower()
            if filename.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            # Normalize column names
            col_map = {}
            for col in df.columns:
                cl = col.strip().lower()
                if "date" in cl and "post" in cl:
                    col_map[col] = "post_date"
                elif "date" in cl:
                    col_map[col] = "post_date"
                elif "desc" in cl:
                    col_map[col] = "description"
                elif "debit" in cl:
                    col_map[col] = "debit"
                elif "credit" in cl:
                    col_map[col] = "credit"
                elif "balance" in cl:
                    col_map[col] = "balance"
                elif "check" in cl:
                    col_map[col] = "check"
                elif "status" in cl:
                    col_map[col] = "status"

            df = df.rename(columns=col_map)

            # Parse and clean
            if "post_date" in df.columns:
                df["post_date"] = pd.to_datetime(df["post_date"], format="mixed")
            if "debit" in df.columns:
                df["debit"] = pd.to_numeric(
                    df["debit"].astype(str).str.replace(",", "").str.replace("$", ""),
                    errors="coerce"
                ).fillna(0)
            if "credit" in df.columns:
                df["credit"] = pd.to_numeric(
                    df["credit"].astype(str).str.replace(",", "").str.replace("$", ""),
                    errors="coerce"
                ).fillna(0)

            for _, row in df.iterrows():
                all_transactions.append({
                    "date": row.get("post_date", date.today()),
                    "description": str(row.get("description", "")),
                    "debit": row.get("debit", 0),
                    "credit": row.get("credit", 0),
                    "balance": row.get("balance", 0),
                })

            st.success(
                "Loaded {} transactions from {}".format(len(df), uploaded_file.name)
            )

        except Exception as e:
            st.error("Error reading {}: {}".format(uploaded_file.name, e))

    if all_transactions:
        # Filter to the target month
        target_year = next_month.year
        target_month = next_month.month
        month_transactions = []
        other_transactions = []

        for txn in all_transactions:
            txn_date = txn["date"]
            if hasattr(txn_date, "year"):
                if txn_date.year == target_year and txn_date.month == target_month:
                    month_transactions.append(txn)
                else:
                    other_transactions.append(txn)
            else:
                other_transactions.append(txn)

        if other_transactions:
            st.warning(
                "{} transaction(s) outside {} were excluded.".format(
                    len(other_transactions), next_month.strftime("%B %Y")
                )
            )

        if not month_transactions:
            st.error(
                "No transactions found for {}. "
                "Make sure the file contains transactions for this month.".format(
                    next_month.strftime("%B %Y")
                )
            )
            st.stop()

        st.markdown(
            "**Processing {} transactions for {}**".format(
                len(month_transactions), next_month.strftime("%B %Y")
            )
        )

        # Sort by date
        month_transactions.sort(key=lambda x: x["date"])

        # Auto-classify — only if not already classified (preserves manual overrides)
        if (st.session_state.get("classified_transactions")
                and st.session_state.get("processing_month") == next_month
                and len(st.session_state.classified_transactions) == len(month_transactions)):
            classified = st.session_state.classified_transactions
        else:
            classified = classify_bank_data(month_transactions)
            st.session_state.classified_transactions = classified
            st.session_state.processing_month = next_month

        # Display classified transactions
        st.subheader("Classified Transactions")

        auto_count = sum(1 for t in classified if t["confidence"] == "auto")
        manual_count = sum(1 for t in classified if t["confidence"] == "manual")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Transactions", len(classified))
        col2.metric("Auto-Classified", auto_count)
        col3.metric("Needs Review", manual_count)

        # Show auto-classified
        if auto_count > 0:
            st.markdown("#### Auto-Classified")
            auto_rows = []
            for t in classified:
                if t["confidence"] != "auto":
                    continue
                d = t["date"]
                date_str = d.strftime("%m/%d/%Y") if hasattr(d, "strftime") else str(d)
                debit_val = t["debit"]
                credit_val = t["credit"]
                debit_str = "${:,.2f}".format(debit_val) if debit_val else ""
                credit_str = "${:,.2f}".format(credit_val) if credit_val else ""
                auto_rows.append({
                    "Date": date_str,
                    "Description": t["description"][:60],
                    "Debit": debit_str,
                    "Credit": credit_str,
                    "Category": t["details"],
                })
            auto_df = pd.DataFrame(auto_rows)
            st.dataframe(auto_df, use_container_width=True, hide_index=True)

        # --- Property Override Section ---
        # Property classification is informational only (rent rolls up to a single
        # "Rental Income" account in the GL), but this lets users correct any
        # mis-classification before the transaction record is stored.
        rent_txns = [(i, t) for i, t in enumerate(classified) if t["category"] == "rent"]
        if rent_txns:
            with st.expander(
                "Override Property Assignment ({} rent transaction{})".format(
                    len(rent_txns), "" if len(rent_txns) == 1 else "s"
                ),
                expanded=False,
            ):
                st.caption(
                    "Property classification is informational only — it does not "
                    "affect journal entries or financial statements. Use this to "
                    "correct any mis-classified rent payments before posting."
                )
                property_options = list(PROPERTIES.keys())

                for idx, txn in rent_txns:
                    d = txn["date"]
                    date_str = d.strftime("%m/%d/%Y") if hasattr(d, "strftime") else str(d)
                    credit_val = txn.get("credit", 0) or 0
                    current_prop = txn.get("property") or property_options[0]

                    label = "{} | {} | ${:,.2f}".format(
                        date_str,
                        txn["description"][:50],
                        credit_val,
                    )

                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.text(label)
                    with col2:
                        new_prop = st.selectbox(
                            "Property",
                            property_options,
                            index=property_options.index(current_prop)
                                if current_prop in property_options else 0,
                            format_func=lambda k: PROPERTIES[k]["name"],
                            key="prop_override_{}".format(idx),
                            label_visibility="collapsed",
                        )
                        if new_prop != current_prop:
                            classified[idx]["property"] = new_prop
                            classified[idx]["details"] = "Rent - {} (manually overridden)".format(
                                PROPERTIES[new_prop]["name"]
                            )
                            st.session_state.classified_transactions = classified

        # Handle unrecognized transactions
        if manual_count > 0:
            st.markdown("#### Needs Manual Classification")
            st.warning(
                "{} transaction(s) could not be auto-classified.".format(manual_count)
            )

            for i, txn in enumerate(classified):
                if txn["confidence"] != "manual":
                    continue

                txn_date = txn["date"]
                date_label = (
                    txn_date.strftime("%m/%d/%Y")
                    if hasattr(txn_date, "strftime") else str(txn_date)
                )
                desc_label = txn["description"][:50]
                if txn["debit"]:
                    amt_label = "Debit: ${:,.2f}".format(txn["debit"])
                else:
                    amt_label = "Credit: ${:,.2f}".format(txn["credit"])
                expander_label = "{} | {} | {}".format(
                    date_label, desc_label, amt_label
                )

                with st.expander(expander_label):
                    category = st.selectbox(
                        "Select category",
                        EXPENSE_CATEGORIES,
                        key="cat_{}".format(i),
                    )
                    if st.button("Apply", key="apply_{}".format(i)):
                        txn["category"] = category.lower().replace(
                            " & ", "_"
                        ).replace(" ", "_")
                        txn["expense_category"] = category
                        txn["confidence"] = "manual_classified"
                        txn["details"] = "{} (manually classified)".format(
                            category
                        )
                        st.session_state.classified_transactions = classified
                        st.rerun()

        # Save to session state
        st.session_state.classified_transactions = classified
        st.session_state.processing_month = next_month

        if st.button(
            "Confirm Classifications & Generate Journal Entries",
            type="primary",
        ):
            unclassified = [
                t for t in classified if t["confidence"] == "manual"
            ]
            if unclassified:
                st.error(
                    "Please classify all transactions before proceeding."
                )
            else:
                st.session_state.processing_complete = True
                st.success(
                    "Classifications confirmed! Navigate to "
                    "'Review Journal Entries' to continue."
                )
