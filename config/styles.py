"""Centralized styling, CSS injection, and formatting helpers for the PQSR Fund I app."""

import streamlit as st
import os

# Brand colors extracted from the investor report PDF
GOLD_PRIMARY = "#F4A523"
GOLD_DARK = "#C78A1E"
GOLD_LIGHT = "#FDF0D5"
TEXT_DARK = "#494949"
TEXT_MEDIUM = "#797979"
ROW_ALT = "#F9F9F9"
BORDER_GRAY = "#CCCCCC"
WHITE = "#FFFFFF"
BG_WHITE = "#FFFFFF"

# Logo path
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")


def inject_custom_css():
    """Inject custom CSS for professional gold-accented styling throughout the app."""
    st.markdown("""
    <style>
        /* ===== HIDE DEFAULT "app" LABEL IN SIDEBAR ===== */
        [data-testid="stSidebarNav"] li:first-child {
            display: none;
        }

        /* ===== REORDER SIDEBAR: Logo on top, nav below ===== */
        [data-testid="stSidebar"] > div:first-child {
            display: flex;
            flex-direction: column;
        }
        /* Push the user-content block (logo) above the nav */
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            order: -1;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            order: 1;
            margin-top: -16px !important;
            padding-top: 0 !important;
        }

        /* ===== SIDEBAR BRANDING ===== */
        [data-testid="stSidebar"] {
            background-color: #FAFAFA;
        }
        [data-testid="stSidebar"] .stMarkdown h1 {
            color: """ + GOLD_PRIMARY + """;
            font-size: 1.3rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            border-bottom: 2px solid """ + GOLD_PRIMARY + """;
            padding-bottom: 8px;
            margin-bottom: 16px;
        }

        /* ===== PAGE HEADERS ===== */
        .main h1 {
            color: """ + TEXT_DARK + """;
            font-weight: 700;
        }
        .main h2 {
            color: """ + TEXT_DARK + """;
            font-weight: 600;
        }
        .main h3 {
            color: """ + GOLD_PRIMARY + """;
            font-weight: 600;
            border-bottom: 2px solid """ + GOLD_PRIMARY + """;
            padding-bottom: 6px;
        }

        /* ===== METRIC CARDS ===== */
        [data-testid="stMetric"] {
            background-color: #FAFAFA;
            border: 1px solid #E8E8E8;
            border-left: 4px solid """ + GOLD_PRIMARY + """;
            border-radius: 4px;
            padding: 12px 16px;
        }
        [data-testid="stMetric"] label {
            color: """ + TEXT_MEDIUM + """ !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: """ + TEXT_DARK + """ !important;
            font-weight: 600 !important;
        }

        /* ===== DATAFRAME / TABLE STYLING ===== */
        .stDataFrame {
            border: 1px solid #E8E8E8;
            border-radius: 4px;
            overflow: hidden;
        }
        .stDataFrame thead tr th {
            background-color: """ + GOLD_PRIMARY + """ !important;
            color: """ + WHITE + """ !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            padding: 10px 12px !important;
            border: none !important;
        }
        .stDataFrame tbody tr:nth-child(even) {
            background-color: """ + ROW_ALT + """;
        }
        .stDataFrame tbody tr td {
            font-size: 0.85rem !important;
            padding: 8px 12px !important;
            color: """ + TEXT_DARK + """ !important;
        }

        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0px;
        }
        .stTabs [data-baseweb="tab"] {
            color: """ + TEXT_MEDIUM + """;
            font-weight: 500;
            padding: 8px 20px;
            border-bottom: 2px solid transparent;
        }
        .stTabs [aria-selected="true"] {
            color: """ + GOLD_PRIMARY + """ !important;
            border-bottom: 3px solid """ + GOLD_PRIMARY + """ !important;
            font-weight: 600;
        }

        /* ===== EXPANDER ===== */
        .streamlit-expanderHeader {
            font-weight: 600;
            color: """ + TEXT_DARK + """;
            background-color: #FAFAFA;
            border-left: 3px solid """ + GOLD_PRIMARY + """;
        }

        /* ===== BUTTONS ===== */
        .stButton > button[kind="primary"] {
            background-color: """ + GOLD_PRIMARY + """;
            border-color: """ + GOLD_PRIMARY + """;
            color: white;
            font-weight: 600;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: """ + GOLD_DARK + """;
            border-color: """ + GOLD_DARK + """;
        }

        /* ===== SUCCESS / WARNING / ERROR ===== */
        .stSuccess {
            border-left: 4px solid #28A745;
        }
        .stWarning {
            border-left: 4px solid """ + GOLD_PRIMARY + """;
        }

        /* ===== INFO BOXES ===== */
        .stAlert {
            border-radius: 4px;
        }

        /* ===== DOWNLOAD BUTTON ===== */
        .stDownloadButton > button {
            background-color: """ + GOLD_PRIMARY + """;
            color: white;
            font-weight: 600;
            border: none;
        }
        .stDownloadButton > button:hover {
            background-color: """ + GOLD_DARK + """;
        }

        /* ===== DIVIDERS ===== */
        hr {
            border-color: #E8E8E8;
        }

        /* ===== FILE UPLOADER ===== */
        [data-testid="stFileUploader"] {
            border: 2px dashed """ + BORDER_GRAY + """;
            border-radius: 8px;
            padding: 20px;
            background-color: #FAFAFA;
        }

        /* ===== SELECTBOX ===== */
        .stSelectbox label {
            color: """ + TEXT_DARK + """;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)


def show_sidebar_branding():
    """Display PQSR Fund I logo and branding in the sidebar."""
    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, use_container_width=True)
    st.sidebar.markdown(
        "<p style='color: {}; font-size: 0.85rem; font-weight: 600; "
        "text-align: center; margin-top: -8px;'>Accounting Portal</p>".format(GOLD_PRIMARY),
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")


def format_currency(val, decimals=2):
    """Format a number as currency with parens for negatives.

    Args:
        val: numeric value
        decimals: number of decimal places (default 2)

    Returns:
        Formatted string like '$1,234.56' or '$(1,234.56)'
    """
    if val is None or val == 0:
        return "-"
    fmt = "{{:,.{}f}}".format(decimals)
    if val < 0:
        return "$({})".format(fmt.format(abs(val)))
    return "${}".format(fmt.format(val))


def format_pct(val, decimals=2):
    """Format as percentage."""
    if val is None:
        return "-"
    fmt = "{{:.{}f}}%".format(decimals)
    return fmt.format(val * 100)


def styled_page_header(title, subtitle=None):
    """Render a professional page header with gold underline."""
    html = (
        "<div style='margin-bottom: 24px;'>"
        "<h2 style='color: {}; margin-bottom: 4px; font-weight: 700;'>{}</h2>".format(
            TEXT_DARK, title
        )
    )
    if subtitle:
        html += (
            "<p style='color: {}; font-size: 0.95rem; margin-top: 0;'>{}</p>".format(
                TEXT_MEDIUM, subtitle
            )
        )
    html += "<div style='height: 3px; background: {}; width: 60px; margin-top: 8px;'></div>".format(
        GOLD_PRIMARY
    )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def styled_section_header(text):
    """Render a section header with gold accent."""
    st.markdown(
        "<h4 style='color: {}; border-left: 4px solid {}; padding-left: 12px; "
        "margin-top: 24px; margin-bottom: 12px;'>{}</h4>".format(
            TEXT_DARK, GOLD_PRIMARY, text
        ),
        unsafe_allow_html=True,
    )


def styled_divider():
    """Render a styled horizontal divider."""
    st.markdown(
        "<hr style='border: none; height: 1px; background: #E8E8E8; margin: 24px 0;'>",
        unsafe_allow_html=True,
    )
