"""Lease data for all 5 PQSR Fund I properties.

Sources:
- Beavercreek: First Amendment to Lease (6/19/2023), Exhibit B rent schedule
- Fairfield: First Amendment to Lease (7/21/2023), Exhibit B rent schedule
- Gallup: Original Lease (12/30/2021), Exhibit B rent schedule
- Loveland: Original Lease + 1st Amendment (12/2/2022), fund_config + 7.5% escalation
- Nacogdoches: Original Lease + Amendment (8/31/2023), fund_config + 7.5% escalation
"""

from datetime import date
import os

# Base path for lease PDF files
LEASE_PDF_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "leases"
)

LEASES = {
    "beavercreek": {
        "property_name": "Beavercreek",
        "psf_code": "PSF 223",
        "address": "SE Corner of Kemp Rd. & N. Fairfield Rd., Beavercreek, OH 45431",
        "tenant": "DJ Steakburgers, LLC",
        "tenant_state": "Ohio",
        "landlord": "Plaza Street Fund 223, LLC",
        "lease_effective_date": date(2022, 10, 19),
        "amendment_date": date(2023, 6, 19),
        "rent_commencement_date": date(2023, 10, 19),
        "initial_term_years": 20,
        "total_term_months": 480,
        "lease_expiration_date": date(2063, 10, 31),
        "renewal_options": 4,
        "renewal_term_years": 5,
        "renewal_notice_months": 6,
        "escalation_rate": 0.075,
        "escalation_frequency_months": 60,
        "lease_type": "NNN",
        "use": "Restaurant with drive-through",
        "rent_schedule": [
            {"period": "RCD - Month 60", "start_month": 1, "end_month": 60,
             "annual_rent": 192148.09, "monthly_rent": 16012.34},
            {"period": "Month 61 - Month 120", "start_month": 61, "end_month": 120,
             "annual_rent": 206559.19, "monthly_rent": 17213.27},
            {"period": "Month 121 - Month 180", "start_month": 121, "end_month": 180,
             "annual_rent": 222051.13, "monthly_rent": 18504.26},
            {"period": "Month 181 - Month 240", "start_month": 181, "end_month": 240,
             "annual_rent": 238704.97, "monthly_rent": 19892.08},
            {"period": "Month 241 - Month 300", "start_month": 241, "end_month": 300,
             "annual_rent": 256607.84, "monthly_rent": 21383.99},
            {"period": "Month 301 - Month 360", "start_month": 301, "end_month": 360,
             "annual_rent": 275853.43, "monthly_rent": 22987.79},
            {"period": "Month 361 - Month 420", "start_month": 361, "end_month": 420,
             "annual_rent": 296542.44, "monthly_rent": 24711.87},
            {"period": "Month 421 - Month 480", "start_month": 421, "end_month": 480,
             "annual_rent": 318783.12, "monthly_rent": 26565.26},
        ],
        "pdf_files": [
            "Beavercreek, OH_PSF 223_Lease_FE_10-19-22.pdf",
            "Beavercreek, OH_PSF 223_Lease Amendment_FE_6-20-23.pdf",
        ],
    },
    "fairfield": {
        "property_name": "Fairfield",
        "psf_code": "PSF 256",
        "address": "6325 S. Gilmore Rd., Fairfield, Butler County, OH 45014",
        "tenant": "DJ Steakburgers, LLC",
        "tenant_state": "Ohio",
        "landlord": "Plaza Street Fund 256, LLC",
        "lease_effective_date": date(2022, 12, 12),
        "amendment_date": date(2023, 7, 21),
        "addendum_date": date(2022, 12, 15),
        "rent_commencement_date": date(2024, 2, 13),
        "initial_term_years": 20,
        "total_term_months": 480,
        "lease_expiration_date": date(2064, 2, 28),
        "renewal_options": 4,
        "renewal_term_years": 5,
        "renewal_notice_months": 6,
        "escalation_rate": 0.075,
        "escalation_frequency_months": 60,
        "lease_type": "NNN",
        "use": "Restaurant with drive-through",
        "rent_schedule": [
            {"period": "RCD - Month 60", "start_month": 1, "end_month": 60,
             "annual_rent": 216795.69, "monthly_rent": 18066.31},
            {"period": "Month 61 - Month 120", "start_month": 61, "end_month": 120,
             "annual_rent": 233055.37, "monthly_rent": 19421.28},
            {"period": "Month 121 - Month 180", "start_month": 121, "end_month": 180,
             "annual_rent": 250534.52, "monthly_rent": 20877.88},
            {"period": "Month 181 - Month 240", "start_month": 181, "end_month": 240,
             "annual_rent": 269324.61, "monthly_rent": 22443.72},
            {"period": "Month 241 - Month 300", "start_month": 241, "end_month": 300,
             "annual_rent": 289523.95, "monthly_rent": 24127.00},
            {"period": "Month 301 - Month 360", "start_month": 301, "end_month": 360,
             "annual_rent": 311238.25, "monthly_rent": 25936.52},
            {"period": "Month 361 - Month 420", "start_month": 361, "end_month": 420,
             "annual_rent": 334581.12, "monthly_rent": 27881.76},
            {"period": "Month 421 - Month 480", "start_month": 421, "end_month": 480,
             "annual_rent": 359674.70, "monthly_rent": 29972.89},
        ],
        "pdf_files": [
            "Fairfield, OH_PSF 256_Lease _FE_12-12-22.pdf",
            "Fairfield, OH_PSF 256_Lease Addendum_FE_12-15-22.pdf",
            "Fairfield, OH_PSF 256_Lease Amendment 1_FE_8-8-23.pdf",
        ],
    },
    "gallup": {
        "property_name": "Gallup",
        "psf_code": "PSF 214",
        "address": "3500 E. Historic Highway 66, Gallup, NM",
        "tenant": "Legacy Chicken, LLC",
        "tenant_state": "California",
        "landlord": "Plaza Street Fund 214, LLC",
        "lease_effective_date": date(2021, 12, 30),
        "rent_commencement_date": date(2023, 4, 19),
        "initial_term_years": 20,
        "total_term_months": 480,
        "lease_expiration_date": date(2063, 4, 30),
        "renewal_options": 4,
        "renewal_term_years": 5,
        "renewal_notice_months": 6,
        "escalation_rate": 0.07,
        "escalation_frequency_months": 60,
        "lease_type": "NNN",
        "use": "Restaurant with drive-through (Popeyes)",
        "right_of_first_refusal": True,
        "rent_schedule": [
            {"period": "RCD - Month 60", "start_month": 1, "end_month": 60,
             "annual_rent": 175000.00, "monthly_rent": 14583.33},
            {"period": "Month 61 - Month 120", "start_month": 61, "end_month": 120,
             "annual_rent": 187250.00, "monthly_rent": 15604.17},
            {"period": "Month 121 - Month 180", "start_month": 121, "end_month": 180,
             "annual_rent": 200357.50, "monthly_rent": 16696.46},
            {"period": "Month 181 - Month 240", "start_month": 181, "end_month": 240,
             "annual_rent": 214382.53, "monthly_rent": 17865.21},
            {"period": "Month 241 - Month 300", "start_month": 241, "end_month": 300,
             "annual_rent": 229389.30, "monthly_rent": 19115.78},
            {"period": "Month 301 - Month 360", "start_month": 301, "end_month": 360,
             "annual_rent": 245446.55, "monthly_rent": 20453.88},
            {"period": "Month 361 - Month 420", "start_month": 361, "end_month": 420,
             "annual_rent": 262627.81, "monthly_rent": 21885.65},
            {"period": "Month 421 - Month 480", "start_month": 421, "end_month": 480,
             "annual_rent": 281011.76, "monthly_rent": 23417.65},
        ],
        "pdf_files": [
            "Gallup NM (Hwy 66)_PSF 214_Lease_8-18-23.pdf",
        ],
    },
    "loveland": {
        "property_name": "Loveland",
        "psf_code": "PSF 231",
        "address": "Loveland, OH",
        "tenant": "DJ Steakburgers, LLC",
        "tenant_state": "Ohio",
        "landlord": "Plaza Street Fund 231, LLC",
        "lease_effective_date": date(2022, 12, 2),
        "amendment_date": date(2023, 7, 10),
        "rent_commencement_date": date(2023, 4, 4),
        "initial_term_years": 20,
        "total_term_months": 480,
        "lease_expiration_date": date(2063, 4, 30),
        "renewal_options": 4,
        "renewal_term_years": 5,
        "renewal_notice_months": 6,
        "escalation_rate": 0.075,
        "escalation_frequency_months": 60,
        "lease_type": "NNN",
        "use": "Restaurant with drive-through",
        "rent_schedule": [
            {"period": "RCD - Month 60", "start_month": 1, "end_month": 60,
             "annual_rent": 190584.92, "monthly_rent": 15882.08},
            {"period": "Month 61 - Month 120", "start_month": 61, "end_month": 120,
             "annual_rent": 204878.79, "monthly_rent": 17073.23},
            {"period": "Month 121 - Month 180", "start_month": 121, "end_month": 180,
             "annual_rent": 220244.70, "monthly_rent": 18353.73},
            {"period": "Month 181 - Month 240", "start_month": 181, "end_month": 240,
             "annual_rent": 236763.05, "monthly_rent": 19730.25},
            {"period": "Month 241 - Month 300", "start_month": 241, "end_month": 300,
             "annual_rent": 254520.28, "monthly_rent": 21210.02},
            {"period": "Month 301 - Month 360", "start_month": 301, "end_month": 360,
             "annual_rent": 273609.30, "monthly_rent": 22800.78},
            {"period": "Month 361 - Month 420", "start_month": 361, "end_month": 420,
             "annual_rent": 294130.00, "monthly_rent": 24510.83},
            {"period": "Month 421 - Month 480", "start_month": 421, "end_month": 480,
             "annual_rent": 316189.75, "monthly_rent": 26349.15},
        ],
        "pdf_files": [
            "Loveland, OH_PSF 231_1st Amend FE_12.2.22.pdf",
            "Loveland, OH_PSF 231_Lease_FE_7-10-23.pdf",
        ],
    },
    "nacogdoches": {
        "property_name": "Nacogdoches",
        "psf_code": "PSF 271",
        "address": "Nacogdoches, TX",
        "tenant": "Ram-Z Custard, LLC",
        "tenant_state": "Texas",
        "landlord": "Plaza Street Fund 271, LLC",
        "lease_effective_date": date(2022, 12, 12),
        "amendment_date": date(2023, 8, 31),
        "rent_commencement_date": date(2023, 10, 3),
        "initial_term_years": 20,
        "total_term_months": 480,
        "lease_expiration_date": date(2063, 10, 31),
        "renewal_options": 4,
        "renewal_term_years": 5,
        "renewal_notice_months": 6,
        "escalation_rate": 0.075,
        "escalation_frequency_months": 60,
        "lease_type": "NNN",
        "use": "Restaurant with drive-through",
        "rent_schedule": [
            {"period": "RCD - Month 60", "start_month": 1, "end_month": 60,
             "annual_rent": 195000.00, "monthly_rent": 16250.00},
            {"period": "Month 61 - Month 120", "start_month": 61, "end_month": 120,
             "annual_rent": 209625.00, "monthly_rent": 17468.75},
            {"period": "Month 121 - Month 180", "start_month": 121, "end_month": 180,
             "annual_rent": 225346.88, "monthly_rent": 18778.91},
            {"period": "Month 181 - Month 240", "start_month": 181, "end_month": 240,
             "annual_rent": 242247.89, "monthly_rent": 20187.32},
            {"period": "Month 241 - Month 300", "start_month": 241, "end_month": 300,
             "annual_rent": 260416.49, "monthly_rent": 21701.37},
            {"period": "Month 301 - Month 360", "start_month": 301, "end_month": 360,
             "annual_rent": 279947.72, "monthly_rent": 23328.98},
            {"period": "Month 361 - Month 420", "start_month": 361, "end_month": 420,
             "annual_rent": 300943.80, "monthly_rent": 25078.65},
            {"period": "Month 421 - Month 480", "start_month": 421, "end_month": 480,
             "annual_rent": 323514.59, "monthly_rent": 26959.55},
        ],
        "pdf_files": [
            "Nac, TX_PSF 271_Lease Agreement_FE_12-12-22.pdf",
            "Nac, TX_Lease Amendment_FE_8.31.23.pdf",
        ],
    },
}


