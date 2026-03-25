"""Calculate quarterly distributions based on FCF and ownership percentages."""

from config.fund_config import INVESTORS, LOAN, TOTAL_MONTHLY_RENT


def calculate_quarterly_distribution(quarterly_rent, quarterly_loan_payments):
    """Calculate distributable cash and per-investor amounts.

    Args:
        quarterly_rent: total rent collected in the quarter
        quarterly_loan_payments: total loan payments made in the quarter (3 x monthly)

    Returns:
        dict with 'total' and per-investor amounts
    """
    distributable_cash = quarterly_rent - quarterly_loan_payments

    result = {"total": round(distributable_cash, 2)}
    for inv_key, inv in INVESTORS.items():
        result[inv_key] = round(distributable_cash * inv["ownership_pct"], 2)

    return result


def calculate_fcf_from_transactions(classified_transactions):
    """Calculate FCF from a quarter's classified transactions.

    FCF = Total Rent Credits - Total Loan Payment Debits - Total Expense Debits
    (Distributions are separate from FCF)
    """
    rent_total = sum(
        (txn.get("credit", 0) or 0)
        for txn in classified_transactions
        if txn["category"] == "rent"
    )
    loan_total = sum(
        (txn.get("debit", 0) or 0)
        for txn in classified_transactions
        if txn["category"] == "loan_payment"
    )
    expense_total = sum(
        (txn.get("debit", 0) or 0)
        for txn in classified_transactions
        if txn["category"] in ("accounting_fees", "bank_fees", "other_expense")
    )
    expense_credits = sum(
        (txn.get("credit", 0) or 0)
        for txn in classified_transactions
        if txn["category"] in ("accounting_fees", "bank_fees", "other_expense")
    )

    return rent_total - loan_total - expense_total + expense_credits
