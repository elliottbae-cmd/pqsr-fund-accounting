"""Roll forward financial statements from baseline using journal entries."""

import copy
from datetime import date
from config.baseline_data import BALANCE_SHEET, BASELINE_DATE
from config.fund_config import FIXED_ASSETS, INVESTORS

# Define debit sign for each BS account based on storage convention.
# +1 means a debit ADDs to the stored value; -1 means a debit SUBTRACTs.
# Credits are always the opposite sign.
DEBIT_SIGN = {
    # Assets (stored positive): debit increases
    "Cash": 1,
    "Land": 1, "Building": 1, "Land Improvements": 1,
    "F&F": 1, "Equipment": 1, "Signage": 1,
    "Capitalized Origination Fee": 1,

    # Contra-assets / A/D (stored negative): debit makes less negative (add)
    "Building A/D": 1, "Land Improvements A/D": 1, "F&F A/D": 1,
    "Equipment A/D": 1, "Signage A/D": 1, "Accumulated Amortization": 1,

    # Liabilities (stored positive): debit decreases (subtract)
    "Note Payable - BBV": -1,
    "Due to PSP Investments, LLC": -1,
    "Deferred Rental Revenue": -1,

    # Equity - contributions (stored positive): debit decreases
    "Contributions - PSP Inv": -1, "Contributions - KCYUM": -1,
    "Contributions - Thengvall": -1, "Contributions - Happ": -1,
    "Contributions - FEND": -1,

    # Contra-equity - distributions (stored negative): debit makes more negative
    "Distributions - PSP Inv": -1, "Distributions - KCYUM": -1,
    "Distributions - Thengvall": -1, "Distributions - Happ": -1,
    "Distributions - FEND": -1,

    # Retained Earnings / CY Net Income (stored negative for losses)
    "Retained Earnings": -1,
    "CY Net Income": -1,
}

# Income statement accounts (not on BS, tracked separately)
IS_ACCOUNTS = {
    "Rental Income", "Interest Expense", "Accounting & Tax Fees",
    "Bank Fees", "Appraisals", "Taxes & Licenses", "Survey Fees",
    "Origination Fee - Amort", "Depreciation Expense", "Other",
}

# Revenue accounts get credit = positive in IS
IS_REVENUE = {"Rental Income"}


def roll_forward(journal_entries, as_of_date):
    """Apply journal entries to the baseline balance sheet.

    Returns:
        balance_sheet: dict of account balances
        income_statement: dict of revenue/expense totals for current year
    """
    bs = copy.deepcopy(BALANCE_SHEET)
    is_accts = {name: 0.0 for name in IS_ACCOUNTS}
    current_year = BASELINE_DATE.year

    for entry in sorted(journal_entries, key=lambda e: e["date"]):
        # Year-end roll: move CY Net Income into Retained Earnings
        # Use while loop to handle multi-year gaps (e.g., no entries in 2027)
        while entry["date"].year > current_year:
            bs["Retained Earnings"] += bs["CY Net Income"]
            bs["CY Net Income"] = 0.0
            current_year += 1

        # Apply debits
        for account, amount in entry["debits"].items():
            if account in IS_ACCOUNTS:
                # Expenses: debit increases expense (positive value)
                if account not in IS_REVENUE:
                    is_accts[account] += amount
                else:
                    is_accts[account] -= amount
            if account in DEBIT_SIGN:
                bs[account] += DEBIT_SIGN[account] * amount

        # Apply credits
        for account, amount in entry["credits"].items():
            if account in IS_ACCOUNTS:
                # Revenue: credit increases revenue (positive value)
                if account in IS_REVENUE:
                    is_accts[account] += amount
                else:
                    is_accts[account] -= amount
            if account in DEBIT_SIGN:
                # Credit is opposite of debit
                bs[account] -= DEBIT_SIGN[account] * amount

        # Update CY Net Income from IS
        revenue = sum(is_accts[k] for k in IS_REVENUE)
        expenses = sum(is_accts[k] for k in IS_ACCOUNTS if k not in IS_REVENUE)
        bs["CY Net Income"] = -(expenses - revenue)  # negative when loss

    return bs, is_accts


def compute_totals(bs):
    """Compute summary totals from the balance sheet."""
    fa_gross = sum(bs.get(k, 0) for k in [
        "Land", "Building", "Land Improvements", "F&F", "Equipment", "Signage"
    ])
    fa_ad = sum(bs.get(k, 0) for k in [
        "Building A/D", "Land Improvements A/D", "F&F A/D", "Equipment A/D", "Signage A/D"
    ])
    total_fa_net = fa_gross + fa_ad

    total_other = bs["Capitalized Origination Fee"] + bs["Accumulated Amortization"]
    total_assets = bs["Cash"] + total_fa_net + total_other

    total_liabilities = (
        bs["Note Payable - BBV"]
        + bs["Due to PSP Investments, LLC"]
        + bs["Deferred Rental Revenue"]
    )

    equity_items = (
        sum(bs.get("Contributions - {}".format(k), 0) for k in INVESTORS)
        + sum(bs.get("Distributions - {}".format(k), 0) for k in INVESTORS)
        + bs["CY Net Income"]
        + bs["Retained Earnings"]
    )

    return {
        "total_fa_net": total_fa_net,
        "total_other_assets": total_other,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": equity_items,
        "total_liabilities_equity": total_liabilities + equity_items,
    }


def compute_cash_flow_metrics(is_accounts, quarterly_principal):
    """Compute EBITDA, FCF, and DSCR from income statement data.

    EBITDA = Revenue - Operating Expenses (excludes Interest, Depreciation, and Amortization)
    """
    revenue = is_accounts.get("Rental Income", 0)
    depreciation = is_accounts.get("Depreciation Expense", 0)
    interest = is_accounts.get("Interest Expense", 0)
    amortization = is_accounts.get("Origination Fee - Amort", 0)

    # Operating expenses = everything except Revenue, Interest, Depreciation, and Amortization
    non_ebitda_accounts = {
        "Rental Income", "Depreciation Expense", "Interest Expense",
        "Origination Fee - Amort",
    }
    other_expenses = sum(
        is_accounts.get(k, 0) for k in is_accounts
        if k not in non_ebitda_accounts
    )

    ebitda = revenue - other_expenses
    fcf = ebitda - interest - quarterly_principal
    debt_service = interest + quarterly_principal
    dscr = ebitda / debt_service if debt_service > 0 else 0

    return {
        "EBITDA": ebitda,
        "Interest Expense": interest,
        "Principal Payments": quarterly_principal,
        "FCF": fcf,
        "DSCR": dscr,
        "Net Income": revenue - interest - other_expenses - depreciation - amortization,
    }