def get_monthly_rent_for_date(lease_key, target_date):
    """Get the monthly rent amount for a specific date.

    Args:
        lease_key: property key (e.g., 'beavercreek')
        target_date: date to look up

    Returns:
        monthly rent amount, or None if before RCD
    """
    lease = LEASES.get(lease_key)
    if not lease:
        return None

    rcd = lease["rent_commencement_date"]
    if target_date < rcd:
        return None

    # Calculate months since RCD
    months_since_rcd = (
        (target_date.year - rcd.year) * 12
        + (target_date.month - rcd.month)
        + 1  # Month 1 starts at RCD
    )

    for period in lease["rent_schedule"]:
        if period["start_month"] <= months_since_rcd <= period["end_month"]:
            return period["monthly_rent"]

    # Past end of schedule
    return lease["rent_schedule"][-1]["monthly_rent"]


def get_next_escalation_date(lease_key, as_of_date):
    """Get the next rent escalation date after the given date.

    Returns (escalation_date, new_monthly_rent) or None if no future escalation.
    """
    from dateutil.relativedelta import relativedelta

    lease = LEASES.get(lease_key)
    if not lease:
        return None

    rcd = lease["rent_commencement_date"]
    freq = lease["escalation_frequency_months"]

    # Escalations happen at month 61, 121, 181, etc.
    for period in lease["rent_schedule"][1:]:  # Skip first period
        escalation_month_num = period["start_month"]
        escalation_date = rcd + relativedelta(months=escalation_month_num - 1)
        escalation_date = date(escalation_date.year, escalation_date.month, 1)

        if escalation_date > as_of_date:
            return {
                "date": escalation_date,
                "new_monthly_rent": period["monthly_rent"],
                "new_annual_rent": period["annual_rent"],
                "period_label": period["period"],
            }

    return None


