from datetime import date

FUND_NAME = "PQSR Fund I, LLC"
FUND_INCEPTION_DATE = date(2023, 10, 19)

# --- Properties ---
PROPERTIES = {
    "nacogdoches": {
        "name": "Nacogdoches",
        "psf_code": "PSF 271",
        "monthly_rent": 16250.00,
        "opening_date": date(2023, 10, 3),
        "first_bump_date": date(2028, 11, 1),
    },
    "gallup": {
        "name": "Gallup",
        "psf_code": "PSF 214",
        "monthly_rent": 14583.333333,
        "opening_date": date(2023, 4, 19),
        "first_bump_date": date(2028, 5, 1),
        "tenant": "Legacy Chicken (Popeyes)",
    },
    "fairfield": {
        "name": "Fairfield",
        "psf_code": "PSF 256",
        "monthly_rent": 18066.3075,
        "opening_date": date(2024, 2, 13),
        "first_bump_date": date(2029, 3, 1),
    },
    "beavercreek": {
        "name": "Beavercreek",
        "psf_code": "PSF 223",
        "monthly_rent": 16012.340833,
        "opening_date": date(2023, 10, 19),
        "first_bump_date": date(2028, 11, 1),
    },
    "loveland": {
        "name": "Loveland",
        "psf_code": "PSF 231",
        "monthly_rent": 15882.076667,
        "opening_date": date(2023, 4, 4),
        "first_bump_date": date(2028, 5, 1),
    },
}

TOTAL_MONTHLY_RENT = sum(p["monthly_rent"] for p in PROPERTIES.values())

# --- Investors ---
INVESTORS = {
    "PSP Inv": {
        "full_name": "PSP Investments, LLC",
        "ownership_pct": 0.558328,
        "contribution": 2623048.59,
    },
    "KCYUM": {
        "full_name": "KCYUM",
        "ownership_pct": 0.319281,
        "contribution": 1500000.00,
    },
    "FEND": {
        "full_name": "FEND QSR 1, LLC",
        "ownership_pct": 0.058535,
        "contribution": 275000.00,
    },
    "Thengvall": {
        "full_name": "AT",
        "ownership_pct": 0.021285,
        "contribution": 100000.00,
    },
    "Happ": {
        "full_name": "CCH",
        "ownership_pct": 0.042571,
        "contribution": 200000.00,
    },
}

# Report display names (investor key -> report display name)
INVESTOR_REPORT_NAMES = {
    "PSP Inv": "PSP Inv.",
    "KCYUM": "KCYUM",
    "FEND": "FEND",
    "Thengvall": "AT",
    "Happ": "CCH",
}

# --- Loan Terms ---
LOAN = {
    "original_amount": 9950000.00,
    "annual_rate": 0.0665,
    "monthly_payment": 68125.647172,
    "origination_date": date(2024, 1, 19),
    "maturity_date": date(2028, 12, 31),
    "first_payment_date": date(2024, 1, 19),
    "lender": "BBV",
    "origination_fee_quarterly_amort": 497.50,
}

# --- Origination Fee ---
ORIGINATION_FEE = {
    "amount": 49750.00,
    "amortization_start": date(2024, 1, 19),
    "amortization_end": date(2048, 12, 31),
    "annual_amortization": 1990.00,
    "quarterly_amortization": 497.50,
    "accumulated_amortization_12_31_2025": 2072.916667,
}

# --- Fixed Assets & Depreciation ---
FIXED_ASSETS = {
    "Land": {
        "cost_seg_pct": 0.2433,
        "amount": 3551766.046947,
        "useful_life": None,
        "annual_depreciation": 0.0,
        "quarterly_depreciation": 0.0,
    },
    "Building": {
        "cost_seg_pct": 0.2615,
        "amount": 3817455.081285,
        "useful_life": 39,
        "annual_depreciation": 97883.463623,
        "quarterly_depreciation": 24470.865906,
    },
    "Land Improvements": {
        "cost_seg_pct": 0.2397,
        "amount": 3499212.172023,
        "useful_life": 15,
        "annual_depreciation": 233280.811468,
        "quarterly_depreciation": 58320.202867,
    },
    "F&F": {
        "cost_seg_pct": 0.0431,
        "amount": 629186.669229,
        "useful_life": 7,
        "annual_depreciation": 89883.80989,
        "quarterly_depreciation": 22470.952472,
    },
    "Equipment": {
        "cost_seg_pct": 0.1978,
        "amount": 2887543.461102,
        "useful_life": 5,
        "annual_depreciation": 577508.69222,
        "quarterly_depreciation": 144377.173055,
    },
    "Signage": {
        "cost_seg_pct": 0.0146,
        "amount": 213135.159414,
        "useful_life": 10,
        "annual_depreciation": 21313.515941,
        "quarterly_depreciation": 5328.378985,
    },
}

TOTAL_QUARTERLY_DEPRECIATION = sum(
    a["quarterly_depreciation"] for a in FIXED_ASSETS.values()
)

TOTAL_PURCHASE_PRICE = 14598298.59

# --- Fair Market Value (updated quarterly by user in investor notes) ---
# These are the most recent FMV estimates; can be overridden in the app
FMV_ASSETS = 15764694.00

# --- Due to PSP Investments, LLC ---
# This tracks the management fee / cash held on behalf of PSP
DUE_TO_PSP_INITIAL = 50056.34

# --- Expense Categories ---
EXPENSE_CATEGORIES = [
    "Accounting & Tax Fees",
    "Bank Fees",
    "Appraisals",
    "Taxes & Licenses",
    "Survey Fees",
    "Other",
]

# --- Distribution History (pre-baseline) ---
DISTRIBUTION_HISTORY = {
    "Total 2024 Distr.": {
        "total": 166125.30,
        "PSP Inv": 92752.283332,
        "KCYUM": 53040.734941,
        "FEND": 9724.134739,
        "Thengvall": 3536.048996,
        "Happ": 7072.097992,
    },
    "Q1 2025": {
        "total": 38235.76,
        "PSP Inv": 21348.067061,
        "KCYUM": 12207.970799,
        "FEND": 2238.12798,
        "Thengvall": 813.86472,
        "Happ": 1627.72944,
    },
    "Q2 2025": {
        "total": 36870.23,
        "PSP Inv": 20585.65444,
        "KCYUM": 11771.982333,
        "FEND": 2158.196761,
        "Thengvall": 784.798822,
        "Happ": 1569.597644,
    },
    "Q3 2025": {
        "total": 37980.23,
        "PSP Inv": 21205.397697,
        "KCYUM": 12126.384798,
        "FEND": 2223.170546,
        "Thengvall": 808.425653,
        "Happ": 1616.851306,
    },
    "Q4 2025": {
        "total": 38000.23,
        "PSP Inv": 21216.564242,
        "KCYUM": 12132.770428,
        "FEND": 2224.341245,
        "Thengvall": 808.851362,
        "Happ": 1617.702724,
    },
}
