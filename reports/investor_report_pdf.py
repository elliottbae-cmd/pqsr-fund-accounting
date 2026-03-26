"""Generate the 6-page investor summary PDF using ReportLab."""

import io
import os
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Image
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from config.fund_config import (
    FUND_NAME, INVESTORS, INVESTOR_REPORT_NAMES, LOAN,
    DISTRIBUTION_HISTORY, FMV_ASSETS, FIXED_ASSETS,
)

# Colors matching the gold/orange brand scheme
GOLD_PRIMARY = HexColor("#F4A523")
GOLD_DARK = HexColor("#C78A1E")
LIGHT_GRAY = HexColor("#F5F5F5")
BORDER_GRAY = HexColor("#CCCCCC")

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")


def _fmt(val, prefix="$", parens_negative=True):
    """Format a number for display."""
    if val is None or val == 0:
        return "-"
    if isinstance(val, str):
        return val
    if val < 0 and parens_negative:
        return "{0}({1:,.0f})".format(prefix, abs(val))
    return "{0}{1:,.0f}".format(prefix, val)


def _fmt2(val, prefix="$"):
    """Format with no decimals, always positive display."""
    if val is None or val == 0:
        return "-"
    return "{0}{1:,.0f}".format(prefix, abs(val))


def _pct(val):
    """Format as percentage."""
    return "{:.2%}".format(val)


