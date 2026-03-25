"""
12/31/2025 financial state — the starting point for all roll-forward calculations.
All values sourced from PQSR_Accounting Workbook_12.31.25.xlsx.
"""

from datetime import date

BASELINE_DATE = date(2025, 12, 31)

# Balance Sheet as of 12/31/2025
BALANCE_SHEET = {
    # ASSETS
    "Cash": 50056.34,

    # Fixed Assets (gross)
    "Land": 3551766.046947,
    "Building": 3817455.081285,
    "Land Improvements": 3499212.172023,
    "F&F": 629186.669229,
    "Equipment": 2887543.461102,
    "Signage": 213135.159414,

    # Accumulated Depreciation (negative values)
    "Building A/D": -203923.882547,
    "Land Improvements A/D": -486001.690559,
    "F&F A/D": -187257.937271,
    "Equipment A/D": -1203143.108793,
    "Signage A/D": -44403.158211,

    # Other Assets
    "Capitalized Origination Fee": 49750.00,
    "Accumulated Amortization": -2072.916667,

    # LIABILITIES
    "Note Payable - BBV": 9617873.286513,
    "Due to PSP Investments, LLC": 50056.34,
    "Deferred Rental Revenue": 0.00,

    # MEMBERS' EQUITY
    "Contributions - PSP Inv": 2623048.59,
    "Contributions - KCYUM": 1500000.00,
    "Contributions - Thengvall": 100000.00,
    "Contributions - Happ": 200000.00,
    "Contributions - FEND": 275000.00,

    "Distributions - PSP Inv": -177107.964091,
    "Distributions - KCYUM": -101279.842705,
    "Distributions - Thengvall": -6751.987514,
    "Distributions - Happ": -13503.975027,
    "Distributions - FEND": -18567.980663,

    "CY Net Income": -697215.189669,
    "Retained Earnings": -780248.983023,
}

# Income Statement for 2025 (will be rolled into Retained Earnings at year-end)
INCOME_STATEMENT_2025 = {
    "Rental Income": 969528.72,
    "Interest Expense": 645939.146526,
    "Appraisals": 0.00,
    "Accounting & Tax Fees": 1130.00,
    "Bank Fees": -195.53,
    "Taxes & Licenses": 0.00,
    "Survey Fees": 0.00,
    "Origination Fee - Amort": 0.00,
    "Depreciation Expense": 1019870.293143,
}

# Cash flow metrics for 2025
CASH_FLOW_2025 = {
    "EBITDA": 968594.25,
    "Interest Expense": -645939.146526,
    "Principal Payments": -171568.61954,
    "FCF": 151086.483934,
    "DSCR": 1.184814,
}

# Quarterly NOI history (for investor report trailing-12 display)
QUARTERLY_NOI = {
    "Q1 2025": 242612.645,
    "Q2 2025": 242377.115,
    "Q3 2025": 241226.705,
    "Q4 2025": 241482.285,
}

# Total distributions paid through 12/31/2025
TOTAL_DISTRIBUTIONS_THROUGH_BASELINE = 317211.75
