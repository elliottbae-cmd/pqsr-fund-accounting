"""Page 1: Upload and classify bank transactions."""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from engine.transaction_classifier import classify_bank_data
from config.fund_config import EXPENSE_CATEGORIES

st.header("Upload Bank Data")

st.markdown("""
Upload your bank CSV export(s) for each month since 12/31/2025.
The app will auto-classify rent, loan payments, and distributions.
Unrecognized transactions will be flagged for your review.
""")

uploaded_files = st.file_uploader(
    "Upload bank CSV(s)",
    type=["csv"],
    accept_multiple_files=True,
    help="Export from your bank portal. Expected columns: Post Date, Description, Debit, Credit, Balance"
)

if uploaded_files:
    all_transactions = []

    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file)

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

            st.success(f"Loaded {len(df)} transactions from {uploaded_file.name}")

        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")

    if all_transactions:
        # Sort by date
        all_transactions.sort(key=lambda x: x["date"])

        # Auto-classify
        classified = classify_bank_data(all_transactions)

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

        # Handle unrecognized transactions
        if manual_count > 0:
            st.markdown("#### Needs Manual Classification")
            st.warning(f"{manual_count} transaction(s) could not be auto-classified.")

            for i, txn in enumerate(classified):
                if txn["confidence"] != "manual":
                    continue

                txn_date = txn["date"]
                date_label = txn_date.strftime("%m/%d/%Y") if hasattr(txn_date, "strftime") else str(txn_date)
                desc_label = txn["description"][:50]
                if txn["debit"]:
                    amt_label = "Debit: ${:,.2f}".format(txn["debit"])
                else:
                    amt_label = "Credit: ${:,.2f}".format(txn["credit"])
                expander_label = "{} | {} | {}".format(date_label, desc_label, amt_label)

                with st.expander(expander_label):
                    category = st.selectbox(
                        "Select category",
                        EXPENSE_CATEGORIES,
                        key=f"cat_{i}",
                    )
                    if st.button("Apply", key=f"apply_{i}"):
                        txn["category"] = category.lower().replace(" & ", "_").replace(" ", "_")
                        txn["expense_category"] = category
                        txn["confidence"] = "manual_classified"
                        txn["details"] = f"{category} (manually classified)"
                        st.success(f"Classified as: {category}")

        # Save to session state
        st.session_state.classified_transactions = classified

        if st.button("Confirm Classifications & Generate Journal Entries", type="primary"):
            unclassified = [t for t in classified if t["confidence"] == "manual"]
            if unclassified:
                st.error("Please classify all transactions before proceeding.")
            else:
                st.session_state.processing_complete = True
                st.success("Classifications confirmed! Navigate to 'Review Journal Entries' to continue.")
