"""Page 10: Lease Management — Rent Schedules, Abstracts, Documents, and Alerts."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from config.lease_data import (
    LEASES, get_monthly_rent_for_date,
    get_next_escalation_date,
)
from config.fund_config import FUND_NAME
from config.styles import (
    inject_custom_css, show_sidebar_branding, styled_page_header,
    styled_section_header, styled_divider,
)

inject_custom_css()
show_sidebar_branding()
styled_page_header("Leases", "Lease Management & Monitoring")

today = date.today()

tab_schedules, tab_abstracts = st.tabs([
    "Rent Schedules",
    "Lease Abstracts",
])


# ==================== RENT SCHEDULES ====================
with tab_schedules:
    st.markdown("### {} | Rent Schedules".format(FUND_NAME))
    st.caption("Monthly rent by property for the full lease term.")

    # Current rent summary
    styled_section_header("Current Monthly Rent")

    current_rows = []
    total_monthly = 0
    for key, lease in LEASES.items():
        rent = get_monthly_rent_for_date(key, today) or 0
        total_monthly += rent
        next_esc = get_next_escalation_date(key, today)
        next_esc_str = next_esc["date"].strftime("%m/%d/%Y") if next_esc else "N/A"
        next_rent_str = "${:,.2f}".format(next_esc["new_monthly_rent"]) if next_esc else "N/A"

        current_rows.append({
            "Property": lease["property_name"],
            "PSF Code": lease["psf_code"],
            "Current Rent": "${:,.2f}".format(rent),
            "Next Increase": next_esc_str,
            "New Rent": next_rent_str,
        })

    current_rows.append({
        "Property": "Total",
        "PSF Code": "",
        "Current Rent": "${:,.2f}".format(total_monthly),
        "Next Increase": "",
        "New Rent": "",
    })

    st.dataframe(
        pd.DataFrame(current_rows),
        hide_index=True, use_container_width=True,
    )

    styled_divider()

    # Escalation schedule by property
    styled_section_header("Rent Escalation Schedule")

    from dateutil.relativedelta import relativedelta

    for key, lease in LEASES.items():
        with st.expander("{} ({})".format(lease["property_name"], lease["psf_code"])):
            rcd = lease["rent_commencement_date"]
            sched_rows = []
            for period in lease["rent_schedule"]:
                # Convert month numbers to actual calendar dates
                start_date = rcd + relativedelta(months=period["start_month"] - 1)
                end_date = rcd + relativedelta(months=period["end_month"]) - relativedelta(days=1)
                date_range = "{} - {}".format(
                    start_date.strftime("%m/%d/%Y"),
                    end_date.strftime("%m/%d/%Y"),
                )
                # Label renewal periods
                label = period["period"]
                if "Renewal" in label:
                    renewal_part = label.split(":")[0]  # e.g., "Renewal 1"
                    date_range = "{} ({})".format(date_range, renewal_part)

                sched_rows.append({
                    "Period": date_range,
                    "Monthly Rent": "${:,.2f}".format(period["monthly_rent"]),
                    "Annual Rent": "${:,.2f}".format(period["annual_rent"]),
                })
            st.dataframe(
                pd.DataFrame(sched_rows),
                hide_index=True, use_container_width=True,
            )
            st.caption(
                "RCD: {} | Escalation: {:.1%} every {} months | Tenant: {}".format(
                    rcd.strftime("%m/%d/%Y"),
                    lease["escalation_rate"],
                    lease["escalation_frequency_months"],
                    lease["tenant"],
                )
            )

    styled_divider()

    # Combined monthly schedule (next 5 years)
    styled_section_header("Monthly Rent Schedule — Next 5 Years")

    monthly_rows = []
    for year in range(today.year, today.year + 5):
        for month in range(1, 13):
            d = date(year, month, 1)
            row = {"Date": d.strftime("%b %Y")}
            row_total = 0
            for key, lease in LEASES.items():
                rent = get_monthly_rent_for_date(key, d) or 0
                row[lease["property_name"]] = "${:,.2f}".format(rent)
                row_total += rent
            row["Total"] = "${:,.2f}".format(row_total)
            monthly_rows.append(row)

    st.dataframe(
        pd.DataFrame(monthly_rows),
        hide_index=True, use_container_width=True, height=500,
    )


# ==================== LEASE ABSTRACTS ====================
with tab_abstracts:
    st.markdown("### {} | Lease Abstracts".format(FUND_NAME))
    st.caption("Key terms and critical dates for each property.")

    for key, lease in LEASES.items():
        with st.expander(
            "{} ({}) — {}".format(
                lease["property_name"], lease["psf_code"], lease["tenant"]
            ),
            expanded=False,
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("##### Property & Parties")
                st.markdown("**Address:** {}".format(lease["address"]))
                st.markdown("**Tenant:** {} ({})".format(
                    lease["tenant"], lease["tenant_state"]
                ))
                st.markdown("**Landlord:** {}".format(lease["landlord"]))
                st.markdown("**Lease Type:** {}".format(lease["lease_type"]))
                st.markdown("**Use:** {}".format(lease["use"]))

            with col2:
                st.markdown("##### Key Dates")
                st.markdown("**Lease Effective:** {}".format(
                    lease["lease_effective_date"].strftime("%m/%d/%Y")
                ))
                if lease.get("amendment_date"):
                    st.markdown("**Amendment:** {}".format(
                        lease["amendment_date"].strftime("%m/%d/%Y")
                    ))
                st.markdown("**Rent Commencement:** {}".format(
                    lease["rent_commencement_date"].strftime("%m/%d/%Y")
                ))
                st.markdown("**Lease Expiration:** {}".format(
                    lease["lease_expiration_date"].strftime("%m/%d/%Y")
                ))

            st.markdown("---")

            col3, col4 = st.columns(2)

            with col3:
                st.markdown("##### Term & Renewals")
                st.markdown("**Initial Term:** {} years ({} months)".format(
                    lease["initial_term_years"],
                    lease["initial_term_months"],
                ))
                st.markdown("**Max Term (with renewals):** {} years".format(
                    lease["initial_term_years"] + lease["renewal_options"] * lease["renewal_term_years"],
                ))
                st.markdown("**Renewal Options:** {} options of {} years each".format(
                    lease["renewal_options"], lease["renewal_term_years"]
                ))
                st.markdown("**Renewal Notice:** {} months prior".format(
                    lease["renewal_notice_months"]
                ))

            with col4:
                st.markdown("##### Rent")
                current_rent = get_monthly_rent_for_date(key, today) or 0
                st.markdown("**Current Monthly Rent:** ${:,.2f}".format(current_rent))
                st.markdown("**Current Annual Rent:** ${:,.2f}".format(current_rent * 12))
                st.markdown("**Escalation Rate:** {:.1%} every {} months".format(
                    lease["escalation_rate"],
                    lease["escalation_frequency_months"],
                ))
                next_esc = get_next_escalation_date(key, today)
                if next_esc:
                    st.markdown("**Next Escalation:** {} (${:,.2f}/mo)".format(
                        next_esc["date"].strftime("%m/%d/%Y"),
                        next_esc["new_monthly_rent"],
                    ))

            st.markdown("---")

            # Renewal Option Notice Deadlines
            from dateutil.relativedelta import relativedelta

            st.markdown("##### Renewal Option Notice Deadlines")
            rcd = lease["rent_commencement_date"]
            notice_months = lease.get("renewal_notice_months", 6)
            initial_months = lease["initial_term_months"]
            renewal_years = lease["renewal_term_years"]
            num_renewals = lease["renewal_options"]

            renewal_rows = []
            for r_num in range(1, num_renewals + 1):
                # Each renewal starts after the initial term + prior renewals
                renewal_start_month = initial_months + ((r_num - 1) * renewal_years * 12) + 1
                renewal_start_date = rcd + relativedelta(months=renewal_start_month - 1)
                renewal_end_date = renewal_start_date + relativedelta(years=renewal_years) - relativedelta(days=1)
                notice_deadline = renewal_start_date - relativedelta(months=notice_months)

                renewal_rows.append({
                    "Option": "Renewal {}".format(r_num),
                    "Term": "{} - {}".format(
                        renewal_start_date.strftime("%m/%d/%Y"),
                        renewal_end_date.strftime("%m/%d/%Y"),
                    ),
                    "Notice Deadline": notice_deadline.strftime("%m/%d/%Y"),
                    "Status": "Upcoming" if notice_deadline > today else "Past Due",
                })

            st.dataframe(
                pd.DataFrame(renewal_rows),
                hide_index=True, use_container_width=True,
            )

            # Right of first refusal
            if lease.get("right_of_first_refusal"):
                st.markdown("---")
                st.info("This lease includes a **Right of First Refusal** for the tenant.")

