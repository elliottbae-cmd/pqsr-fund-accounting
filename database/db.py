"""SQLite database layer for persistent financial data storage."""

import sqlite3
import os
from datetime import date, datetime
from contextlib import contextmanager

# Database file lives next to the app, excluded from git via .gitignore
DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DB_DIR, "data", "pqsr_fund.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_connection():
    """Context manager for database connections."""
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS posted_periods (
                period_date TEXT PRIMARY KEY,
                period_type TEXT DEFAULT 'monthly',
                posted_at TEXT NOT NULL,
                quarter_end INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_date TEXT NOT NULL,
                post_date TEXT NOT NULL,
                description TEXT NOT NULL,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                category TEXT,
                property TEXT,
                investor TEXT,
                confidence TEXT,
                details TEXT,
                FOREIGN KEY (period_date) REFERENCES posted_periods(period_date)
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_date TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                description TEXT NOT NULL,
                entry_type TEXT DEFAULT 'monthly',
                FOREIGN KEY (period_date) REFERENCES posted_periods(period_date)
            );

            CREATE TABLE IF NOT EXISTS journal_entry_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                account TEXT NOT NULL,
                debit_amount REAL DEFAULT 0,
                credit_amount REAL DEFAULT 0,
                FOREIGN KEY (entry_id) REFERENCES journal_entries(id)
            );

            CREATE TABLE IF NOT EXISTS balance_sheet_snapshots (
                period_date TEXT NOT NULL,
                account TEXT NOT NULL,
                amount REAL NOT NULL,
                PRIMARY KEY (period_date, account)
            );

            CREATE TABLE IF NOT EXISTS income_statement_snapshots (
                period_date TEXT NOT NULL,
                account TEXT NOT NULL,
                amount REAL NOT NULL,
                PRIMARY KEY (period_date, account)
            );

            CREATE TABLE IF NOT EXISTS cash_flow_snapshots (
                period_date TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (period_date, metric)
            );

            CREATE TABLE IF NOT EXISTS totals_snapshots (
                period_date TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (period_date, metric)
            );

            CREATE TABLE IF NOT EXISTS distribution_snapshots (
                period_date TEXT NOT NULL,
                investor_key TEXT NOT NULL,
                amount REAL NOT NULL,
                PRIMARY KEY (period_date, investor_key)
            );

            CREATE TABLE IF NOT EXISTS depreciation_posted (
                quarter_key TEXT PRIMARY KEY,
                posted_at TEXT NOT NULL,
                total_depreciation REAL NOT NULL
            );
        """)


# --- Posted Periods ---

def get_posted_periods():
    """Return all posted periods sorted by date."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM posted_periods ORDER BY period_date"
        ).fetchall()
    return [dict(r) for r in rows]


def get_last_posted_period():
    """Return the most recently posted period date, or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT period_date FROM posted_periods ORDER BY period_date DESC LIMIT 1"
        ).fetchone()
    if row:
        return date.fromisoformat(row["period_date"])
    return None


def get_next_expected_month():
    """Determine the next month to process based on posted history.

    Returns a date for the first day of the next expected month.
    If nothing posted yet, returns January 2026 (first month after baseline).
    """
    from dateutil.relativedelta import relativedelta
    last = get_last_posted_period()
    if last is None:
        return date(2026, 1, 1)
    return date(last.year, last.month, 1) + relativedelta(months=1)


def is_period_posted(period_date):
    """Check if a period has been posted."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM posted_periods WHERE period_date = ?", (pd_str,)
        ).fetchone()
    return row is not None


# --- Save a Complete Period ---

