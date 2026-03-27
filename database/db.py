"""Supabase Postgres database layer for persistent financial data storage."""

import os
import psycopg2
import psycopg2.extras
from datetime import date, datetime
from contextlib import contextmanager

# Connection parameters — loaded from Streamlit secrets or environment
def _get_db_url():
    """Get the database URL from Streamlit secrets or environment."""
    try:
        import streamlit as st
        return st.secrets["DATABASE_URL"]
    except Exception:
        return os.environ.get("DATABASE_URL", "")


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = psycopg2.connect(_get_db_url(), sslmode="require")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _fetchall(conn, query, params=None):
    """Execute a query and return all rows as list of dicts."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params or ())
    return [dict(r) for r in cur.fetchall()]


def _fetchone(conn, query, params=None):
    """Execute a query and return one row as dict or None."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params or ())
    row = cur.fetchone()
    return dict(row) if row else None


def _execute(conn, query, params=None):
    """Execute a query and return the cursor."""
    cur = conn.cursor()
    cur.execute(query, params or ())
    return cur


def init_db():
    """Tables are created in Supabase — this is a no-op for cloud deployment.
    Kept for API compatibility."""
    pass


# --- Posted Periods ---

def get_posted_periods():
    """Return all posted periods sorted by date."""
    with get_connection() as conn:
        return _fetchall(conn, "SELECT * FROM posted_periods ORDER BY period_date")


def get_last_posted_period():
    """Return the most recently posted period date, or None."""
    with get_connection() as conn:
        row = _fetchone(conn,
            "SELECT period_date FROM posted_periods ORDER BY period_date DESC LIMIT 1")
    if row:
        return date.fromisoformat(row["period_date"])
    return None


def get_next_expected_month():
    """Determine the next month to process based on posted history."""
    from dateutil.relativedelta import relativedelta
    last = get_last_posted_period()
    if last is None:
        return date(2026, 1, 1)
    return date(last.year, last.month, 1) + relativedelta(months=1)


