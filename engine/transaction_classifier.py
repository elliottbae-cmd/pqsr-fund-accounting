"""Classify bank transactions into accounting categories."""

import re
from config.fund_config import PROPERTIES, INVESTORS


# Amount-based rent matching (for ACH payments with identical descriptions)
RENT_BY_AMOUNT = {
    round(p["monthly_rent"], 2): key for key, p in PROPERTIES.items()
}

# Description patterns for classification
CLASSIFICATION_RULES = [
    {
        "pattern": r"(?i)RAM-Z CUSTARD.*Nac.*Rent|Nac.*Landlord",
        "category": "rent",
        "property": "nacogdoches",
    },
    {
        "pattern": r"(?i)LEGACY CHICKEN",
        "category": "rent",
        "property": "gallup",
    },
    {
        "pattern": r"(?i)UMB BANK LOAN PYMT",
        "category": "loan_payment",
    },
    {
        "pattern": r"(?i)Distributions?\s*-\s*PSP",
        "category": "distribution",
        "investor": "PSP Inv",
    },
    {
        "pattern": r"(?i)Distributions?\s*-\s*KCYUM",
        "category": "distribution",
        "investor": "KCYUM",
    },
    {
        "pattern": r"(?i)Distributions?\s*-\s*Thengvall",
        "category": "distribution",
        "investor": "Thengvall",
    },
    {
        "pattern": r"(?i)Distributions?\s*-\s*Happ",
        "category": "distribution",
        "investor": "Happ",
    },
    {
        "pattern": r"(?i)Distributions?\s*-\s*FEND",
        "category": "distribution",
        "investor": "FEND",
    },
    {
        "pattern": r"(?i)CBIZ",
        "category": "accounting_fees",
    },
    {
        "pattern": r"(?i)PQSR\s*FUND\s*I\s*LLC\s*ACH\s*PQSRFUNDI",
        "category": "accounting_fees",
    },
]


def classify_transaction(description, debit, credit):
    """Classify a single bank transaction.

    Returns a dict with:
        category: str - the transaction category
        property: str or None - property key if rent
        investor: str or None - investor key if distribution
        confidence: str - 'auto' or 'manual'
        details: str - human-readable classification
    """
    # Check description patterns first
    for rule in CLASSIFICATION_RULES:
        if re.search(rule["pattern"], description):
            result = {
                "category": rule["category"],
                "property": rule.get("property"),
                "investor": rule.get("investor"),
                "confidence": "auto",
            }
            if rule["category"] == "rent":
                prop = PROPERTIES[rule["property"]]
                result["details"] = "Rent - {}".format(prop["name"])
            elif rule["category"] == "loan_payment":
                result["details"] = "Loan Payment (UMB Bank)"
            elif rule["category"] == "distribution":
                inv = INVESTORS[rule["investor"]]
                result["details"] = "Distribution - {}".format(inv["full_name"])
            elif rule["category"] == "accounting_fees":
                result["details"] = "Accounting & Tax Fees (CBIZ)"
            return result

    # For RAM-Z CUSTARD ACH payments, match by credit amount to identify property
    if re.search(r"(?i)RAM-Z CUSTARD.*ACH", description) and credit > 0:
        rounded = round(credit, 2)
        if rounded in RENT_BY_AMOUNT:
            prop_key = RENT_BY_AMOUNT[rounded]
            prop = PROPERTIES[prop_key]
            return {
                "category": "rent",
                "property": prop_key,
                "investor": None,
                "confidence": "auto",
                "details": "Rent - {} (matched by amount)".format(prop["name"]),
            }

    # Unrecognized
    return {
        "category": "unknown",
        "property": None,
        "investor": None,
        "confidence": "manual",
        "details": "Unrecognized - needs manual classification",
    }


def classify_bank_data(transactions):
    """Classify a list of bank transactions.

    Each transaction should be a dict with: date, description, debit, credit.
    Returns the same list with classification info added.
    """
    classified = []
    for txn in transactions:
        classification = classify_transaction(
            txn["description"],
            txn.get("debit", 0) or 0,
            txn.get("credit", 0) or 0,
        )
        classified.append({**txn, **classification})
    return classified
