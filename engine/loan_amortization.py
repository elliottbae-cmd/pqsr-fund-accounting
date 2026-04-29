"""Loan amortization schedule and interest/principal split lookups."""

from datetime import date
from dateutil.relativedelta import relativedelta
from config.fund_config import LOAN


def generate_amortization_schedule():
    """Generate the full amortization schedule from origination to maturity.

    Uses the implied monthly rate from the workbook's first interest payment
    (55,148.796296 on 9,950,000) to exactly match the original amortization.
    """
    balance = LOAN["original_amount"]
    # Derive exact monthly rate from the workbook's first interest calculation
    # rather than simple annual_rate/12, to match the bank's computation method
    first_interest = 55148.796296
    monthly_rate = first_interest / LOAN["original_amount"]
    payment = LOAN["monthly_payment"]
    payment_date = LOAN["first_payment_date"]
    schedule = []

    while balance > 0.01 and payment_date <= LOAN["maturity_date"]:
        interest = balance * monthly_rate
        principal = payment - interest
        balance -= principal
        schedule.append({
            "payment_date": payment_date,
            "beginning_balance": balance + principal,
            "interest": interest,
            "principal": principal,
            "payment": payment,
            "ending_balance": balance,
        })
        payment_date += relativedelta(months=1)

    return schedule


def get_payment_for_date(schedule, target_date):
    """Find the amortization entry closest to a given date.

    Loan payments post on the 20th of each month, but the amort schedule
    uses the 19th. Match by year-month.
    """
    for entry in schedule:
        if (entry["payment_date"].year == target_date.year
                and entry["payment_date"].month == target_date.month):
            return entry
    return None


def get_payments_for_quarter(schedule, year, quarter):
    """Return the 3 amortization entries for a given quarter."""
    month_start = (quarter - 1) * 3 + 1
    months = [month_start, month_start + 1, month_start + 2]
    return [
        entry for entry in schedule
        if entry["payment_date"].year == year
        and entry["payment_date"].month in months
    ]


def get_ending_balance_at_date(schedule, target_date):
    """Get the loan balance as of a given date."""
    last_entry = None
    for entry in schedule:
        if entry["payment_date"] <= target_date:
            last_entry = entry
        else:
            break
    return last_entry["ending_balance"] if last_entry else LOAN["original_amount"]


def get_total_principal_paid(schedule, through_date):
    """Get total principal paid through a given date."""
    return sum(
        entry["principal"] for entry in schedule
        if entry["payment_date"] <= through_date
    )


def get_ytd_principal_paid(schedule, year, through_date):
    """Get year-to-date principal paid for a given year through a given date.

    Used to match the YTD income statement when computing DSCR/FCF for
    interim periods. The IS in roll_forward() is YTD, so principal must
    also be YTD for consistent ratios.
    """
    return sum(
        entry["principal"] for entry in schedule
        if entry["payment_date"].year == year
        and entry["payment_date"] <= through_date
    )


def get_ytd_interest_paid(schedule, year, through_date):
    """Get year-to-date interest paid for a given year through a given date."""
    return sum(
        entry["interest"] for entry in schedule
        if entry["payment_date"].year == year
        and entry["payment_date"] <= through_date
    )