def save_period(period_date, transactions, journal_entries, bs, is_accounts,
                cash_flow, totals, distributions=None):
    """Save all data for a posted period to the database.

    Args:
        period_date: date object for the period (first of month)
        transactions: list of classified transaction dicts
        journal_entries: list of AJE dicts with date, description, debits, credits
        bs: balance sheet dict
        is_accounts: income statement dict
        cash_flow: cash flow metrics dict
        totals: computed totals dict
        distributions: optional dict of investor_key -> amount for quarter-end
    """
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    is_qtr_end = period_date.month in (3, 6, 9, 12)

    with get_connection() as conn:
        # 1. Posted period record
        conn.execute(
            "INSERT OR REPLACE INTO posted_periods (period_date, period_type, posted_at, quarter_end) "
            "VALUES (?, 'monthly', ?, ?)",
            (pd_str, datetime.now().isoformat(), 1 if is_qtr_end else 0)
        )

        # 2. Transactions
        conn.execute("DELETE FROM transactions WHERE period_date = ?", (pd_str,))
        for txn in transactions:
            txn_date = txn.get("date", period_date)
            if hasattr(txn_date, "isoformat"):
                txn_date_str = txn_date.isoformat()
            elif hasattr(txn_date, "date"):
                txn_date_str = txn_date.date().isoformat()
            else:
                txn_date_str = str(txn_date)
            conn.execute(
                "INSERT INTO transactions "
                "(period_date, post_date, description, debit, credit, balance, "
                "category, property, investor, confidence, details) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pd_str, txn_date_str, txn.get("description", ""),
                 txn.get("debit", 0) or 0, txn.get("credit", 0) or 0,
                 txn.get("balance", 0) or 0,
                 txn.get("category"), txn.get("property"),
                 txn.get("investor"), txn.get("confidence"),
                 txn.get("details"))
            )

        # 3. Journal entries
        # Delete old NON-DEPRECIATION entries for this period.
        # Depreciation entries are managed separately via the Depreciation page
        # and must be preserved when a monthly period is re-posted.
        old_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM journal_entries WHERE period_date = ? AND entry_type != 'depreciation'",
            (pd_str,)
        ).fetchall()]
        if old_ids:
            placeholders = ",".join("?" * len(old_ids))
            conn.execute(
                "DELETE FROM journal_entry_lines WHERE entry_id IN ({})".format(placeholders),
                old_ids
            )
            conn.execute(
                "DELETE FROM journal_entries WHERE period_date = ? AND entry_type != 'depreciation'",
                (pd_str,)
            )

        for entry in journal_entries:
            entry_date = entry["date"]
            if hasattr(entry_date, "isoformat"):
                entry_date_str = entry_date.isoformat()
            else:
                entry_date_str = str(entry_date)
            entry_type = "depreciation" if "depreciation" in entry["description"].lower() else "monthly"
            cursor = conn.execute(
                "INSERT INTO journal_entries (period_date, entry_date, description, entry_type) "
                "VALUES (?, ?, ?, ?)",
                (pd_str, entry_date_str, entry["description"], entry_type)
            )
            entry_id = cursor.lastrowid
            for acct, amt in entry.get("debits", {}).items():
                conn.execute(
                    "INSERT INTO journal_entry_lines (entry_id, account, debit_amount) "
                    "VALUES (?, ?, ?)",
                    (entry_id, acct, amt)
                )
            for acct, amt in entry.get("credits", {}).items():
                conn.execute(
                    "INSERT INTO journal_entry_lines (entry_id, account, credit_amount) "
                    "VALUES (?, ?, ?)",
                    (entry_id, acct, amt)
                )

        # 4. Balance sheet snapshot
        conn.execute("DELETE FROM balance_sheet_snapshots WHERE period_date = ?", (pd_str,))
        for acct, amt in bs.items():
            conn.execute(
                "INSERT INTO balance_sheet_snapshots (period_date, account, amount) VALUES (?, ?, ?)",
                (pd_str, acct, amt)
            )

        # 5. Income statement snapshot
        conn.execute("DELETE FROM income_statement_snapshots WHERE period_date = ?", (pd_str,))
        for acct, amt in is_accounts.items():
            conn.execute(
                "INSERT INTO income_statement_snapshots (period_date, account, amount) VALUES (?, ?, ?)",
                (pd_str, acct, amt)
            )

        # 6. Cash flow snapshot
        conn.execute("DELETE FROM cash_flow_snapshots WHERE period_date = ?", (pd_str,))
        for metric, val in cash_flow.items():
            conn.execute(
                "INSERT INTO cash_flow_snapshots (period_date, metric, value) VALUES (?, ?, ?)",
                (pd_str, metric, val)
            )

        # 7. Totals snapshot
        conn.execute("DELETE FROM totals_snapshots WHERE period_date = ?", (pd_str,))
        for metric, val in totals.items():
            conn.execute(
                "INSERT INTO totals_snapshots (period_date, metric, value) VALUES (?, ?, ?)",
                (pd_str, metric, val)
            )

        # 8. Distribution snapshot (quarter-end only)
        if distributions:
            conn.execute("DELETE FROM distribution_snapshots WHERE period_date = ?", (pd_str,))
            for inv_key, amt in distributions.items():
                # Skip the "total" key — only store actual investor allocations
                if inv_key == "total":
                    continue
                conn.execute(
                    "INSERT INTO distribution_snapshots (period_date, investor_key, amount) "
                    "VALUES (?, ?, ?)",
                    (pd_str, inv_key, amt)
                )


# --- Load Period Data ---

def load_balance_sheet(period_date):
    """Load balance sheet for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT account, amount FROM balance_sheet_snapshots WHERE period_date = ?",
            (pd_str,)
        ).fetchall()
    return {r["account"]: r["amount"] for r in rows}


def load_income_statement(period_date):
    """Load income statement for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT account, amount FROM income_statement_snapshots WHERE period_date = ?",
            (pd_str,)
        ).fetchall()
    return {r["account"]: r["amount"] for r in rows}


def load_cash_flow(period_date):
    """Load cash flow metrics for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT metric, value FROM cash_flow_snapshots WHERE period_date = ?",
            (pd_str,)
        ).fetchall()
    return {r["metric"]: r["value"] for r in rows}


def load_totals(period_date):
    """Load computed totals for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT metric, value FROM totals_snapshots WHERE period_date = ?",
            (pd_str,)
        ).fetchall()
    return {r["metric"]: r["value"] for r in rows}


