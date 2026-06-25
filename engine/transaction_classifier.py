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
    # NOTE: "PQSR FUND I LLC ACH PQSRFUNDI" is the bank's *generic* outgoing-ACH
    # memo — it appears on both distributions AND accounting-fee payments, so it
    # is intentionally NOT mapped to a category here. The distribution detector
    # (detect_distribution_group) catches the proportional distribution group by
    # amount; anything left over falls through to manual review rather than being
    # silently assumed to be an accounting fee.
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

    # Online transfers IN (credits) reimburse the accounting/tax fees that were
    # paid via "PQSR FUND I LLC ACH" debits. Classifying them as accounting_fees
    # lets the journal-entry logic net them against the matching debits (→ $0).
    if re.search(r"(?i)ONLINE\s*XFER", description) and credit > 0:
        return {
            "category": "accounting_fees",
            "property": None,
            "investor": None,
            "confidence": "auto",
            "details": "Accounting & Tax Fee reimbursement (online transfer in)",
        }

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


def detect_distribution_group(classified):
    """Identify quarterly investor distributions by ownership ratio.

    Distributions hit the bank as outgoing debits with no investor name in the
    description (e.g. "PQSR FUND I LLC ACH" or "ONLINE XFER"), so they can't be
    matched by description alone — and the generic ACH description collides with
    the accounting-fee rule. But every distribution is paid in proportion to the
    investors' ownership percentages, so a set of debits that all divide down to
    the same implied total identifies the group and maps each debit to its owner.

    Returns {index_in_classified: investor_key} for the matched transactions.
    """
    invs = [(k, v["ownership_pct"]) for k, v in INVESTORS.items()
            if v["ownership_pct"] > 0]

    # Only outgoing debits that aren't already firmly classified are candidates.
    # accounting_fees is included because the generic ACH description is shared
    # with real fee payments; unknown covers the channels we don't recognize.
    candidates = [
        i for i, t in enumerate(classified)
        if (t.get("debit", 0) or 0) > 0
        and t.get("category") in ("accounting_fees", "unknown")
    ]
    if len(candidates) < 4:
        return {}

    best = {}
    for ci in candidates:
        anchor_amt = classified[ci]["debit"] or 0
        for _, anchor_pct in invs:
            implied_total = anchor_amt / anchor_pct
            matches = {}
            used = set()
            for inv_key, pct in invs:
                target = implied_total * pct
                tol = max(1.00, target * 0.005)  # $1 or 0.5%, whichever larger
                for cj in candidates:
                    if cj in used:
                        continue
                    if abs((classified[cj]["debit"] or 0) - target) <= tol:
                        matches[cj] = inv_key
                        used.add(cj)
                        break
            if len(matches) > len(best):
                best = matches

    # Require at least 4 of the 5 owners to converge on one total before we
    # treat the group as a distribution (guards against coincidental matches).
    return best if len(best) >= 4 else {}


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

    # Post-pass: reassign any ownership-proportional debit group to distributions.
    for idx, inv_key in detect_distribution_group(classified).items():
        inv = INVESTORS[inv_key]
        classified[idx].update({
            "category": "distribution",
            "investor": inv_key,
            "property": None,
            "confidence": "auto",
            "details": "Distribution - {} (matched by amount/ownership)".format(
                inv["full_name"]
            ),
        })

    return classified