def is_period_posted(period_date):
    """Check if a period has been posted."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        row = _fetchone(conn,
            "SELECT 1 FROM posted_periods WHERE period_date = %s", (pd_str,))
    return row is not None


# --- Save a Complete Period ---

def save_period(period_date, transactions, journal_entries, bs, is_accounts,
                cash_flow, totals, distributions=None):
    """Save all data for a posted period to the database."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date

    # Year-lock check
    year_val = period_date.year if isinstance(period_date, date) else date.fromisoformat(period_date).year
    if is_year_closed(year_val):
        raise ValueError(
            "Year {} is closed. Cannot modify periods in a closed year.".format(year_val)
        )
    is_qtr_end = period_date.month in (3, 6, 9, 12)

    with get_connection() as conn:
        cur = conn.cursor()

        # 1. Posted period record
        cur.execute(
            "INSERT INTO posted_periods (period_date, period_type, posted_at, quarter_end) "
            "VALUES (%s, 'monthly', %s, %s) "
            "ON CONFLICT (period_date) DO UPDATE SET posted_at = EXCLUDED.posted_at, "
            "quarter_end = EXCLUDED.quarter_end",
            (pd_str, datetime.now().isoformat(), 1 if is_qtr_end else 0)
        )

        # 2. Transactions
        cur.execute("DELETE FROM transactions WHERE period_date = %s", (pd_str,))
        for txn in transactions:
            txn_date = txn.get("date", period_date)
            if hasattr(txn_date, "isoformat"):
                txn_date_str = txn_date.isoformat()
            elif hasattr(txn_date, "date"):
                txn_date_str = txn_date.date().isoformat()
            else:
                txn_date_str = str(txn_date)
            cur.execute(
                "INSERT INTO transactions "
                "(period_date, post_date, description, debit, credit, balance, "
                "category, property, investor, confidence, details) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (pd_str, txn_date_str, txn.get("description", ""),
                 txn.get("debit", 0) or 0, txn.get("credit", 0) or 0,
                 txn.get("balance", 0) or 0,
                 txn.get("category"), txn.get("property"),
                 txn.get("investor"), txn.get("confidence"),
                 txn.get("details"))
            )

        # 3. Journal entries — delete old non-depreciation entries
        old_ids = _fetchall(conn,
            "SELECT id FROM journal_entries WHERE period_date = %s AND entry_type != 'depreciation'",
            (pd_str,))
        old_id_list = [r["id"] for r in old_ids]
        if old_id_list:
            cur.execute(
                "DELETE FROM journal_entry_lines WHERE entry_id = ANY(%s)",
                (old_id_list,)
            )
            cur.execute(
                "DELETE FROM journal_entries WHERE period_date = %s AND entry_type != 'depreciation'",
                (pd_str,)
            )

        for entry in journal_entries:
            entry_date = entry["date"]
            if hasattr(entry_date, "isoformat"):
                entry_date_str = entry_date.isoformat()
            else:
                entry_date_str = str(entry_date)
            entry_type = "depreciation" if "depreciation" in entry["description"].lower() else "monthly"
            cur.execute(
                "INSERT INTO journal_entries (period_date, entry_date, description, entry_type) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (pd_str, entry_date_str, entry["description"], entry_type)
            )
            entry_id = cur.fetchone()[0]
            for acct, amt in entry.get("debits", {}).items():
                cur.execute(
                    "INSERT INTO journal_entry_lines (entry_id, account, debit_amount) "
                    "VALUES (%s, %s, %s)",
                    (entry_id, acct, amt)
                )
            for acct, amt in entry.get("credits", {}).items():
                cur.execute(
                    "INSERT INTO journal_entry_lines (entry_id, account, credit_amount) "
                    "VALUES (%s, %s, %s)",
                    (entry_id, acct, amt)
                )

        # 4. Balance sheet snapshot
        cur.execute("DELETE FROM balance_sheet_snapshots WHERE period_date = %s", (pd_str,))
        for acct, amt in bs.items():
            cur.execute(
                "INSERT INTO balance_sheet_snapshots (period_date, account, amount) VALUES (%s, %s, %s)",
                (pd_str, acct, amt)
            )

        # 5. Income statement snapshot
        cur.execute("DELETE FROM income_statement_snapshots WHERE period_date = %s", (pd_str,))
        for acct, amt in is_accounts.items():
            cur.execute(
                "INSERT INTO income_statement_snapshots (period_date, account, amount) VALUES (%s, %s, %s)",
                (pd_str, acct, amt)
            )

        # 6. Cash flow snapshot
        cur.execute("DELETE FROM cash_flow_snapshots WHERE period_date = %s", (pd_str,))
        for metric, val in cash_flow.items():
            cur.execute(
                "INSERT INTO cash_flow_snapshots (period_date, metric, value) VALUES (%s, %s, %s)",
                (pd_str, metric, val)
            )

        # 7. Totals snapshot
        cur.execute("DELETE FROM totals_snapshots WHERE period_date = %s", (pd_str,))
        for metric, val in totals.items():
            cur.execute(
                "INSERT INTO totals_snapshots (period_date, metric, value) VALUES (%s, %s, %s)",
                (pd_str, metric, val)
            )

        # 8. Distribution snapshot (quarter-end only)
        if distributions:
            cur.execute("DELETE FROM distribution_snapshots WHERE period_date = %s", (pd_str,))
            for inv_key, amt in distributions.items():
                if inv_key == "total":
                    continue
                cur.execute(
                    "INSERT INTO distribution_snapshots (period_date, investor_key, amount) "
                    "VALUES (%s, %s, %s)",
                    (pd_str, inv_key, amt)
                )


# --- Load Period Data ---

def load_balance_sheet(period_date):
    """Load balance sheet for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT account, amount FROM balance_sheet_snapshots WHERE period_date = %s",
            (pd_str,))
    return {r["account"]: r["amount"] for r in rows}


def load_income_statement(period_date):
    """Load income statement for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT account, amount FROM income_statement_snapshots WHERE period_date = %s",
            (pd_str,))
    return {r["account"]: r["amount"] for r in rows}


def load_cash_flow(period_date):
    """Load cash flow metrics for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT metric, value FROM cash_flow_snapshots WHERE period_date = %s",
            (pd_str,))
    return {r["metric"]: r["value"] for r in rows}


def load_totals(period_date):
    """Load computed totals for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT metric, value FROM totals_snapshots WHERE period_date = %s",
            (pd_str,))
    return {r["metric"]: r["value"] for r in rows}