def get_lease_alerts(as_of_date, alert_months_early=12, alert_months_reminder=7):
    """Generate all active alerts for lease events.

    Returns a list of alert dicts with type, property, date, description, urgency.
    """
    from dateutil.relativedelta import relativedelta

    alerts = []

    for key, lease in LEASES.items():
        # --- Rent Escalation Alerts ---
        next_esc = get_next_escalation_date(key, as_of_date)
        if next_esc:
            esc_date = next_esc["date"]
            months_until = (
                (esc_date.year - as_of_date.year) * 12
                + (esc_date.month - as_of_date.month)
            )

            if months_until <= alert_months_early:
                urgency = "high" if months_until <= alert_months_reminder else "normal"
                current_rent = get_monthly_rent_for_date(key, as_of_date)
                alerts.append({
                    "type": "Rent Escalation",
                    "property": lease["property_name"],
                    "psf_code": lease["psf_code"],
                    "date": esc_date,
                    "months_until": months_until,
                    "urgency": urgency,
                    "description": "Rent increases from ${:,.2f} to ${:,.2f}/mo".format(
                        current_rent or 0, next_esc["new_monthly_rent"]
                    ),
                })

        # --- Lease Expiration Alerts ---
        exp_date = lease["lease_expiration_date"]
        months_until_exp = (
            (exp_date.year - as_of_date.year) * 12
            + (exp_date.month - as_of_date.month)
        )

        if months_until_exp <= alert_months_early:
            urgency = "high" if months_until_exp <= alert_months_reminder else "normal"
            alerts.append({
                "type": "Lease Expiration",
                "property": lease["property_name"],
                "psf_code": lease["psf_code"],
                "date": exp_date,
                "months_until": months_until_exp,
                "urgency": urgency,
                "description": "Lease expires on {}".format(
                    exp_date.strftime("%m/%d/%Y")
                ),
            })

        # --- Renewal Option Alerts ---
        # Renewal notice is typically due X months before expiration
        if lease.get("renewal_options", 0) > 0:
            notice_months = lease.get("renewal_notice_months", 6)
            renewal_notice_date = exp_date - relativedelta(months=notice_months)
            months_until_notice = (
                (renewal_notice_date.year - as_of_date.year) * 12
                + (renewal_notice_date.month - as_of_date.month)
            )

            if 0 < months_until_notice <= alert_months_early:
                urgency = "high" if months_until_notice <= alert_months_reminder else "normal"
                alerts.append({
                    "type": "Renewal Option Notice",
                    "property": lease["property_name"],
                    "psf_code": lease["psf_code"],
                    "date": renewal_notice_date,
                    "months_until": months_until_notice,
                    "urgency": urgency,
                    "description": "Tenant must notify by {} to exercise renewal ({} options of {} yrs remaining)".format(
                        renewal_notice_date.strftime("%m/%d/%Y"),
                        lease["renewal_options"],
                        lease["renewal_term_years"],
                    ),
                })

    # Sort by date
    alerts.sort(key=lambda a: a["date"])
    return alerts


def generate_full_rent_schedule(lease_key):
    """Generate a month-by-month rent schedule from RCD through lease expiration.

    Returns a list of dicts with: month_num, date, monthly_rent, period_label
    """
    from dateutil.relativedelta import relativedelta

    lease = LEASES.get(lease_key)
    if not lease:
        return []

    rcd = lease["rent_commencement_date"]
    schedule = []

    for month_num in range(1, lease["total_term_months"] + 1):
        month_date = rcd + relativedelta(months=month_num - 1)

        # Find which rent period this month falls in
        monthly_rent = 0
        period_label = ""
        for period in lease["rent_schedule"]:
            if period["start_month"] <= month_num <= period["end_month"]:
                monthly_rent = period["monthly_rent"]
                period_label = period["period"]
                break

        schedule.append({
            "month_num": month_num,
            "date": date(month_date.year, month_date.month, 1),
            "monthly_rent": monthly_rent,
            "period_label": period_label,
        })

    return schedule
