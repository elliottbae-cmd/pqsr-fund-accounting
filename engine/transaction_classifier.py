"""Classify bank transactions into accounting categories."""

import re
from config.fund_config import PROPERTIES, INVESTORS


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

    # NOTE: "ONLINE XFER" transactions are intentionally NOT auto-classified.
    # An earlier rule auto-booked ONLINE XFER credits as accounting-fee
    # reimbursements, which worked for small fee-reimbursement pairs but
    # misclassified unrelated transfers (e.g. a $50k transfer-in). Per Bret
    # (2026-08-11): every online transfer must be manually assigned. They fall
    # through to "unknown" below. (Outgoing ONLINE XFER debits that are part of
    # a proportional distribution group are still caught by
    # detect_distribution_group — that auto-detection is intentional.)

    # For RAM-Z CUSTARD payments, match by credit amount to identify the
    # property. Use a small tolerance (the five rents are all >$130 apart, so $1
    # is unambiguous) so a payment a few cents off (rounding / CAM drift) still
    # auto-matches instead of dropping to manual. Pick the closest property.
    # NOTE: deliberately does NOT require "ACH" in the memo — the bank changed
    # the format in Sept 2026 from "RAM-Z CUSTARD ACH Paymen ..." to
    # "RAM-Z CUSTARD RE-00xx ...", which broke the old pattern. The amount is
    # the real identifier; the RAM-Z CUSTARD prefix just scopes it to the tenant.
    if re.search(r"(?i)RAM-Z CUSTARD", description) and credit > 0:
        best_key, best_diff = None, None
        for key, p in PROPERTIES.items():
            diff = abs(p["monthly_rent"] - credit)
            if diff <= 1.00 and (best_diff is None or diff < best_diff):
                best_key, best_diff = key, diff
        if best_key:
            prop = PROPERTIES[best_key]
            return {
                "category": "rent",
                "property": best_key,
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

    # Only outgoing UNKNOWN debits are candidates. Real distributions hit the
    # bank with a generic memo that falls through to "unknown"; actual fee
    # payments carry an identifying memo (e.g. CBIZ) and are classified as
    # accounting_fees. Excluding accounting_fees prevents a fee debit that
    # happens to fall near an investor's distribution target from being hijacked
    # into the group and displacing a real distribution.
    candidates = [
        i for i, t in enumerate(classified)
        if (t.get("debit", 0) or 0) > 0
        and t.get("category") == "unknown"
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


def classify_bank_data(transactions, distributions_payable_balance=0.0):
    """Classify a list of bank transactions.

    Each transaction should be a dict with: date, description, debit, credit.
    Returns the same list with classification info added.

    distributions_payable_balance: the "Distributions Payable" balance from the
    most recently posted balance sheet. When a quarter's distributions were
    DECLARED at quarter-end (Dr Distributions - <inv> / Cr Distributions
    Payable) and the cash goes out the following month, the payment debits
    would otherwise be re-detected as a distribution group and double-count
    equity. If the detected group's total matches the outstanding payable, the
    group is booked as a payable payment (Dr Distributions Payable / Cr Cash)
    instead.
    """
    classified = []
    for txn in transactions:
        classification = classify_transaction(
            txn["description"],
            txn.get("debit", 0) or 0,
            txn.get("credit", 0) or 0,
        )
        classified.append({**txn, **classification})

    # Post-pass: reassign any ownership-proportional debit group to
    # distributions — or, if it pays off a declared Distributions Payable
    # balance, to payable payments.
    group = detect_distribution_group(classified)
    if group:
        group_total = sum(classified[i].get("debit", 0) or 0 for i in group)
        pay_bal = distributions_payable_balance or 0.0
        pays_declared = (
            pay_bal > 0
            and abs(group_total - pay_bal) <= max(1.00, pay_bal * 0.005)
        )
        for idx, inv_key in group.items():
            inv = INVESTORS[inv_key]
            if pays_declared:
                classified[idx].update({
                    "category": "dist_payable",
                    "investor": inv_key,
                    "property": None,
                    "confidence": "auto",
                    "details": "Payment of declared distribution - {} (Distributions Payable)".format(
                        inv["full_name"]
                    ),
                })
            else:
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
