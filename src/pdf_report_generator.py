"""
Premium PDF Report Generator — Agency-Grade Design
====================================================
Generates sophisticated PDF reports using reportlab with:
- Professional page templates with gradient headers and footers
- Navy gradient header bar with teal accent line
- Navy/teal/gold/emerald/rose color scheme
- Custom tables with alternating row colors and status indicators
- KPI boxes in 2x3 grid layout
- Horizontal bar charts for platform comparison
- Budget utilization gauge charts
- Colored callout boxes for insights
- Data appendix
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black, transparent
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether, PageTemplate, Frame, Flowable
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie

logger = logging.getLogger(__name__)

# Color scheme (premium agency palette)
NAVY = HexColor('#1B2A4A')
NAVY_DARK = HexColor('#0F1729')
TEAL = HexColor('#00B4D8')
GOLD = HexColor('#F4A261')
EMERALD = HexColor('#10B981')
ROSE = HexColor('#F43F5E')
SUCCESS = HexColor('#10b981')
WARNING = HexColor('#f59e0b')
DANGER = HexColor('#ef4444')
GRAY_100 = HexColor('#f3f4f6')
GRAY_200 = HexColor('#e5e7eb')
GRAY_600 = HexColor('#4b5563')
GRAY_300 = HexColor('#d1d5db')


def _safe_sum(series):
    """Safely sum a series, handling empty/None cases."""
    if series is None or (hasattr(series, 'empty') and series.empty):
        return 0
    try:
        return float(series.sum())
    except:
        return 0


def _safe_div(a, b, multiplier=1):
    """Safe division returning 0 on error."""
    try:
        if b and b != 0:
            return (a / b) * multiplier
    except:
        pass
    return 0


def _format_number(num, decimal_places=0):
    """Format number with commas and specified decimal places."""
    if num is None or np.isnan(num) or np.isinf(num):
        return "0"
    if decimal_places == 0:
        return f"{int(num):,}"
    return f"{num:,.{decimal_places}f}"


class BudgetGaugeChart(Flowable):
    """Custom gauge chart for budget utilization."""

    def __init__(self, label, spent, allocated, width=2.5*inch, height=0.8*inch):
        self.label = label
        self.spent = max(0, min(spent, allocated))
        self.allocated = allocated
        self.width = width
        self.height = height
        self.pct = (self.spent / self.allocated * 100) if self.allocated > 0 else 0

    def draw(self):
        """Draw the gauge chart."""
        drawing = Drawing(self.width, self.height)

        # Background bar
        bar_y = 0.2*inch
        bar_height = 0.3*inch
        bar_width = 1.8*inch

        # Gray background
        drawing.add(Rect(0.2*inch, bar_y, bar_width, bar_height,
                        fillColor=GRAY_200, strokeColor=GRAY_300, strokeWidth=1))

        # Colored fill bar (green/amber/red based on pct)
        fill_width = bar_width * (self.pct / 100)
        if self.pct <= 80:
            fill_color = SUCCESS
        elif self.pct <= 95:
            fill_color = WARNING
        else:
            fill_color = DANGER

        drawing.add(Rect(0.2*inch, bar_y, fill_width, bar_height,
                        fillColor=fill_color, strokeColor=None))

        # Percentage label
        pct_str = f"{self.pct:.1f}%"
        drawing.add(String(0.2*inch + bar_width + 0.15*inch, bar_y + 0.1*inch, pct_str,
                          fontName='Helvetica-Bold', fontSize=9, fillColor=NAVY))

        return drawing

    def wrap(self, aW, aH):
        return self.width, self.height


class KPIBox(Flowable):
    """Custom KPI box with top border and value display."""

    def __init__(self, label, value, vs_target="", color=TEAL, width=1.8*inch, height=1.2*inch):
        self.label = label
        self.value = value
        self.vs_target = vs_target
        self.color = color
        self.width = width
        self.height = height

    def draw(self):
        """Draw the KPI box."""
        drawing = Drawing(self.width, self.height)

        # Background
        drawing.add(Rect(0, 0, self.width, self.height,
                        fillColor=white, strokeColor=GRAY_200, strokeWidth=1.5))

        # Top colored border
        drawing.add(Rect(0, self.height - 0.15*inch, self.width, 0.15*inch,
                        fillColor=self.color, strokeColor=None))

        # Label
        drawing.add(String(0.1*inch, self.height - 0.35*inch, self.label,
                          fontName='Helvetica', fontSize=8, fillColor=GRAY_600))

        # Value
        drawing.add(String(0.1*inch, self.height - 0.65*inch, str(self.value),
                          fontName='Helvetica-Bold', fontSize=14, fillColor=NAVY))

        # Vs target
        if self.vs_target:
            drawing.add(String(0.1*inch, self.height - 0.85*inch, self.vs_target,
                              fontName='Helvetica', fontSize=7, fillColor=GRAY_600))

        return drawing

    def wrap(self, aW, aH):
        return self.width, self.height


class SimpleBarChart(Flowable):
    """Simple horizontal bar chart for platform comparison."""

    def __init__(self, data_values, labels, width=3*inch, height=1.5*inch, colors=None):
        """
        data_values: list of numeric values [val1, val2, ...]
        labels: ["Label 1", "Label 2"]
        colors: list of colors for each bar
        """
        self.data_values = data_values if isinstance(data_values, list) else list(data_values)
        self.labels = labels
        self.width = width
        self.height = height
        self.colors = colors or [NAVY, TEAL]

    def draw(self):
        """Draw horizontal bar chart."""
        drawing = Drawing(self.width, self.height)

        if not self.data_values or len(self.data_values) == 0:
            return drawing

        # Find max value for scaling
        max_val = max(self.data_values) if self.data_values else 1
        if max_val == 0 or max_val is None:
            max_val = 1

        bar_height = 0.25*inch
        spacing = 0.35*inch
        start_y = self.height - 0.3*inch

        for idx, (val, label) in enumerate(zip(self.data_values, self.labels)):
            y_pos = start_y - (idx * spacing)

            # Skip invalid values
            if val is None or val == 0:
                continue

            # Calculate bar width based on value
            bar_width = (float(val) / float(max_val)) * 2*inch if max_val > 0 else 0.1*inch

            # Draw bar
            drawing.add(Rect(0.5*inch, y_pos, bar_width, bar_height,
                            fillColor=self.colors[idx % len(self.colors)],
                            strokeColor=GRAY_300, strokeWidth=0.5))

            # Label
            drawing.add(String(0.05*inch, y_pos + 0.05*inch, label,
                              fontName='Helvetica', fontSize=8, fillColor=NAVY))

            # Value
            val_str = f"{val:,.0f}" if float(val) > 100 else f"{val:.1f}"
            drawing.add(String(0.5*inch + bar_width + 0.1*inch, y_pos + 0.05*inch, val_str,
                              fontName='Helvetica-Bold', fontSize=8, fillColor=NAVY))

        return drawing

    def wrap(self, aW, aH):
        return self.width, self.height


def _extract_platform_metrics(df, platform="meta"):
    """Extract standardized metrics from platform data."""
    if df is None or df.empty:
        return {
            "spend": 0, "impressions": 0, "reach": 0, "clicks": 0,
            "ctr": 0, "cpm": 0, "cpc": 0, "engagements": 0, "cpe": 0,
            "roas": 0, "engagement_rate": 0
        }

    if platform == "meta":
        spend = _safe_sum(df["Amount spent (INR)"]) if "Amount spent (INR)" in df.columns else 0
        impressions = _safe_sum(df["Impressions"]) if "Impressions" in df.columns else 0
        reach = _safe_sum(df["Reach"]) if "Reach" in df.columns else 0
        clicks = _safe_sum(df["Clicks (all)"]) if "Clicks (all)" in df.columns else 0
        engagements = _safe_sum(df["Post engagements"]) if "Post engagements" in df.columns else 0
        cpm = _safe_div(spend, impressions, 1000) if impressions else 0
        cpc = _safe_div(spend, clicks) if clicks else 0
        cpe = _safe_div(spend, engagements) if engagements else 0
        ctr = _safe_div(clicks, impressions, 100) if impressions else 0
        engagement_rate = _safe_div(engagements, impressions, 100) if impressions else 0
    else:  # YouTube
        spend = _safe_sum(df["Cost"]) if "Cost" in df.columns else 0
        impressions = _safe_sum(df["Impr."]) if "Impr." in df.columns else 0
        reach = impressions * 0.65
        clicks = _safe_sum(df["Clicks"]) if "Clicks" in df.columns else 0
        views = _safe_sum(df["TrueView views"]) if "TrueView views" in df.columns else 0
        cpm = _safe_div(spend, impressions, 1000) if impressions else 0
        cpc = _safe_div(spend, clicks) if clicks else 0
        ctr = _safe_div(clicks, impressions, 100) if impressions else 0
        engagement_rate = _safe_div(views, impressions, 100) if impressions else 0
        cpe = 0
        engagements = views

    return {
        "spend": spend,
        "impressions": impressions,
        "reach": reach,
        "clicks": clicks,
        "ctr": ctr,
        "cpm": cpm,
        "cpc": cpc,
        "engagements": engagements,
        "cpe": cpe,
        "roas": 0,
        "engagement_rate": engagement_rate
    }


class HeaderFooterTemplate(PageTemplate):
    """Custom page template with header and footer."""

    def __init__(self, brand_name, report_type, page_num=[0], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brand_name = brand_name
        self.report_type = report_type
        self.page_num = page_num

    def afterDrawPage(self, canvas, doc):
        """Draw header and footer after each page."""
        # Header
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(NAVY)
        canvas.drawString(0.75*inch, 10.75*inch, self.brand_name)
        canvas.drawString(6*inch, 10.75*inch, f"{self.report_type.upper()} Report")

        # Footer
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY_600)
        canvas.drawString(0.75*inch, 0.5*inch, "Confidential — AdFlow Studio")
        canvas.drawRightString(7.75*inch, 0.5*inch, f"Page {self.page_num[0]}")

        # Increment page number
        self.page_num[0] += 1


def generate_pdf_report(meta_data, google_data, brand_config, report_type="full", output_path=None):
    """Generate a premium, agency-grade PDF report.

    Args:
        meta_data: dict with raw_data, campaign_data, adset_data, ad_data (DataFrames)
        google_data: dict with raw_data, campaign_data, ad_group_data, ad_data (DataFrames)
        brand_config: dict with brand name, targets, budgets, regions, date ranges
        report_type: 'daily', 'weekly', 'monthly', 'full'
        output_path: where to save the .pdf file

    Returns:
        path to generated PDF file
    """
    if output_path is None:
        output_path = f"/tmp/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Extract brand info
    brand_name = brand_config.get("name", "Brand Report") if isinstance(brand_config, dict) else "Brand Report"
    date_generated = datetime.now().strftime("%B %d, %Y at %H:%M")

    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=1.2*inch,
        bottomMargin=0.9*inch,
    )

    # Build styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=36,
        textColor=white,
        spaceAfter=6,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )

    cover_subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontSize=18,
        textColor=white,
        spaceAfter=24,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )

    section_style = ParagraphStyle(
        'CustomSection',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=NAVY,
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold',
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=GRAY_600,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=black,
    )

    small_style = ParagraphStyle(
        'CustomSmall',
        parent=styles['Normal'],
        fontSize=8,
        textColor=GRAY_600,
    )

    # Extract metrics
    meta_metrics = _extract_platform_metrics(meta_data.get("raw_data"), "meta")
    google_metrics = _extract_platform_metrics(google_data.get("raw_data"), "youtube")

    total_spend = meta_metrics["spend"] + google_metrics["spend"]
    total_impressions = meta_metrics["impressions"] + google_metrics["impressions"]
    total_clicks = meta_metrics["clicks"] + google_metrics["clicks"]
    total_reach = meta_metrics["reach"] + google_metrics["reach"]
    total_ctr = _safe_div(total_clicks, total_impressions, 100)
    total_cpm = _safe_div(total_spend, total_impressions, 1000)
    total_engagements = meta_metrics["engagements"] + google_metrics["engagements"]

    # Build PDF content
    elements = []

    # ══════════════════════════════════════════════════════════════
    # COVER PAGE - Full Navy Background
    # ══════════════════════════════════════════════════════════════

    # Create a table for cover page with navy background
    cover_content = [
        [Spacer(1, 2*inch)],
        [Paragraph(brand_name, title_style)],
        [Spacer(1, 0.3*inch)],
        [Paragraph("Campaign Performance Report", cover_subtitle_style)],
        [Spacer(1, 1.5*inch)],
        [Paragraph(f"<b>Report Period:</b> {report_type.upper()}",
                  ParagraphStyle('CoverMeta', parent=styles['Normal'], fontSize=11,
                               textColor=white, fontName='Helvetica'))],
        [Paragraph(f"<b>Generated:</b> {date_generated}",
                  ParagraphStyle('CoverMeta', parent=styles['Normal'], fontSize=11,
                               textColor=white, fontName='Helvetica'))],
        [Spacer(1, 1.5*inch)],
        [Paragraph("CONFIDENTIAL",
                  ParagraphStyle('Confidential', parent=styles['Normal'], fontSize=14,
                               textColor=TEAL, fontName='Helvetica-Bold', alignment=TA_CENTER))],
    ]

    cover_table = Table(cover_content, colWidths=[7.5*inch])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY_DARK),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(cover_table)
    elements.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY - KPI Grid Layout (2x3)
    # ══════════════════════════════════════════════════════════════

    elements.append(Paragraph("Executive Summary", section_style))
    elements.append(Paragraph(
        "Key performance indicators for this reporting period across Meta and YouTube platforms.",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.25*inch))

    # Determine KPI colors based on performance
    def get_ctr_color(ctr_val):
        if ctr_val >= 1.5:
            return SUCCESS
        elif ctr_val >= 1.0:
            return WARNING
        else:
            return DANGER

    def get_spend_status(pct):
        if pct <= 80:
            return "On Track"
        elif pct <= 95:
            return "Monitor"
        else:
            return "Over Budget"

    meta_budget = brand_config.get("meta", {}).get("budget", 1000000) if isinstance(brand_config, dict) else 1000000
    yt_budget = brand_config.get("youtube", {}).get("budget", 500000) if isinstance(brand_config, dict) else 500000
    total_budget = meta_budget + yt_budget
    spend_pct = _safe_div(total_spend, total_budget, 100)

    # Create 2x3 KPI grid using Table
    kpi_grid_data = [
        [
            KPIBox("Total Spend", f"₹{_format_number(total_spend, 0)}", f"vs ₹{_format_number(total_budget, 0)}", TEAL),
            KPIBox("Impressions", _format_number(total_impressions, 0), "", NAVY),
            KPIBox("Reach", _format_number(total_reach, 0), "", EMERALD),
        ],
        [
            KPIBox("Clicks", _format_number(total_clicks, 0), "", GOLD),
            KPIBox("CTR %", f"{_format_number(total_ctr, 2)}%", f"Target: 1.5%", get_ctr_color(total_ctr)),
            KPIBox("CPM", f"₹{_format_number(total_cpm, 1)}", "", ROSE),
        ]
    ]

    kpi_table = Table(kpi_grid_data, colWidths=[1.95*inch, 1.95*inch, 1.95*inch])
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.3*inch))
    elements.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # CAMPAIGN PERFORMANCE - Meta & YouTube Separate Sections
    # ══════════════════════════════════════════════════════════════

    elements.append(Paragraph("Campaign Performance", section_style))
    elements.append(Spacer(1, 0.2*inch))

    # Meta campaigns
    meta_raw = meta_data.get("raw_data")
    if meta_raw is not None and not meta_raw.empty:
        elements.append(Paragraph("Meta Platforms (Facebook, Instagram, Audience Network)", ParagraphStyle(
            'MetaTitle', parent=styles['Heading3'], fontSize=11, textColor=NAVY, fontName='Helvetica-Bold'
        )))

        campaigns = meta_raw.groupby('Campaign name').agg({
            'Amount spent (INR)': 'sum',
            'Impressions': 'sum',
            'Clicks (all)': 'sum',
            'Reach': 'sum',
        }).reset_index()

        campaign_data = [["Campaign", "Spend", "Impressions", "Reach", "Clicks", "CTR", "Status"]]
        for _, row in campaigns.iterrows():
            camp_name = str(row['Campaign name'])[:35]
            spend = row['Amount spent (INR)']
            impr = row['Impressions']
            reach = row['Reach']
            clicks = row['Clicks (all)']
            ctr = _safe_div(clicks, impr, 100)

            # Determine CTR status
            if ctr >= 1.5:
                status_color = SUCCESS
                status_text = "●"
            elif ctr >= 1.0:
                status_color = WARNING
                status_text = "●"
            else:
                status_color = DANGER
                status_text = "●"

            campaign_data.append([
                camp_name,
                f"₹{_format_number(spend, 0)}",
                _format_number(impr, 0),
                _format_number(reach, 0),
                _format_number(clicks, 0),
                f"{_format_number(ctr, 2)}%",
                status_text
            ])

        campaign_table = Table(campaign_data, colWidths=[1.9*inch, 0.85*inch, 1*inch, 0.9*inch, 0.75*inch, 0.65*inch, 0.35*inch])

        # Build table style with CTR color-coding
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_300),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, GRAY_100]),
        ]

        # Color-code CTR status dots
        for row_idx in range(1, len(campaign_data)):
            ctr_val = float(campaign_data[row_idx][5].rstrip('%'))
            if ctr_val >= 1.5:
                table_style.append(('TEXTCOLOR', (-1, row_idx), (-1, row_idx), SUCCESS))
            elif ctr_val >= 1.0:
                table_style.append(('TEXTCOLOR', (-1, row_idx), (-1, row_idx), WARNING))
            else:
                table_style.append(('TEXTCOLOR', (-1, row_idx), (-1, row_idx), DANGER))

        campaign_table.setStyle(TableStyle(table_style))
        elements.append(campaign_table)
        elements.append(Spacer(1, 0.25*inch))

    # YouTube campaigns
    yt_raw = google_data.get("raw_data")
    if yt_raw is not None and not yt_raw.empty:
        elements.append(Paragraph("YouTube & Google Video Ads", ParagraphStyle(
            'YouTubeTitle', parent=styles['Heading3'], fontSize=11, textColor=NAVY, fontName='Helvetica-Bold'
        )))

        campaigns_yt = yt_raw.groupby('Campaign').agg({
            'Cost': 'sum',
            'Impr.': 'sum',
            'Clicks': 'sum',
            'TrueView views': 'sum'
        }).reset_index()

        campaign_data_yt = [["Campaign", "Cost", "Impressions", "Views", "Clicks", "CTR", "Status"]]
        for _, row in campaigns_yt.iterrows():
            camp_name = str(row['Campaign'])[:35]
            cost = row['Cost']
            impr = row['Impr.']
            views = row['TrueView views']
            clicks = row['Clicks']
            ctr = _safe_div(clicks, impr, 100)

            # Determine CTR status
            if ctr >= 1.5:
                status_color = SUCCESS
                status_text = "●"
            elif ctr >= 1.0:
                status_color = WARNING
                status_text = "●"
            else:
                status_color = DANGER
                status_text = "●"

            campaign_data_yt.append([
                camp_name,
                f"₹{_format_number(cost, 0)}",
                _format_number(impr, 0),
                _format_number(views, 0),
                _format_number(clicks, 0),
                f"{_format_number(ctr, 2)}%",
                status_text
            ])

        campaign_table_yt = Table(campaign_data_yt, colWidths=[1.9*inch, 0.85*inch, 1*inch, 0.9*inch, 0.75*inch, 0.65*inch, 0.35*inch])

        # Build table style with CTR color-coding
        table_style_yt = [
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#C41E3A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_300),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, GRAY_100]),
        ]

        # Color-code CTR status dots
        for row_idx in range(1, len(campaign_data_yt)):
            ctr_val = float(campaign_data_yt[row_idx][5].rstrip('%'))
            if ctr_val >= 1.5:
                table_style_yt.append(('TEXTCOLOR', (-1, row_idx), (-1, row_idx), SUCCESS))
            elif ctr_val >= 1.0:
                table_style_yt.append(('TEXTCOLOR', (-1, row_idx), (-1, row_idx), WARNING))
            else:
                table_style_yt.append(('TEXTCOLOR', (-1, row_idx), (-1, row_idx), DANGER))

        campaign_table_yt.setStyle(TableStyle(table_style_yt))
        elements.append(campaign_table_yt)

    elements.append(Spacer(1, 0.2*inch))
    elements.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # PLATFORM COMPARISON - Side-by-Side with Horizontal Bar Charts
    # ══════════════════════════════════════════════════════════════

    elements.append(Paragraph("Platform Performance Comparison", section_style))
    elements.append(Spacer(1, 0.2*inch))

    # Metrics comparison table
    platform_data = [
        ["Metric", "Meta", "YouTube", "Difference", "Winner"],
        ["Spend", f"₹{_format_number(meta_metrics['spend'], 0)}",
         f"₹{_format_number(google_metrics['spend'], 0)}",
         f"₹{_format_number(meta_metrics['spend'] - google_metrics['spend'], 0)}",
         "YouTube" if google_metrics['spend'] < meta_metrics['spend'] else "Meta"],
        ["Impressions", _format_number(meta_metrics['impressions'], 0),
         _format_number(google_metrics['impressions'], 0),
         _format_number(meta_metrics['impressions'] - google_metrics['impressions'], 0),
         "Meta" if meta_metrics['impressions'] > google_metrics['impressions'] else "YouTube"],
        ["Clicks", _format_number(meta_metrics['clicks'], 0),
         _format_number(google_metrics['clicks'], 0),
         _format_number(meta_metrics['clicks'] - google_metrics['clicks'], 0),
         "Meta" if meta_metrics['clicks'] > google_metrics['clicks'] else "YouTube"],
        ["CTR %", f"{_format_number(meta_metrics['ctr'], 2)}%",
         f"{_format_number(google_metrics['ctr'], 2)}%", "",
         "Meta" if meta_metrics['ctr'] > google_metrics['ctr'] else "YouTube"],
        ["CPM", f"₹{_format_number(meta_metrics['cpm'], 1)}",
         f"₹{_format_number(google_metrics['cpm'], 1)}", "",
         "Meta" if meta_metrics['cpm'] < google_metrics['cpm'] else "YouTube"],
    ]

    platform_table = Table(platform_data, colWidths=[1.4*inch, 1.3*inch, 1.3*inch, 1.3*inch, 0.95*inch])
    platform_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), GRAY_100),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY_300),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, GRAY_100]),
    ]))
    elements.append(platform_table)
    elements.append(Spacer(1, 0.3*inch))

    # Horizontal bar chart for spending comparison
    elements.append(Paragraph("Budget Allocation Comparison", ParagraphStyle(
        'ChartTitle', parent=styles['Heading3'], fontSize=11, textColor=NAVY, fontName='Helvetica-Bold'
    )))
    elements.append(Spacer(1, 0.1*inch))

    bar_chart = SimpleBarChart(
        [meta_metrics['spend'], google_metrics['spend']],
        ["Meta", "YouTube"],
        width=3.5*inch, height=1.2*inch,
        colors=[NAVY, HexColor('#C41E3A')]
    )
    elements.append(bar_chart)
    elements.append(Spacer(1, 0.2*inch))
    elements.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # BUDGET UTILIZATION - Gauge Charts with Pacing Status
    # ══════════════════════════════════════════════════════════════

    elements.append(Paragraph("Budget Utilization & Pacing Analysis", section_style))
    elements.append(Spacer(1, 0.2*inch))

    meta_spent_pct = min(100, _safe_div(meta_metrics["spend"], meta_budget, 100)) if meta_budget > 0 else 0
    yt_spent_pct = min(100, _safe_div(google_metrics["spend"], yt_budget, 100)) if yt_budget > 0 else 0
    total_spent_pct = _safe_div(total_spend, total_budget, 100) if total_budget > 0 else 0

    # Gauge charts for each platform
    gauge_table_data = [
        [
            Paragraph("Meta Platforms", ParagraphStyle('GaugeLabel', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=NAVY)),
            Paragraph("YouTube", ParagraphStyle('GaugeLabel', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=NAVY)),
        ],
        [
            BudgetGaugeChart("Meta", meta_metrics["spend"], meta_budget),
            BudgetGaugeChart("YouTube", google_metrics["spend"], yt_budget),
        ]
    ]

    gauge_table = Table(gauge_table_data, colWidths=[3*inch, 3*inch])
    gauge_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(gauge_table)
    elements.append(Spacer(1, 0.3*inch))

    # Detailed budget breakdown table
    budget_data = [
        ["Platform", "Allocated Budget", "Spent", "Remaining", "% Utilized", "Pacing Status"],
        ["Meta", f"₹{_format_number(meta_budget, 0)}", f"₹{_format_number(meta_metrics['spend'], 0)}",
         f"₹{_format_number(max(0, meta_budget - meta_metrics['spend']), 0)}", f"{_format_number(meta_spent_pct, 1)}%",
         get_spend_status(meta_spent_pct)],
        ["YouTube", f"₹{_format_number(yt_budget, 0)}", f"₹{_format_number(google_metrics['spend'], 0)}",
         f"₹{_format_number(max(0, yt_budget - google_metrics['spend']), 0)}", f"{_format_number(yt_spent_pct, 1)}%",
         get_spend_status(yt_spent_pct)],
        ["Total Campaign", f"₹{_format_number(total_budget, 0)}", f"₹{_format_number(total_spend, 0)}",
         f"₹{_format_number(max(0, total_budget - total_spend), 0)}", f"{_format_number(total_spent_pct, 1)}%",
         get_spend_status(total_spent_pct)],
    ]

    budget_table = Table(budget_data, colWidths=[1.2*inch, 1.3*inch, 1.2*inch, 1.2*inch, 0.95*inch, 1.0*inch])
    budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, -1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, -1), (-1, -1), GRAY_200),
        ('BACKGROUND', (0, 1), (-1, -2), GRAY_100),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY_300),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, GRAY_100]),
    ]))
    elements.append(budget_table)
    elements.append(Spacer(1, 0.3*inch))
    elements.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # KEY INSIGHTS & RECOMMENDATIONS - Colored Callout Boxes
    # ══════════════════════════════════════════════════════════════

    elements.append(Paragraph("Key Insights & Recommendations", section_style))
    elements.append(Spacer(1, 0.2*inch))

    # Generate insights based on data
    insights = []

    # CTR Performance
    if total_ctr >= 2.0:
        insights.append({
            'type': 'success',
            'title': 'Excellent CTR Performance',
            'text': f'CTR of {_format_number(total_ctr, 2)}% is performing well above industry benchmark of 1.5%. Maintain current creative strategy and audience targeting.'
        })
    elif total_ctr >= 1.5:
        insights.append({
            'type': 'success',
            'title': 'Strong CTR Performance',
            'text': f'CTR of {_format_number(total_ctr, 2)}% meets industry benchmark. Continue optimizing creative variations and A/B testing.'
        })
    elif total_ctr >= 1.0:
        insights.append({
            'type': 'warning',
            'title': 'Monitor CTR Performance',
            'text': f'CTR of {_format_number(total_ctr, 2)}% is below target (1.5%). Consider refreshing creative assets, refining audience targeting, or testing new ad copy.'
        })
    else:
        insights.append({
            'type': 'danger',
            'title': 'Low CTR - Immediate Action Required',
            'text': f'CTR of {_format_number(total_ctr, 2)}% is significantly below benchmark (1.5%). Urgent creative refresh and audience refinement recommended.'
        })

    # Platform efficiency
    if meta_metrics["cpm"] > 0 and google_metrics["cpm"] > 0:
        if meta_metrics["cpm"] < google_metrics["cpm"]:
            savings_pct = (google_metrics["cpm"] - meta_metrics["cpm"]) / google_metrics["cpm"] * 100
            insights.append({
                'type': 'success',
                'title': f'Meta is {_format_number(savings_pct, 1)}% More Cost-Efficient',
                'text': f'Meta CPM (₹{_format_number(meta_metrics["cpm"], 1)}) is lower than YouTube (₹{_format_number(google_metrics["cpm"], 1)}). Consider increasing Meta budget allocation.'
            })
        else:
            savings_pct = (meta_metrics["cpm"] - google_metrics["cpm"]) / meta_metrics["cpm"] * 100
            insights.append({
                'type': 'success',
                'title': f'YouTube is {_format_number(savings_pct, 1)}% More Cost-Efficient',
                'text': f'YouTube CPM (₹{_format_number(google_metrics["cpm"], 1)}) is lower than Meta (₹{_format_number(meta_metrics["cpm"], 1)}). Optimize Meta targeting or increase YouTube allocation.'
            })

    # Budget pacing
    if total_spent_pct > 95:
        insights.append({
            'type': 'danger',
            'title': 'Budget Nearly Exhausted',
            'text': f'Campaign has spent {_format_number(total_spent_pct, 1)}% of allocated budget. Review pacing and daily limits to avoid premature budget depletion.'
        })
    elif total_spent_pct > 80:
        insights.append({
            'type': 'warning',
            'title': 'Monitor Budget Pacing',
            'text': f'Campaign has spent {_format_number(total_spent_pct, 1)}% of budget. Current pacing is on track. Continue monitoring daily delivery.'
        })
    else:
        insights.append({
            'type': 'success',
            'title': 'Budget Pacing On Target',
            'text': f'Campaign has spent {_format_number(total_spent_pct, 1)}% of budget with time remaining. Current pacing is healthy and on schedule.'
        })

    # Reach efficiency
    if total_impressions > 0 and total_reach > 0:
        reach_efficiency = _safe_div(total_reach, total_impressions, 100)
        if reach_efficiency >= 40:
            insights.append({
                'type': 'success',
                'title': 'Strong Reach Efficiency',
                'text': f'Reach of {_format_number(total_reach, 0)} represents {_format_number(reach_efficiency, 1)}% reach rate on {_format_number(total_impressions, 0)} impressions. Good frequency control.'
            })

    # Render insights with colored boxes
    for insight in insights:
        if insight['type'] == 'success':
            box_color = EMERALD
            label_color = EMERALD
        elif insight['type'] == 'warning':
            box_color = WARNING
            label_color = WARNING
        else:
            box_color = DANGER
            label_color = DANGER

        # Create colored box using Table
        insight_content = [
            [Paragraph(f"<b>{insight['title']}</b><br/>{insight['text']}", normal_style)]
        ]
        insight_table = Table(insight_content, colWidths=[6.5*inch])
        insight_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_100),
            ('LEFTBORDER', (0, 0), (0, -1), 4, box_color),
            ('RIGHTBORDER', (0, 0), (-1, -1), 1, GRAY_300),
            ('TOPBORDER', (0, 0), (-1, -1), 1, GRAY_300),
            ('BOTTOMBORDER', (0, 0), (-1, -1), 1, GRAY_300),
            ('PADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(insight_table)
        elements.append(Spacer(1, 0.15*inch))

    elements.append(Spacer(1, 0.2*inch))
    elements.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # DATA APPENDIX
    # ══════════════════════════════════════════════════════════════

    elements.append(Paragraph("Data Appendix", section_style))
    elements.append(Spacer(1, 0.15*inch))

    elements.append(Paragraph("Metrics Summary", ParagraphStyle(
        'AppendixSubtitle', parent=styles['Heading3'], fontSize=10, textColor=NAVY, fontName='Helvetica-Bold'
    )))
    elements.append(Spacer(1, 0.1*inch))

    appendix_data = [
        ["Metric", "Meta", "YouTube", "Total"],
        ["Spend (INR)", f"₹{_format_number(meta_metrics['spend'], 0)}", f"₹{_format_number(google_metrics['spend'], 0)}", f"₹{_format_number(total_spend, 0)}"],
        ["Impressions", _format_number(meta_metrics['impressions'], 0), _format_number(google_metrics['impressions'], 0), _format_number(total_impressions, 0)],
        ["Reach", _format_number(meta_metrics['reach'], 0), _format_number(google_metrics['reach'], 0), _format_number(total_reach, 0)],
        ["Clicks", _format_number(meta_metrics['clicks'], 0), _format_number(google_metrics['clicks'], 0), _format_number(total_clicks, 0)],
        ["CTR %", f"{_format_number(meta_metrics['ctr'], 2)}%", f"{_format_number(google_metrics['ctr'], 2)}%", f"{_format_number(total_ctr, 2)}%"],
        ["CPM (INR)", f"₹{_format_number(meta_metrics['cpm'], 1)}", f"₹{_format_number(google_metrics['cpm'], 1)}", f"₹{_format_number(total_cpm, 1)}"],
        ["Engagements", _format_number(meta_metrics['engagements'], 0), _format_number(google_metrics['engagements'], 0), _format_number(total_engagements, 0)],
    ]

    appendix_table = Table(appendix_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.5*inch])
    appendix_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), GRAY_100),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY_300),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, GRAY_100]),
    ]))
    elements.append(appendix_table)
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph("Methodology", ParagraphStyle(
        'MethodologyTitle', parent=styles['Heading3'], fontSize=10, textColor=NAVY, fontName='Helvetica-Bold'
    )))
    elements.append(Spacer(1, 0.1*inch))

    methodology_text = (
        "This report aggregates performance data from Meta platforms (Facebook, Instagram, Audience Network) and YouTube/Google Ads. "
        "Metrics are calculated as follows: CTR = Clicks / Impressions × 100%; CPM = Spend / Impressions × 1,000; "
        "Reach = estimated unique users exposed to campaign content. All figures are based on platform reporting and may vary slightly from third-party attribution. "
        "For detailed campaign-level breakdowns and API documentation, visit the AdFlow Studio dashboard."
    )

    elements.append(Paragraph(methodology_text, small_style))
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph(
        "<i>Report generated by AdFlow Studio. Confidential. For internal use only.</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=GRAY_600, alignment=TA_CENTER)
    ))

    # ── BUILD PDF WITH CUSTOM CANVAS ──
    page_num = [1]  # Start at 1

    def canvas_maker(filename, **kwargs):
        return _NumberedCanvas(filename, brand_name=brand_name, report_type=report_type, page_num=page_num, **kwargs)

    doc.build(
        elements,
        canvasmaker=canvas_maker
    )

    logger.info(f"PDF report generated: {output_path}")
    return output_path


class _NumberedCanvas(canvas.Canvas):
    """Custom canvas with navy gradient header, teal accent line, and footer."""

    def __init__(self, filename, pagesize=None, brand_name=None, report_type=None, page_num=None, is_cover=False, **kwargs):
        super().__init__(filename, pagesize=pagesize or letter, **kwargs)
        self.brand_name = brand_name or ""
        self.report_type = report_type or ""
        self.page_num = page_num or [0]
        self.is_cover = is_cover

    def _draw_gradient_header(self):
        """Draw navy gradient header bar."""
        # Solid navy header bar (full width)
        self.setFillColor(NAVY)
        self.rect(0, 10.35*inch, 8.5*inch, 0.55*inch, fill=1, stroke=0)

        # Company logo text in top-left
        self.setFont("Helvetica-Bold", 9)
        self.setFillColor(TEAL)
        self.drawString(0.5*inch, 10.7*inch, "AdFlow Studio")

        # Report type and brand in top-right
        self.setFont("Helvetica", 9)
        self.setFillColor(white)
        self.drawRightString(7.75*inch, 10.7*inch, f"{self.report_type.upper()} Report")

        # Teal accent line under header
        self.setStrokeColor(TEAL)
        self.setLineWidth(3)
        self.line(0, 10.35*inch, 8.5*inch, 10.35*inch)

    def _draw_footer(self):
        """Draw footer with page numbers and confidentiality notice."""
        # Footer line
        self.setStrokeColor(GRAY_300)
        self.setLineWidth(1)
        self.line(0.5*inch, 0.6*inch, 8*inch, 0.6*inch)

        # Confidential notice
        self.setFont("Helvetica", 7)
        self.setFillColor(GRAY_600)
        self.drawString(0.5*inch, 0.35*inch, "Confidential | Generated by AdFlow Studio | " + datetime.now().strftime("%B %d, %Y"))

        # Page number
        self.setFont("Helvetica", 7)
        self.setFillColor(GRAY_600)
        self.drawRightString(8*inch, 0.35*inch, f"Page {self.page_num[0]} of Y")

    def showPage(self):
        """Override to add header/footer before showing page."""
        # Skip header/footer on cover page
        if not self.is_cover:
            self._draw_gradient_header()
            self._draw_footer()
            self.page_num[0] += 1

        super().showPage()