def load_transactions(period_date):
    """Load transactions for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE period_date = ? ORDER BY post_date",
            (pd_str,)
        ).fetchall()
    return [dict(r) for r in rows]


def load_journal_entries(period_date):
    """Load journal entries with their lines for a period."""
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        entries = conn.execute(
            "SELECT * FROM journal_entries WHERE period_date = ? ORDER BY entry_date",
            (pd_str,)
        ).fetchall()
        result = []
        for entry in entries:
            lines = conn.execute(
                "SELECT * FROM journal_entry_lines WHERE entry_id = ?",
                (entry["id"],)
            ).fetchall()
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
    """Load ALL journal entries from all periods through the given date.

    This is needed for roll-forward calculations that build from baseline.
    """
    pd_str = period_date.isoformat() if isinstance(period_date, date) else period_date
    with get_connection() as conn:
        entries = conn.execute(
            "SELECT * FROM journal_entries WHERE period_date <= ? ORDER BY entry_date",
            (pd_str,)
        ).fetchall()
        result = []
        for entry in entries:
            lines = conn.execute(
                "SELECT * FROM journal_entry_lines WHERE entry_id = ?",
                (entry["id"],)
            ).fetchall()
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
        rows = conn.execute(
            "SELECT investor_key, amount FROM distribution_snapshots WHERE period_date = ?",
            (pd_str,)
        ).fetchall()
    return {r["investor_key"]: r["amount"] for r in rows}


def load_all_distributions():
    """Load all distribution snapshots across all periods."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT period_date, investor_key, amount FROM distribution_snapshots "
            "ORDER BY period_date"
        ).fetchall()
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["investor_key"]] = r["amount"]
    return result


def load_all_balance_sheets():
    """Load balance sheets for all posted periods, keyed by period_date string."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT period_date, account, amount FROM balance_sheet_snapshots "
            "ORDER BY period_date"
        ).fetchall()
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["account"]] = r["amount"]
    return result


def load_all_income_statements():
    """Load income statements for all posted periods, keyed by period_date string."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT period_date, account, amount FROM income_statement_snapshots "
            "ORDER BY period_date"
        ).fetchall()
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["account"]] = r["amount"]
    return result


def load_all_cash_flows():
    """Load cash flow snapshots for all posted periods, keyed by period_date string."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT period_date, metric, value FROM cash_flow_snapshots "
            "ORDER BY period_date"
        ).fetchall()
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["metric"]] = r["value"]
    return result


def load_all_totals():
    """Load totals snapshots for all posted periods, keyed by period_date string."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT period_date, metric, value FROM totals_snapshots "
            "ORDER BY period_date"
        ).fetchall()
    result = {}
    for r in rows:
        pd = r["period_date"]
        if pd not in result:
            result[pd] = {}
        result[pd][r["metric"]] = r["value"]
    return result


# --- Depreciation Tracking ---

def is_depreciation_posted(quarter_key):
    """Check if depreciation has been posted for a quarter (e.g., 'Q1 2026')."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM depreciation_posted WHERE quarter_key = ?",
            (quarter_key,)
        ).fetchone()
    return row is not None


def get_posted_depreciation():
    """Return all quarters with posted depreciation."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM depreciation_posted ORDER BY quarter_key"
        ).fetchall()
    return [dict(r) for r in rows]


def save_depreciation_posted(quarter_key, total_depreciation):
    """Record that depreciation has been posted for a quarter."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO depreciation_posted "
            "(quarter_key, posted_at, total_depreciation) VALUES (?, ?, ?)",
            (quarter_key, datetime.now().isoformat(), total_depreciation)
        )


def save_depreciation_journal_entry(quarter_end_date, entry):
    """Save a depreciation journal entry to the database.

    The entry is stored under the quarter-end month's period_date.
    """
    pd_str = date(quarter_end_date.year, quarter_end_date.month, 1).isoformat()

    with get_connection() as conn:
        entry_date_str = quarter_end_date.isoformat()
        cursor = conn.execute(
            "INSERT INTO journal_entries (period_date, entry_date, description, entry_type) "
            "VALUES (?, ?, ?, 'depreciation')",
            (pd_str, entry_date_str, entry["description"])
        )
        entry_id = cursor.lastrowid
        for acct, amt in entry.get("debits", {}).items():
            conn.execute(
                "INSERT INTO journal_entry_lines (entry_id, account, debit_amount) "
                "VALUES (?, ?, ?)",
                (entry_id, acct, amt)
            )
        for acct, amt in entry.get("credits", {}).items():
            conn.execute(
                "INSERT INTO journal_entry_lines (entry_id, account, credit_amount) "
                "VALUES (?, ?, ?)",
                (entry_id, acct, amt)
            )
