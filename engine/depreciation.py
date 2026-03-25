"""Quarterly depreciation calculations by asset class."""

from config.fund_config import FIXED_ASSETS, TOTAL_QUARTERLY_DEPRECIATION


def get_quarterly_depreciation():
    """Return depreciation entries for one quarter.

    Returns a dict of {account: amount} for the depreciation journal entry.
    """
    debits = {"Depreciation Expense": TOTAL_QUARTERLY_DEPRECIATION}
    credits = {}
    for asset_class, info in FIXED_ASSETS.items():
        if info["quarterly_depreciation"] > 0:
            credits[f"{asset_class} A/D"] = info["quarterly_depreciation"]
    return debits, credits


def get_accumulated_depreciation_at_quarter(quarters_since_inception):
    """Get accumulated depreciation by class after N quarters.

    Inception = Q4 2023 (partial), then full quarters starting Q1 2024.
    The FA Schedule already accounts for the partial first quarter.
    """
    result = {}
    for asset_class, info in FIXED_ASSETS.items():
        if info["quarterly_depreciation"] > 0:
            result[f"{asset_class} A/D"] = -(
                info["quarterly_depreciation"] * quarters_since_inception
            )
    return result


def is_quarter_end(d):
    """Check if a date is the last day of a quarter."""
    return d.month in (3, 6, 9, 12) and d == _last_day_of_month(d)


def _last_day_of_month(d):
    from calendar import monthrange
    return d.replace(day=monthrange(d.year, d.month)[1])