def _build_styles():
    """Create paragraph styles for the report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'ReportTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=24, textColor=white,
        alignment=TA_CENTER, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'ReportSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=14, textColor=white,
        alignment=TA_CENTER, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'SectionHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, textColor=GOLD_PRIMARY,
        spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'PageHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12, textColor=GOLD_PRIMARY,
        alignment=TA_LEFT, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        'NoteText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, textColor=black,
        spaceBefore=2, spaceAfter=2, leading=10,
    ))
    styles.add(ParagraphStyle(
        'FooterText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7, textColor=HexColor("#888888"),
        alignment=TA_CENTER,
    ))
    return styles


def generate_investor_report(
    bs, is_accounts, cash_flow, totals, distribution_data,
    as_of_date, investor_notes, quarterly_noi_history,
    loan_balance, total_principal_paid,
):
    """Generate the investor report PDF.

    Args:
        bs: balance sheet dict
        is_accounts: income statement dict
        cash_flow: cash flow metrics dict
        totals: computed totals dict
        distribution_data: current quarter distribution + history
        as_of_date: date for the report
        investor_notes: list of note strings
        quarterly_noi_history: dict of quarter label -> NOI value
        loan_balance: current loan balance
        total_principal_paid: total principal paid to date

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    styles = _build_styles()

    date_str = as_of_date.strftime("%-m/%-d/%Y") if hasattr(as_of_date, 'strftime') else str(as_of_date)
    try:
        date_str = as_of_date.strftime("%m/%d/%Y").lstrip("0").replace("/0", "/")
    except Exception:
        date_str = str(as_of_date)

    quarter = (as_of_date.month - 1) // 3 + 1
    date_display = f"{as_of_date.month}/{as_of_date.day}/{as_of_date.year}"

    footer_text = f"{FUND_NAME} | Confidential - For Investor Use Only"

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(HexColor("#888888"))
        canvas.drawCentredString(
            letter[0] / 2, 0.5 * inch, footer_text
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )

    story = []

    # ==================== PAGE 1: COVER ====================
    story.append(Spacer(1, 1.5 * inch))

    # Logo above the cover box
    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=1.5 * inch, height=1.5 * inch)
        logo.hAlign = 'CENTER'
        story.append(logo)
        story.append(Spacer(1, 0.25 * inch))
    else:
        story.append(Spacer(1, 0.5 * inch))

    # Gold background box via a table
    cover_data = [
        [Paragraph(FUND_NAME, styles['ReportTitle'])],
        [Paragraph(f"{as_of_date.strftime('%m/%d/%Y')} Financial Reporting", styles['ReportSubtitle'])],
        [Paragraph("Investor Summary", styles['ReportSubtitle'])],
    ]
    cover_table = Table(cover_data, colWidths=[5 * inch])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GOLD_PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ==================== PAGE 2: SUMMARY ====================
    story.append(Paragraph(
        f"{FUND_NAME} | Investor Summary | {as_of_date.strftime('%m/%d/%Y')}",
        styles['PageHeader']
    ))

    # Book Value table
    book_basis = sum(FIXED_ASSETS[k]["amount"] for k in FIXED_ASSETS)
    bv_data = [
        ["BOOK VALUE", ""],
        ["Book Basis of Assets Held", _fmt(book_basis)],
        ["Outstanding Debt Balance", _fmt2(loan_balance)],
        ["Net Book Value", _fmt(book_basis - loan_balance)],
    ]
    bv_table = Table(bv_data, colWidths=[4 * inch, 2.5 * inch])
    bv_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(bv_table)
    story.append(Spacer(1, 8))

    # Fair Market Value table
    fmv_data = [
        ["FAIR MARKET VALUE", ""],
        ["Est. FMV of Assets Held", _fmt(FMV_ASSETS)],
        ["Outstanding Debt Balance", _fmt2(loan_balance)],
        ["Est. Fund Net Worth", _fmt(FMV_ASSETS - loan_balance)],
    ]
    fmv_table = Table(fmv_data, colWidths=[4 * inch, 2.5 * inch])
    fmv_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(fmv_table)
    story.append(Spacer(1, 8))

    # Cash Distributions table
    total_dist_all_time = distribution_data.get("cumulative_total", 0)
    current_qtr_dist = distribution_data.get("current_quarter", {}).get("total", 0)
    cd_data = [
        ["CASH DISTRIBUTIONS", ""],
        [f"Distributable Cash - {as_of_date.strftime('%m/%d/%Y')}", _fmt(current_qtr_dist)],
        ["Total Distributions Post Acquisition", _fmt(total_dist_all_time)],
    ]
    cd_table = Table(cd_data, colWidths=[4 * inch, 2.5 * inch])
    cd_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(cd_table)
    story.append(Spacer(1, 12))

    # Debt info bar
    debt_data = [[
        _fmt(loan_balance),
        LOAN["maturity_date"].strftime("%m/%d/%Y"),
        "{:.2%}".format(LOAN['annual_rate']),
    ]]
    debt_header = [["DEBT BALANCE", "MATURITY DATE", "INTEREST RATE"]]

    # NOI by quarter
    noi_labels = list(quarterly_noi_history.keys())
    noi_values = [_fmt(v) for v in quarterly_noi_history.values()]
    t12_noi = sum(quarterly_noi_history.values())

    noi_header_row = noi_labels + ["T-12 NOI"]
    noi_value_row = noi_values + [_fmt(t12_noi)]

    debt_noi_data = [
        [_fmt(loan_balance), LOAN["maturity_date"].strftime("%m/%d/%Y"),
         "{:.2%}".format(LOAN['annual_rate'])] + noi_labels + ["T-12 NOI"],
        ["DEBT BALANCE", "MATURITY DATE", "INTEREST RATE"] + noi_values + [_fmt(t12_noi)],
    ]
    col_w = [1.2 * inch, 1.0 * inch, 0.9 * inch] + [0.85 * inch] * (len(noi_labels) + 1)
    debt_noi_table = Table(debt_noi_data, colWidths=col_w)
    debt_noi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(debt_noi_table)
    story.append(Spacer(1, 16))

    # Investor Notes
    story.append(Paragraph("Investor Notes", styles['SectionHeader']))
    for note in investor_notes:
        story.append(Paragraph(note, styles['NoteText']))
    story.append(PageBreak())

    # ==================== PAGE 3: BALANCE SHEET - ASSETS ====================
    story.append(Paragraph(
        f"{FUND_NAME} | Balance Sheet | {as_of_date.strftime('%m/%d/%Y')}",
        styles['PageHeader']
    ))

    assets_data = [
        ["ASSETS", ""],
        ["Cash", _fmt(bs["Cash"])],
        ["FIXED ASSETS", ""],
        ["Land", _fmt2(bs["Land"])],
        ["Building", _fmt2(bs["Building"])],
        ["Land Improvements", _fmt2(bs["Land Improvements"])],
        ["Furniture & Fixtures", _fmt2(bs["F&F"])],
        ["Equipment", _fmt2(bs["Equipment"])],
        ["Signage", _fmt2(bs["Signage"])],
        ["Building - Accum. Depreciation", _fmt(bs["Building A/D"])],
        ["Land Improvements - Accum. Depreciation", _fmt(bs["Land Improvements A/D"])],
        ["F&F - Accum. Depreciation", _fmt(bs["F&F A/D"])],
        ["Equipment - Accum. Depreciation", _fmt(bs["Equipment A/D"])],
        ["Signage - Accum. Depreciation", _fmt(bs["Signage A/D"])],
        ["Total Fixed Assets (Net)", _fmt(totals["total_fa_net"])],
        ["OTHER ASSETS", ""],
        ["Capitalized Origination Fee", _fmt2(bs["Capitalized Origination Fee"])],
        ["Accumulated Amortization", _fmt(bs["Accumulated Amortization"])],
        ["Total Other Assets", _fmt(totals["total_other_assets"])],
        ["Total Assets", _fmt(totals["total_assets"])],
    ]

    assets_table = Table(assets_data, colWidths=[4.5 * inch, 2 * inch])
    assets_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 2), (-1, 2), GOLD_DARK),
        ('TEXTCOLOR', (0, 2), (-1, 2), white),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 15), (-1, 15), GOLD_DARK),
        ('TEXTCOLOR', (0, 15), (-1, 15), white),
        ('FONTNAME', (0, 15), (-1, 15), 'Helvetica-Bold'),
        ('FONTNAME', (0, 14), (-1, 14), 'Helvetica-Bold'),
        ('FONTNAME', (0, 18), (-1, 18), 'Helvetica-Bold'),
        ('FONTNAME', (0, 19), (-1, 19), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, 1), [white]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(assets_table)
    story.append(PageBreak())

    # ==================== PAGE 4: BALANCE SHEET - LIABILITIES & EQUITY ====================
    story.append(Paragraph(
        f"{FUND_NAME} | Balance Sheet | {as_of_date.strftime('%m/%d/%Y')} (continued)",
        styles['PageHeader']
    ))

    liab_data = [
        ["LIABILITIES", ""],
        ["Note Payable - BBV", _fmt2(bs["Note Payable - BBV"])],
        ["Due to PSP Investments, LLC", _fmt2(bs["Due to PSP Investments, LLC"])],
        ["Deferred Rental Revenue", _fmt(bs["Deferred Rental Revenue"])],
        ["Total Liabilities", _fmt(totals["total_liabilities"])],
    ]

    equity_data = [
        ["MEMBERS' EQUITY", ""],
        ["Contributions - PSP Inv", _fmt2(bs["Contributions - PSP Inv"])],
        ["Contributions - KCYUM", _fmt2(bs["Contributions - KCYUM"])],
        ["Contributions - Thengvall", _fmt2(bs["Contributions - Thengvall"])],
        ["Contributions - Happ", _fmt2(bs["Contributions - Happ"])],
        ["Contributions - FEND", _fmt2(bs["Contributions - FEND"])],
        ["Distributions - PSP Inv", _fmt(bs["Distributions - PSP Inv"])],
        ["Distributions - KCYUM", _fmt(bs["Distributions - KCYUM"])],
        ["Distributions - Thengvall", _fmt(bs["Distributions - Thengvall"])],
        ["Distributions - Happ", _fmt(bs["Distributions - Happ"])],
        ["Distributions - FEND", _fmt(bs["Distributions - FEND"])],
        ["CY Net Income", _fmt(bs["CY Net Income"])],
        ["Retained Earnings", _fmt(bs["Retained Earnings"])],
        ["Total Equity", _fmt(totals["total_equity"])],
        ["Total Liabilities / Equity", _fmt(totals["total_liabilities_equity"])],
    ]

    combined = liab_data + [["", ""]] + equity_data
    le_table = Table(combined, colWidths=[4.5 * inch, 2 * inch])

    le_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 6), (-1, 6), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 6), (-1, 6), white),
        ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),
        ('FONTNAME', (0, 19), (-1, 19), 'Helvetica-Bold'),
        ('FONTNAME', (0, 20), (-1, 20), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    le_table.setStyle(TableStyle(le_styles))
    story.append(le_table)
    story.append(PageBreak())

    # ==================== PAGE 5: INCOME STATEMENT + CASH FLOW ====================
    story.append(Paragraph(
        f"{FUND_NAME} | Income Statement | {as_of_date.strftime('%m/%d/%Y')}",
        styles['PageHeader']
    ))

    is_data = [
        ["REVENUE", ""],
        ["Rental Income", _fmt(is_accounts["Rental Income"])],
        ["EXPENSES", ""],
        ["Interest Expense", _fmt2(is_accounts["Interest Expense"])],
        ["Accounting & Tax Fees", _fmt2(is_accounts["Accounting & Tax Fees"]) if is_accounts["Accounting & Tax Fees"] else "-"],
        ["Bank Fees", _fmt(is_accounts.get("Bank Fees", 0))],
        ["Depreciation Expense", _fmt2(is_accounts["Depreciation Expense"])],
        ["Total Expenses", _fmt2(
            is_accounts["Interest Expense"] + is_accounts["Accounting & Tax Fees"]
            + is_accounts.get("Bank Fees", 0) + is_accounts["Depreciation Expense"]
        )],
        ["Net Income", _fmt(cash_flow.get("Net Income", 0))],
    ]

    is_table = Table(is_data, colWidths=[4.5 * inch, 2 * inch])
    is_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 2), (-1, 2), GOLD_DARK),
        ('TEXTCOLOR', (0, 2), (-1, 2), white),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('FONTNAME', (0, 8), (-1, 8), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(is_table)
    story.append(Spacer(1, 16))

    # Cash Flow Metrics
    cf_data = [
        ["CASH FLOW METRICS", ""],
        ["EBITDA", _fmt(cash_flow["EBITDA"])],
        ["Less: Interest Expense", _fmt(-cash_flow["Interest Expense"])],
        ["Less: Principal Payments", _fmt(-cash_flow["Principal Payments"])],
        ["Free Cash Flow (FCF)", _fmt(cash_flow["FCF"])],
    ]
    cf_table = Table(cf_data, colWidths=[4.5 * inch, 2 * inch])
    cf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(cf_table)
    story.append(Spacer(1, 16))

    # DSCR
    dscr_data = [
        ["DEBT SERVICE", ""],
        ["Debt Service Coverage Ratio (DSCR)", "{:.2f}x".format(cash_flow['DSCR'])],
    ]
    dscr_table = Table(dscr_data, colWidths=[4.5 * inch, 2 * inch])
    dscr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(dscr_table)
    story.append(PageBreak())

    # ==================== PAGE 6: DISTRIBUTIONS ====================
    story.append(Paragraph(
        f"{FUND_NAME} | Distributions | {as_of_date.strftime('%m/%d/%Y')}",
        styles['PageHeader']
    ))

    # Investor Ownership table
    story.append(Paragraph("Investor Ownership", styles['SectionHeader']))
    own_data = [["Investor", "Ownership %"]]
    for inv_key, inv in INVESTORS.items():
        own_data.append([inv["full_name"], _pct(inv["ownership_pct"])])
    own_data.append(["Total", "100.00%"])

    own_table = Table(own_data, colWidths=[3.5 * inch, 1.5 * inch])
    own_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(own_table)
    story.append(Spacer(1, 16))

    # Quarterly Distributions table
    story.append(Paragraph("Quarterly Distributions", styles['SectionHeader']))

    inv_keys = list(INVESTORS.keys())
    inv_short = [INVESTOR_REPORT_NAMES[k] for k in inv_keys]

    dist_header = ["Quarter", "Distributable\nCash"] + inv_short
    dist_rows = [dist_header]

    all_dist_history = distribution_data.get("history", {})
    for label, amounts in all_dist_history.items():
        row = [
            label,
            _fmt(amounts["total"]),
        ] + [_fmt(amounts.get(k, 0)) for k in inv_keys]
        dist_rows.append(row)

    # Totals row
    totals_row = distribution_data.get("cumulative_by_investor", {})
    dist_rows.append([
        "Totals",
        _fmt(distribution_data.get("cumulative_total", 0)),
    ] + [_fmt(totals_row.get(k, 0)) for k in inv_keys])

    n_cols = len(dist_header)
    col_widths = [1.2 * inch, 1.0 * inch] + [0.85 * inch] * (n_cols - 2)
    dist_table = Table(dist_rows, colWidths=col_widths)
    dist_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(dist_table)

    # Build PDF
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return buffer
