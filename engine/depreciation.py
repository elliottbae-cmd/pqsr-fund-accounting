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
            credits["{} A/D".format(asset_class)] = info["quarterly_depreciation"]
    return debits, credits


def get_accumulated_depreciation_at_quarter(quarters_since_inception):
    """Get accumulated depreciation by class after N quarters.

    Inception = Q4 2023 (partial), then full quarters starting Q1 2024.
    The FA Schedule already accounts for the partial first quarter.
    """
    result = {}
    for asset_class, info in FIXED_ASSETS.items():
        if info["quarterly_depreciation"] > 0:
            result["{} A/D".format(asset_class)] = -(
                info["quarterly_depreciation"] * quarters_since_inception
            )
    return result


def is_quarter_end(d):
    """Check if a date is the last day of a quarter."""
    return d.month in (3, 6, 9, 12) and d == _last_day_of_month(d)


def _last_day_of_month(d):
    from calendar import monthrange
    return d.replace(day=monthrange(d.year, d.month)[1])


def generate_fa_schedule(through_date, baseline_ad=None):
    """Generate the full fixed asset schedule from inception through a given date.

    Returns a dict with:
        - asset_classes: list of asset class info dicts
        - depreciation_by_year: {year: {asset_class: annual_depr_amount}}
        - accum_depr_by_year: {year: {asset_class: cumulative_ad_amount}}
        - total_purchase_price: total cost basis
        - summary: per-class summary with cost, useful life, annual depr, current A/D, NBV

    Args:
        through_date: date to calculate through
        baseline_ad: dict of baseline A/D values from 12/31/2025 (optional)
    """
    from config.fund_config import TOTAL_PURCHASE_PRICE
    from config.baseline_data import BALANCE_SHEET

    if baseline_ad is None:
        baseline_ad = {
            k: abs(v) for k, v in BALANCE_SHEET.items() if "A/D" in k
        }

    # Inception: 10/19/2023, first full year of depreciation: 2024
    inception_year = 2023
    through_year = through_date.year

    # Partial first year (2023): ~73 days / 365 = 0.2 of annual depreciation
    # We back-calculate from baseline to get the exact 2023 amount
    # Baseline is 12/31/2025, which includes 2023(partial) + 2024(full) + 2025(full)
    asset_classes = []
    depreciation_by_year = {}
    accum_depr_by_year = {}

    for year in range(inception_year, through_year + 1):
        depreciation_by_year[year] = {}
        accum_depr_by_year[year] = {}

    for asset_class, info in FIXED_ASSETS.items():
        if info["useful_life"] is None:
            # Land — no depreciation
            asset_classes.append({
                "class": asset_class,
                "cost_seg_pct": info["cost_seg_pct"],
                "amount": info["amount"],
                "useful_life": "N/A",
                "annual_depreciation": 0,
                "quarterly_depreciation": 0,
            })
            for year in range(inception_year, through_year + 1):
                depreciation_by_year[year][asset_class] = 0
                accum_depr_by_year[year][asset_class] = 0
            continue

        annual_depr = info["annual_depreciation"]
        quarterly_depr = info["quarterly_depreciation"]
        ad_key = "{} A/D".format(asset_class)

        # Back-calculate 2023 partial year from baseline
        # Baseline A/D = 2023_partial + 2024_full + 2025_full
        baseline_val = baseline_ad.get(ad_key, 0)
        depr_2024_2025 = annual_depr * 2
        depr_2023 = baseline_val - depr_2024_2025
        if depr_2023 < 0:
            depr_2023 = 0

        asset_classes.append({
            "class": asset_class,
            "cost_seg_pct": info["cost_seg_pct"],
            "amount": info["amount"],
            "useful_life": info["useful_life"],
            "annual_depreciation": annual_depr,
            "quarterly_depreciation": quarterly_depr,
        })

        cumulative = 0
        for year in range(inception_year, through_year + 1):
            if year == inception_year:
                year_depr = depr_2023
            elif year <= inception_year + int(info["useful_life"]):
                # Check if this is a partial final year
                final_year = inception_year + int(info["useful_life"])
                if year == final_year:
                    # Remaining depreciation
                    remaining = info["amount"] - cumulative
                    year_depr = min(annual_depr, remaining) if remaining > 0 else 0
                else:
                    year_depr = annual_depr
            else:
                year_depr = 0

            # For the current year if not yet complete, prorate by quarters posted
            if year == through_date.year and through_date.month < 12:
                quarters_in_year = (through_date.month - 1) // 3 + 1
                if year == inception_year:
                    year_depr = depr_2023  # Partial first year is what it is
                else:
                    year_depr = quarterly_depr * quarters_in_year

            cumulative += year_depr
            # Don't exceed cost basis
            if cumulative > info["amount"]:
                year_depr -= (cumulative - info["amount"])
                cumulative = info["amount"]

            depreciation_by_year[year][asset_class] = year_depr
            accum_depr_by_year[year][asset_class] = cumulative

    # Build summary
    summary = []
    for ac in asset_classes:
        asset_class = ac["class"]
        current_ad = accum_depr_by_year.get(through_year, {}).get(asset_class, 0)
        nbv = ac["amount"] - current_ad
        summary.append({
            "class": asset_class,
            "cost_seg_pct": ac["cost_seg_pct"],
            "amount": ac["amount"],
            "useful_life": ac["useful_life"],
            "annual_depreciation": ac["annual_depreciation"],
            "current_ad": current_ad,
            "nbv": nbv,
        })

    return {
        "asset_classes": asset_classes,
        "depreciation_by_year": depreciation_by_year,
        "accum_depr_by_year": accum_depr_by_year,
        "total_purchase_price": TOTAL_PURCHASE_PRICE,
        "summary": summary,
        "years": list(range(inception_year, through_year + 1)),
    }