def load_transactions(period_date):
    """Load transactions for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        return _fetchall(conn,
            "SELECT * FROM transactions WHERE period_date = %s ORDER BY post_date",
            (pd_str,))


def load_journal_entries(period_date):
    """Load journal entries with their lines for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        entries = _fetchall(conn,
            "SELECT * FROM journal_entries WHERE period_date = %s ORDER BY entry_date",
            (pd_str,))
        result = []
        for entry in entries:
            lines = _fetchall(conn,
                "SELECT * FROM journal_entry_lines WHERE entry_id = %s",
                (entry["id"],))
            debits = {}
            credits = {}
            for line in lines:
                if line["debit_amount"] and line["debit_amount"] > 0:
                    debits[line["account"]] = line["debit_amount"]
                if line["credit_amount"] and line["credit_amount"] > 0:
                    credits[line["account"]] = line["credit_amount"]
            result.append({
                "date": date.fromisoformat(entry["entry_date"]),
                "description": entry["description"],
                "entry_type": entry["entry_type"],
                "debits": debits,
                "credits": credits,
            })
    return result


def load_all_journal_entries_through(period_date):
    """Load ALL journal entries from all periods through the given date."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        entries = _fetchall(conn,
            "SELECT * FROM journal_entries WHERE period_date <= %s ORDER BY entry_date",
            (pd_str,))
        result = []
        for entry in entries:
            lines = _fetchall(conn,
                "SELECT * FROM journal_entry_lines WHERE entry_id = %s",
                (entry["id"],))
            debits = {}
            credits = {}
            for line in lines:
                if line["debit_amount"] and line["debit_amount"] > 0:
                    debits[line["account"]] = line["debit_amount"]
                if line["credit_amount"] and line["credit_amount"] > 0:
                    credits[line["account"]] = line["credit_amount"]
            result.append({
                "date": date.fromisoformat(entry["entry_date"]),
                "description": entry["description"],
                "entry_type": entry["entry_type"],
                "debits": debits,
                "credits": credits,
            })
    return result


def load_distributions(period_date):
    """Load distribution amounts for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT investor_key, amount FROM distribution_snapshots WHERE period_date = %s",
            (pd_str,))
    return {r["investor_key"]: r["amount"] for r in rows}


def load_all_distributions():
    """Load all distribution snapshots across all periods."""
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT period_date, investor_key, amount FROM distribution_snapshots "
            "ORDER BY period_date")
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["investor_key"]] = r["amount"]
    return result


def load_all_balance_sheets():
    """Load balance sheets for all posted periods."""
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT period_date, account, amount FROM balance_sheet_snapshots "
            "ORDER BY period_date")
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["account"]] = r["amount"]
    return result


def load_all_income_statements():
    """Load income statements for all posted periods."""
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT period_date, account, amount FROM income_statement_snapshots "
            "ORDER BY period_date")
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["account"]] = r["amount"]
    return result


def load_all_cash_flows():
    """Load cash flow snapshots for all posted periods."""
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT period_date, metric, value FROM cash_flow_snapshots "
            "ORDER BY period_date")
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["metric"]] = r["value"]
    return result


def load_all_totals():
    """Load totals snapshots for all posted periods."""
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT period_date, metric, value FROM totals_snapshots "
            "ORDER BY period_date")
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["metric"]] = r["value"]
    return result


# --- Depreciation Tracking ---

def is_depreciation_posted(quarter_key):
    """Check if depreciation has been posted for a quarter."""
    with get_connection() as conn:
        row = _fetchone(conn,
            "SELECT 1 FROM depreciation_posted WHERE quarter_key = %s",
            (quarter_key,))
    return row is not None


def get_posted_depreciation():
    """Return all quarters with posted depreciation."""
    with get_connection() as conn:
        return _fetchall(conn,
            "SELECT * FROM depreciation_posted ORDER BY quarter_key")


def save_depreciation_posted(quarter_key, total_depreciation):
    """Record that depreciation has been posted for a quarter."""
    with get_connection() as conn:
        _execute(conn,
            "INSERT INTO depreciation_posted (quarter_key, posted_at, total_depreciation) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (quarter_key) DO UPDATE SET "
            "posted_at = EXCLUDED.posted_at, total_depreciation = EXCLUDED.total_depreciation",
            (quarter_key, datetime.now().isoformat(), total_depreciation))


