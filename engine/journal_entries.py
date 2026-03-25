"""Generate double-entry journal entries from classified bank transactions."""

from datetime import date
from engine.loan_amortization import generate_amortization_schedule, get_payment_for_date
from engine.depreciation import get_quarterly_depreciation
from config.fund_config import PROPERTIES, LOAN


def generate_monthly_ajes(classified_transactions, month_date):
    """Generate journal entries for a month's classified transactions.

    Args:
        classified_transactions: list of classified bank transactions for one month
        month_date: date object for the month (e.g., date(2026, 1, 1))

    Returns:
        list of journal entry dicts, each with:
            date, description, debits: {account: amount}, credits: {account: amount}
    """
    entries = []
    amort_schedule = generate_amortization_schedule()

    # Group transactions by type for the monthly entry
    rent_total = 0.0
    rent_details = []
    loan_payment = None
    distributions = {}
    expenses = {}
    cash_in = 0.0
    cash_out = 0.0

    for txn in classified_transactions:
        credit = txn.get("credit", 0) or 0
        debit = txn.get("debit", 0) or 0

        if txn["category"] == "rent":
            rent_total += credit
            prop = PROPERTIES.get(txn["property"], {})
            rent_details.append(f"{prop.get('name', 'Unknown')}: ${credit:,.2f}")

        elif txn["category"] == "loan_payment":
            payment_entry = get_payment_for_date(amort_schedule, month_date)
            if payment_entry:
                loan_payment = payment_entry

        elif txn["category"] == "distribution":
            inv_key = txn["investor"]
            distributions[inv_key] = distributions.get(inv_key, 0) + debit

        elif txn["category"] == "accounting_fees":
            # Net debits and credits for multi-fund invoices
            if debit > 0:
                expenses["Accounting & Tax Fees"] = expenses.get("Accounting & Tax Fees", 0) + debit
            if credit > 0:
                expenses["Accounting & Tax Fees"] = expenses.get("Accounting & Tax Fees", 0) - credit

        elif txn["category"] == "bank_fees":
            if debit > 0:
                expenses["Bank Fees"] = expenses.get("Bank Fees", 0) + debit
            if credit > 0:
                expenses["Bank Fees"] = expenses.get("Bank Fees", 0) - credit

        elif txn["category"] != "unknown":
            # Other categorized expenses
            cat = txn.get("expense_category", txn["category"])
            if debit > 0:
                expenses[cat] = expenses.get(cat, 0) + debit
            if credit > 0:
                expenses[cat] = expenses.get(cat, 0) - credit

    # Build the monthly journal entry
    debits = {}
    credits = {}
    month_name = month_date.strftime("%B")

    # Cash from rent
    if rent_total > 0:
        debits["Cash"] = rent_total
        credits["Rental Income"] = rent_total

    # Loan payment
    if loan_payment:
        debits["Interest Expense"] = loan_payment["interest"]
        debits["Note Payable - BBV"] = loan_payment["principal"]
        credits["Cash"] = credits.get("Cash", 0) + LOAN["monthly_payment"]

    # Distributions
    for inv_key, amount in distributions.items():
        debits[f"Distributions - {inv_key}"] = amount
        credits["Cash"] = credits.get("Cash", 0) + amount

    # Expenses
    for exp_name, amount in expenses.items():
        if amount > 0:
            debits[exp_name] = amount
            credits["Cash"] = credits.get("Cash", 0) + amount
        elif amount < 0:
            # Net credit (e.g., refund exceeds expense)
            debits["Cash"] = debits.get("Cash", 0) + abs(amount)
            credits[exp_name] = abs(amount)

    entry = {
        "date": month_date,
        "description": f"To record {month_name} Activity",
        "debits": debits,
        "credits": credits,
    }
    entries.append(entry)

    return entries


def generate_depreciation_aje(quarter_end_date):
    """Generate the quarterly depreciation journal entry."""
    debits, credits = get_quarterly_depreciation()
    quarter_num = (quarter_end_date.month - 1) // 3 + 1
    return {
        "date": quarter_end_date,
        "description": f"To record Q{quarter_num} book depreciation",
        "debits": debits,
        "credits": credits,
    }
