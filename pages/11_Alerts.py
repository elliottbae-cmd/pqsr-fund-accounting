"""Page 11: Alerts — Lease event monitoring and notifications."""

import streamlit as st
from config.auth import check_password
if not check_password():
    st.stop()
import pandas as pd
from datetime import date
from config.lease_data import get_lease_alerts
from config.fund_config import FUND_NAME
from config.styles import (
    inject_custom_css, show_sidebar_branding, styled_page_header,
    styled_section_header, styled_divider,
)
from database.db import clear_alert, get_cleared_alerts, clear_all_alerts

inject_custom_css()
show_sidebar_branding()
styled_page_header("Alerts", "Lease Event Monitoring")

today = date.today()


def _alert_key(alert):
    """Generate a unique key for an alert."""
    return "{}_{}_{}".format(
        alert["type"].replace(" ", "_"),
        alert["psf_code"].replace(" ", "_"),
        alert["date"].isoformat(),
    )


# --- Active Alerts ---
all_alerts = get_lease_alerts(today, alert_months_early=12, alert_months_reminder=7)
cleared = get_cleared_alerts()

active_alerts = [a for a in all_alerts if _alert_key(a) not in cleared]
cleared_count = len(all_alerts) - len(active_alerts)

# Summary metrics
col1, col2, col3 = st.columns(3)
col1.metric("Active Alerts", len(active_alerts))
col2.metric("Cleared", cleared_count)
col3.metric("Total (12-Month Window)", len(all_alerts))

styled_divider()

if not active_alerts:
    if cleared_count > 0:
        st.success("All {} alert(s) have been cleared.".format(cleared_count))
    else:
        st.success("No active alerts. All lease events are more than 12 months away.")
else:
    # Separate high urgency vs normal
    high_alerts = [a for a in active_alerts if a["urgency"] == "high"]
    normal_alerts = [a for a in active_alerts if a["urgency"] == "normal"]

    if high_alerts:
        styled_section_header("Urgent (7 Months or Less)")
        for alert in high_alerts:
            col_alert, col_btn = st.columns([5, 1])
            with col_alert:
                st.error(
                    "**{} — {} ({})** | {} months | {} | {}".format(
                        alert["type"],
                        alert["property"],
                        alert["psf_code"],
                        alert["months_until"],
                        alert["date"].strftime("%m/%d/%Y"),
                        alert["description"],
                    )
                )
            with col_btn:
                if st.button("Clear", key="clear_{}".format(_alert_key(alert))):
                    clear_alert(_alert_key(alert))
                    st.rerun()

    if normal_alerts:
        styled_section_header("Upcoming (12 Months or Less)")
        for alert in normal_alerts:
            col_alert, col_btn = st.columns([5, 1])
            with col_alert:
                st.warning(
                    "**{} — {} ({})** | {} months | {} | {}".format(
                        alert["type"],
                        alert["property"],
                        alert["psf_code"],
                        alert["months_until"],
                        alert["date"].strftime("%m/%d/%Y"),
                        alert["description"],
                    )
                )
            with col_btn:
                if st.button("Clear", key="clear_{}".format(_alert_key(alert))):
                    clear_alert(_alert_key(alert))
                    st.rerun()

# Cleared count and reset
if cleared_count > 0:
    st.caption("{} alert(s) cleared.".format(cleared_count))
    if st.button("Restore All Cleared Alerts"):
        clear_all_alerts()
        st.rerun()

styled_divider()

# --- 5-Year Event Timeline ---
styled_section_header("Lease Event Timeline — Next 5 Years")

timeline_alerts = get_lease_alerts(today, alert_months_early=60, alert_months_reminder=7)

if timeline_alerts:
    timeline_rows = []
    for alert in timeline_alerts:
        ak = _alert_key(alert)
        timeline_rows.append({
            "Date": alert["date"].strftime("%m/%d/%Y"),
            "Type": alert["type"],
            "Property": "{} ({})".format(alert["property"], alert["psf_code"]),
            "Months": alert["months_until"],
            "Details": alert["description"],
            "Status": "Cleared" if ak in cleared else "Active",
        })
    st.dataframe(
        pd.DataFrame(timeline_rows),
        hide_index=True, use_container_width=True,
    )
else:
    st.info("No lease events in the next 5 years.")