def save_depreciation_journal_entry(quarter_end_date, entry):
    """Save a depreciation journal entry to the database."""
    pd_str = date(quarter_end_date.year, quarter_end_date.month, 1).isoformat()

    with get_connection() as conn:
        cur = conn.cursor()
        entry_date_str = quarter_end_date.isoformat()
        cur.execute(
            "INSERT INTO journal_entries (period_date, entry_date, description, entry_type) "
            "VALUES (%s, %s, %s, 'depreciation') RETURNING id",
            (pd_str, entry_date_str, entry["description"])
        )
        entry_id = cur.fetchone()[0]
        for acct, amt in entry.get("debits", {}).items():
            cur.execute(
                "INSERT INTO journal_entry_lines (entry_id, account, debit_amount) "
                "VALUES (%s, %s, %s)",
                (entry_id, acct, amt)
            )
        for acct, amt in entry.get("credits", {}).items():
            cur.execute(
                "INSERT INTO journal_entry_lines (entry_id, account, credit_amount) "
                "VALUES (%s, %s, %s)",
                (entry_id, acct, amt)
            )


# --- Year-End Close ---

def is_year_closed(year):
    """Check if a fiscal year has been closed and locked."""
    with get_connection() as conn:
        row = _fetchone(conn,
            "SELECT locked FROM year_end_close WHERE year = %s", (year,))
    return row is not None and row["locked"] == 1


def get_closed_years():
    """Return all closed years with their details."""
    with get_connection() as conn:
        return _fetchall(conn,
            "SELECT * FROM year_end_close ORDER BY year")


def save_year_close(year, cy_net_income, re_before, re_after):
    """Record a year-end close."""
    with get_connection() as conn:
        _execute(conn,
            "INSERT INTO year_end_close "
            "(year, closed_at, cy_net_income, retained_earnings_before, "
            "retained_earnings_after, locked) VALUES (%s, %s, %s, %s, %s, 1) "
            "ON CONFLICT (year) DO UPDATE SET "
            "closed_at = EXCLUDED.closed_at, cy_net_income = EXCLUDED.cy_net_income, "
            "retained_earnings_before = EXCLUDED.retained_earnings_before, "
            "retained_earnings_after = EXCLUDED.retained_earnings_after, "
            "locked = EXCLUDED.locked",
            (year, datetime.now().isoformat(), cy_net_income, re_before, re_after))


def get_year_close_prerequisites(year):
    """Check what's needed before a year can be closed."""
    with get_connection() as conn:
        rows = _fetchall(conn,
            "SELECT period_date FROM posted_periods WHERE period_date LIKE %s",
            ("{}-%-01".format(year),))

    posted_months = set()
    for r in rows:
        pd_obj = date.fromisoformat(r["period_date"])
        posted_months.add(pd_obj.month)

    months_missing = [m for m in range(1, 13) if m not in posted_months]

    depr_posted = []
    depr_missing = []
    for q in range(1, 5):
        qk = "Q{} {}".format(q, year)
        if is_depreciation_posted(qk):
            depr_posted.append(qk)
        else:
            depr_missing.append(qk)

    ready = len(months_missing) == 0 and len(depr_missing) == 0

    return {
        "ready": ready,
        "months_posted": sorted(posted_months),
        "months_missing": months_missing,
        "depreciation_posted": depr_posted,
        "depreciation_missing": depr_missing,
    }


# --- Cleared Alerts ---

def is_alert_cleared(alert_key):
    """Check if an alert has been cleared."""
    with get_connection() as conn:
        row = _fetchone(conn,
            "SELECT 1 FROM cleared_alerts WHERE alert_key = %s", (alert_key,))
    return row is not None


def clear_alert(alert_key):
    """Mark an alert as cleared."""
    with get_connection() as conn:
        _execute(conn,
            "INSERT INTO cleared_alerts (alert_key, cleared_at) VALUES (%s, %s) "
            "ON CONFLICT (alert_key) DO UPDATE SET cleared_at = EXCLUDED.cleared_at",
            (alert_key, datetime.now().isoformat()))


def get_cleared_alerts():
    """Return all cleared alert keys."""
    with get_connection() as conn:
        rows = _fetchall(conn, "SELECT alert_key FROM cleared_alerts")
    return set(r["alert_key"] for r in rows)


def unclear_alert(alert_key):
    """Re-activate a previously cleared alert."""
    with get_connection() as conn:
        _execute(conn,
            "DELETE FROM cleared_alerts WHERE alert_key = %s", (alert_key,))


def clear_all_alerts():
    """Clear all alerts."""
    with get_connection() as conn:
        _execute(conn, "DELETE FROM cleared_alerts")
