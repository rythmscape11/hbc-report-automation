/**
 * Premium PPTX Report Generator — Agency-Grade Design
 * =====================================================
 * Generates sophisticated PowerPoint reports using pptxgenjs with:
 * - Midnight Executive color scheme (navy/teal/gold)
 * - Professional slide masters with branded headers/footers
 * - Data-driven charts (bar, line, pie, doughnut)
 * - KPI callout cards with large stat displays
 * - Budget utilization gauges
 * - Campaign performance tables
 * - Optimization recommendations
 *
 * Usage: node src/pptx_report_generator.js <json_data_path> <output_path>
 */

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

// ── Color Palette: Midnight Executive ────────────────────────────────
const C = {
    navy:       "0F1729",
    navyLight:  "1B2A4A",
    navyMid:    "2D3E5F",
    teal:       "00B4D8",
    tealLight:  "22D3EE",
    gold:       "F4A261",
    goldLight:  "FBBF24",
    emerald:    "10B981",
    rose:       "F43F5E",
    white:      "FFFFFF",
    offWhite:   "F8FAFC",
    gray100:    "F1F5F9",
    gray200:    "E2E8F0",
    gray300:    "CBD5E1",
    gray500:    "64748B",
    gray600:    "475569",
    gray700:    "334155",
    gray900:    "0F172A",
    metaBlue:   "1877F2",
    ytRed:      "FF0000",
};

// ── Helper Functions ─────────────────────────────────────────────────
function fmt(num, decimals = 0) {
    if (num == null || isNaN(num) || !isFinite(num)) return "0";
    if (decimals === 0) return Math.round(num).toLocaleString("en-IN");
    return num.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function safeDiv(a, b, mult = 1) {
    if (!b || b === 0) return 0;
    return (a / b) * mult;
}

function pctColor(value, thresholds) {
    // thresholds: {good: 80, warn: 50} — above good=green, above warn=amber, else red
    if (value >= (thresholds.good || 80)) return C.emerald;
    if (value >= (thresholds.warn || 50)) return C.gold;
    return C.rose;
}

function ctrColor(ctr) {
    if (ctr >= 1.5) return C.emerald;
    if (ctr >= 1.0) return C.gold;
    return C.rose;
}

function makeShadow() {
    return { type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.12 };
}

// ── Slide Builders ───────────────────────────────────────────────────

function addCoverSlide(pres, data) {
    const slide = pres.addSlide();
    slide.background = { color: C.navy };

    // Decorative teal accent shape top-right
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 7.5, y: 0, w: 2.5, h: 0.08, fill: { color: C.teal }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 9.92, y: 0, w: 0.08, h: 2, fill: { color: C.teal }
    });

    // Logo / branding
    slide.addText("ADFLOW STUDIO", {
        x: 0.7, y: 0.5, w: 5, h: 0.4,
        fontSize: 12, fontFace: "Arial", color: C.teal,
        charSpacing: 6, bold: true
    });

    slide.addText("Campaign Intelligence Platform", {
        x: 0.7, y: 0.85, w: 5, h: 0.3,
        fontSize: 10, fontFace: "Calibri", color: C.gray500, italic: true
    });

    // Brand name - large
    slide.addText(data.brandName || "Campaign Report", {
        x: 0.7, y: 1.8, w: 8.5, h: 1.2,
        fontSize: 44, fontFace: "Georgia", color: C.white, bold: true
    });

    // Report type
    slide.addText(`${(data.reportType || "FULL").toUpperCase()} PERFORMANCE REPORT`, {
        x: 0.7, y: 3.0, w: 8.5, h: 0.5,
        fontSize: 16, fontFace: "Calibri", color: C.tealLight, charSpacing: 3
    });

    // Teal divider line
    slide.addShape(pres.shapes.LINE, {
        x: 0.7, y: 3.7, w: 3, h: 0,
        line: { color: C.teal, width: 3 }
    });

    // Date & meta info
    const metaLines = [];
    if (data.metaDateRange) metaLines.push({ text: `Meta Period: ${data.metaDateRange}`, options: { breakLine: true, fontSize: 11, color: C.gray300 } });
    if (data.ytDateRange) metaLines.push({ text: `YouTube Period: ${data.ytDateRange}`, options: { breakLine: true, fontSize: 11, color: C.gray300 } });
    metaLines.push({ text: `Generated: ${new Date().toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" })}`, options: { fontSize: 11, color: C.gray500 } });

    slide.addText(metaLines, {
        x: 0.7, y: 3.95, w: 8, h: 1.2, fontFace: "Calibri", valign: "top"
    });

    // Confidential footer
    slide.addText("CONFIDENTIAL", {
        x: 0.7, y: 5.1, w: 3, h: 0.3,
        fontSize: 9, fontFace: "Arial", color: C.gray600, charSpacing: 4
    });
}

function addExecutiveSummarySlide(pres, data) {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };

    // Header bar
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.navyLight }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0.7, w: 10, h: 0.04, fill: { color: C.teal }
    });
    slide.addText("EXECUTIVE SUMMARY", {
        x: 0.5, y: 0.1, w: 9, h: 0.5,
        fontSize: 18, fontFace: "Georgia", color: C.white, bold: true
    });

    // KPI Cards - 2 rows x 3 cols
    const kpis = [
        { label: "TOTAL SPEND", value: `₹${fmt(data.totalSpend)}`, color: C.teal },
        { label: "IMPRESSIONS", value: fmt(data.totalImpressions), color: C.navyMid },
        { label: "TOTAL REACH", value: fmt(data.totalReach), color: C.emerald },
        { label: "TOTAL CLICKS", value: fmt(data.totalClicks), color: C.gold },
        { label: "CLICK-THROUGH RATE", value: `${fmt(data.totalCtr, 2)}%`, color: ctrColor(data.totalCtr) },
        { label: "COST PER MILLE", value: `₹${fmt(data.totalCpm, 1)}`, color: C.rose },
    ];

    const cardW = 2.7, cardH = 1.5, gapX = 0.35, gapY = 0.3;
    const startX = 0.6, startY = 1.1;

    kpis.forEach((kpi, i) => {
        const col = i % 3, row = Math.floor(i / 3);
        const x = startX + col * (cardW + gapX);
        const y = startY + row * (cardH + gapY);

        // Card background
        slide.addShape(pres.shapes.RECTANGLE, {
            x, y, w: cardW, h: cardH,
            fill: { color: C.white }, shadow: makeShadow()
        });
        // Top accent line
        slide.addShape(pres.shapes.RECTANGLE, {
            x, y, w: cardW, h: 0.06, fill: { color: kpi.color }
        });
        // Label
        slide.addText(kpi.label, {
            x: x + 0.2, y: y + 0.2, w: cardW - 0.4, h: 0.3,
            fontSize: 9, fontFace: "Arial", color: C.gray500, bold: true, charSpacing: 1
        });
        // Value
        slide.addText(kpi.value, {
            x: x + 0.2, y: y + 0.55, w: cardW - 0.4, h: 0.7,
            fontSize: 28, fontFace: "Georgia", color: C.navy, bold: true
        });
    });

    // Footer note
    slide.addText("All metrics aggregated across Meta and YouTube platforms for the reporting period.", {
        x: 0.6, y: 5.0, w: 8.8, h: 0.4,
        fontSize: 9, fontFace: "Calibri", color: C.gray500, italic: true
    });
}

function addCampaignPerformanceSlide(pres, data, platform) {
    const slide = pres.addSlide();
    slide.background = { color: C.white };

    // Header
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.navyLight }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0.7, w: 10, h: 0.04, fill: { color: C.teal }
    });

    const isYt = platform === "youtube";
    const title = isYt ? "YOUTUBE & GOOGLE ADS PERFORMANCE" : "META PLATFORMS PERFORMANCE";
    const campaigns = isYt ? (data.ytCampaigns || []) : (data.metaCampaigns || []);
    const platformColor = isYt ? C.ytRed : C.metaBlue;

    slide.addText(title, {
        x: 0.5, y: 0.1, w: 9, h: 0.5,
        fontSize: 18, fontFace: "Georgia", color: C.white, bold: true
    });

    // Platform badge
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y: 0.95, w: 0.12, h: 0.35, fill: { color: platformColor }
    });
    slide.addText(isYt ? "YouTube Campaigns" : "Meta Campaigns", {
        x: 0.75, y: 0.95, w: 4, h: 0.35,
        fontSize: 13, fontFace: "Calibri", color: C.navyLight, bold: true
    });

    if (campaigns.length === 0) {
        slide.addText("No campaign data available for this platform.", {
            x: 1, y: 2.5, w: 8, h: 1,
            fontSize: 14, fontFace: "Calibri", color: C.gray500, italic: true, align: "center"
        });
        return;
    }

    // Table header
    const headerRow = [
        { text: "Campaign", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, fontFace: "Arial" } },
        { text: "Spend", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, fontFace: "Arial", align: "right" } },
        { text: "Impressions", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, fontFace: "Arial", align: "right" } },
        { text: "Clicks", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, fontFace: "Arial", align: "right" } },
        { text: "CTR %", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, fontFace: "Arial", align: "right" } },
        { text: "CPM", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, fontFace: "Arial", align: "right" } },
    ];

    const rows = [headerRow];
    campaigns.slice(0, 8).forEach((c, i) => {
        const rowFill = i % 2 === 0 ? C.white : C.gray100;
        const ctr = c.ctr || 0;
        const ctrClr = ctrColor(ctr);
        rows.push([
            { text: (c.name || "").substring(0, 35), options: { fill: { color: rowFill }, fontSize: 8, fontFace: "Calibri", color: C.gray700 } },
            { text: `₹${fmt(c.spend)}`, options: { fill: { color: rowFill }, fontSize: 8, fontFace: "Calibri", color: C.gray700, align: "right" } },
            { text: fmt(c.impressions), options: { fill: { color: rowFill }, fontSize: 8, fontFace: "Calibri", color: C.gray700, align: "right" } },
            { text: fmt(c.clicks), options: { fill: { color: rowFill }, fontSize: 8, fontFace: "Calibri", color: C.gray700, align: "right" } },
            { text: `${fmt(ctr, 2)}%`, options: { fill: { color: rowFill }, fontSize: 8, fontFace: "Calibri", color: ctrClr, bold: true, align: "right" } },
            { text: `₹${fmt(c.cpm, 1)}`, options: { fill: { color: rowFill }, fontSize: 8, fontFace: "Calibri", color: C.gray700, align: "right" } },
        ]);
    });

    slide.addTable(rows, {
        x: 0.5, y: 1.5, w: 9,
        colW: [3.2, 1.2, 1.3, 1.0, 0.9, 1.0],
        border: { pt: 0.5, color: C.gray200 },
        rowH: 0.35,
        margin: [3, 5, 3, 5],
    });
}

function addPlatformComparisonSlide(pres, data) {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };

    // Header
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.navyLight }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0.7, w: 10, h: 0.04, fill: { color: C.teal }
    });
    slide.addText("PLATFORM PERFORMANCE COMPARISON", {
        x: 0.5, y: 0.1, w: 9, h: 0.5,
        fontSize: 18, fontFace: "Georgia", color: C.white, bold: true
    });

    // Comparison chart: Meta vs YouTube
    const chartData = [
        { name: "Meta", labels: ["Spend (₹K)", "Impressions (K)", "Clicks", "Engagement"], values: [
            (data.metaMetrics?.spend || 0) / 1000,
            (data.metaMetrics?.impressions || 0) / 1000,
            data.metaMetrics?.clicks || 0,
            data.metaMetrics?.engagements || 0
        ]},
        { name: "YouTube", labels: ["Spend (₹K)", "Impressions (K)", "Clicks", "Engagement"], values: [
            (data.ytMetrics?.spend || 0) / 1000,
            (data.ytMetrics?.impressions || 0) / 1000,
            data.ytMetrics?.clicks || 0,
            data.ytMetrics?.engagements || 0
        ]}
    ];

    slide.addChart(pres.charts.BAR, chartData, {
        x: 0.5, y: 1.0, w: 5.5, h: 3.5, barDir: "col",
        chartColors: [C.metaBlue, C.ytRed],
        chartArea: { fill: { color: C.white }, roundedCorners: true },
        catAxisLabelColor: C.gray600, valAxisLabelColor: C.gray600,
        valGridLine: { color: C.gray200, size: 0.5 },
        catGridLine: { style: "none" },
        showLegend: true, legendPos: "b",
        legendColor: C.gray600, legendFontSize: 9,
    });

    // Spend distribution doughnut
    const totalSpend = (data.metaMetrics?.spend || 0) + (data.ytMetrics?.spend || 0);
    if (totalSpend > 0) {
        slide.addChart(pres.charts.DOUGHNUT, [{
            name: "Spend Share",
            labels: ["Meta", "YouTube"],
            values: [data.metaMetrics?.spend || 0, data.ytMetrics?.spend || 0]
        }], {
            x: 6.5, y: 1.0, w: 3, h: 2.8,
            chartColors: [C.metaBlue, C.ytRed],
            showPercent: true, showTitle: true, title: "Spend Distribution",
            titleColor: C.navyLight, titleFontSize: 11,
            dataLabelColor: C.gray700, dataLabelFontSize: 10,
        });
    }

    // Key metrics comparison table
    const metaM = data.metaMetrics || {};
    const ytM = data.ytMetrics || {};
    const compRows = [
        [
            { text: "Metric", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9 } },
            { text: "Meta", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, align: "center" } },
            { text: "YouTube", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 9, align: "center" } },
        ],
        [
            { text: "CTR %", options: { fontSize: 9 } },
            { text: `${fmt(metaM.ctr || 0, 2)}%`, options: { fontSize: 9, align: "center", color: ctrColor(metaM.ctr || 0) } },
            { text: `${fmt(ytM.ctr || 0, 2)}%`, options: { fontSize: 9, align: "center", color: ctrColor(ytM.ctr || 0) } },
        ],
        [
            { text: "CPM (₹)", options: { fontSize: 9, fill: { color: C.gray100 } } },
            { text: `₹${fmt(metaM.cpm || 0, 1)}`, options: { fontSize: 9, align: "center", fill: { color: C.gray100 } } },
            { text: `₹${fmt(ytM.cpm || 0, 1)}`, options: { fontSize: 9, align: "center", fill: { color: C.gray100 } } },
        ],
        [
            { text: "CPC (₹)", options: { fontSize: 9 } },
            { text: `₹${fmt(metaM.cpc || 0, 1)}`, options: { fontSize: 9, align: "center" } },
            { text: `₹${fmt(ytM.cpc || 0, 1)}`, options: { fontSize: 9, align: "center" } },
        ],
    ];

    slide.addTable(compRows, {
        x: 6.3, y: 4.0, w: 3.3,
        colW: [1.1, 1.1, 1.1],
        border: { pt: 0.5, color: C.gray200 },
        rowH: 0.3,
    });
}

function addBudgetPacingSlide(pres, data) {
    const slide = pres.addSlide();
    slide.background = { color: C.white };

    // Header
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.navyLight }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0.7, w: 10, h: 0.04, fill: { color: C.teal }
    });
    slide.addText("BUDGET PACING & UTILIZATION", {
        x: 0.5, y: 0.1, w: 9, h: 0.5,
        fontSize: 18, fontFace: "Georgia", color: C.white, bold: true
    });

    // Meta Budget Card
    const metaBudget = data.metaBudget || 0;
    const metaSpent = data.metaMetrics?.spend || 0;
    const metaPct = metaBudget > 0 ? Math.min(100, safeDiv(metaSpent, metaBudget, 100)) : 0;

    addBudgetCard(slide, pres, 0.5, 1.1, "Meta Platforms", metaBudget, metaSpent, metaPct, C.metaBlue);

    // YouTube Budget Card
    const ytBudget = data.ytBudget || 0;
    const ytSpent = data.ytMetrics?.spend || 0;
    const ytPct = ytBudget > 0 ? Math.min(100, safeDiv(ytSpent, ytBudget, 100)) : 0;

    addBudgetCard(slide, pres, 5.2, 1.1, "YouTube & Google", ytBudget, ytSpent, ytPct, C.ytRed);

    // Total summary
    const totalBudget = metaBudget + ytBudget;
    const totalSpent = metaSpent + ytSpent;
    const totalPct = totalBudget > 0 ? safeDiv(totalSpent, totalBudget, 100) : 0;

    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y: 4.0, w: 9, h: 1.2,
        fill: { color: C.gray100 }, shadow: makeShadow()
    });
    slide.addText("TOTAL BUDGET OVERVIEW", {
        x: 0.8, y: 4.1, w: 3, h: 0.3,
        fontSize: 10, fontFace: "Arial", color: C.gray500, bold: true, charSpacing: 2
    });
    slide.addText(`₹${fmt(totalSpent)} / ₹${fmt(totalBudget)}`, {
        x: 0.8, y: 4.4, w: 4, h: 0.5,
        fontSize: 20, fontFace: "Georgia", color: C.navy, bold: true
    });
    slide.addText(`${fmt(totalPct, 1)}% utilized  |  ₹${fmt(totalBudget - totalSpent)} remaining`, {
        x: 0.8, y: 4.85, w: 5, h: 0.3,
        fontSize: 11, fontFace: "Calibri", color: C.gray600
    });

    // Pacing status
    let status, statusColor;
    if (totalPct <= 85) { status = "ON TRACK"; statusColor = C.emerald; }
    else if (totalPct <= 95) { status = "MONITOR"; statusColor = C.gold; }
    else { status = "OVER BUDGET"; statusColor = C.rose; }

    slide.addShape(pres.shapes.RECTANGLE, {
        x: 7.5, y: 4.35, w: 1.7, h: 0.45,
        fill: { color: statusColor }
    });
    slide.addText(status, {
        x: 7.5, y: 4.35, w: 1.7, h: 0.45,
        fontSize: 10, fontFace: "Arial", color: C.white, bold: true, align: "center", valign: "middle"
    });
}

function addBudgetCard(slide, pres, x, y, label, budget, spent, pct, accentColor) {
    const cardW = 4.2, cardH = 2.5;

    slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: cardH, fill: { color: C.white }, shadow: makeShadow()
    });
    // Accent top
    slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: 0.06, fill: { color: accentColor }
    });
    // Label
    slide.addText(label, {
        x: x + 0.3, y: y + 0.2, w: cardW - 0.6, h: 0.3,
        fontSize: 12, fontFace: "Calibri", color: C.navyLight, bold: true
    });
    // Progress bar background
    slide.addShape(pres.shapes.RECTANGLE, {
        x: x + 0.3, y: y + 0.7, w: cardW - 0.6, h: 0.25, fill: { color: C.gray200 }
    });
    // Progress bar fill
    const fillW = Math.max(0.01, (cardW - 0.6) * (pct / 100));
    slide.addShape(pres.shapes.RECTANGLE, {
        x: x + 0.3, y: y + 0.7, w: fillW, h: 0.25,
        fill: { color: pctColor(100 - pct, { good: 20, warn: 5 }) }
    });
    // Percentage
    slide.addText(`${fmt(pct, 1)}%`, {
        x: x + 0.3, y: y + 1.05, w: 1.5, h: 0.3,
        fontSize: 22, fontFace: "Georgia", color: C.navy, bold: true
    });
    slide.addText("utilized", {
        x: x + 1.7, y: y + 1.1, w: 1, h: 0.25,
        fontSize: 10, fontFace: "Calibri", color: C.gray500
    });
    // Budget details
    slide.addText([
        { text: `Budget: ₹${fmt(budget)}`, options: { breakLine: true, fontSize: 10, color: C.gray600 } },
        { text: `Spent: ₹${fmt(spent)}`, options: { breakLine: true, fontSize: 10, color: C.gray600 } },
        { text: `Remaining: ₹${fmt(budget - spent)}`, options: { fontSize: 10, color: C.gray600 } },
    ], {
        x: x + 0.3, y: y + 1.5, w: cardW - 0.6, h: 0.9, fontFace: "Calibri", valign: "top"
    });
}

function addWeeklyTrendsSlide(pres, data) {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };

    // Header
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.navyLight }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0.7, w: 10, h: 0.04, fill: { color: C.teal }
    });
    slide.addText("WEEKLY PERFORMANCE TRENDS", {
        x: 0.5, y: 0.1, w: 9, h: 0.5,
        fontSize: 18, fontFace: "Georgia", color: C.white, bold: true
    });

    const weeklyData = data.weeklyTrends || [];
    if (weeklyData.length === 0) {
        slide.addText("Insufficient data for weekly trend analysis.", {
            x: 1, y: 2.5, w: 8, h: 1,
            fontSize: 14, fontFace: "Calibri", color: C.gray500, italic: true, align: "center"
        });
        return;
    }

    // Spend trend chart
    slide.addChart(pres.charts.BAR, [{
        name: "Weekly Spend (₹)",
        labels: weeklyData.map(w => w.label),
        values: weeklyData.map(w => w.spend)
    }], {
        x: 0.5, y: 0.95, w: 5.5, h: 2.5, barDir: "col",
        chartColors: [C.teal],
        chartArea: { fill: { color: C.white }, roundedCorners: true },
        catAxisLabelColor: C.gray600, valAxisLabelColor: C.gray600,
        catAxisLabelFontSize: 8, valAxisLabelFontSize: 8,
        valGridLine: { color: C.gray200, size: 0.5 },
        catGridLine: { style: "none" },
        showValue: true, dataLabelPosition: "outEnd",
        dataLabelColor: C.gray700, dataLabelFontSize: 7,
        showLegend: false,
    });

    // CTR trend line
    slide.addChart(pres.charts.LINE, [{
        name: "CTR %",
        labels: weeklyData.map(w => w.label),
        values: weeklyData.map(w => w.ctr)
    }], {
        x: 6.2, y: 0.95, w: 3.5, h: 2.5,
        lineSize: 3, lineSmooth: true,
        chartColors: [C.gold],
        chartArea: { fill: { color: C.white }, roundedCorners: true },
        catAxisLabelColor: C.gray600, valAxisLabelColor: C.gray600,
        catAxisLabelFontSize: 7, valAxisLabelFontSize: 8,
        valGridLine: { color: C.gray200, size: 0.5 },
        catGridLine: { style: "none" },
        showTitle: true, title: "CTR % Trend",
        titleColor: C.navyLight, titleFontSize: 10,
        showLegend: false,
    });

    // Week-over-week table
    const wowRows = [
        [
            { text: "Week", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 8 } },
            { text: "Spend", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 8, align: "right" } },
            { text: "Impr.", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 8, align: "right" } },
            { text: "CTR", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 8, align: "right" } },
            { text: "WoW", options: { fill: { color: C.navyLight }, color: C.white, bold: true, fontSize: 8, align: "center" } },
        ],
    ];
    weeklyData.slice(0, 6).forEach((w, i) => {
        const bg = i % 2 === 0 ? C.white : C.gray100;
        const wow = i > 0 ? ((w.spend - weeklyData[i-1].spend) / (weeklyData[i-1].spend || 1) * 100) : 0;
        const wowText = i === 0 ? "-" : `${wow >= 0 ? "+" : ""}${fmt(wow, 1)}%`;
        const wowColor = wow >= 0 ? C.emerald : C.rose;
        wowRows.push([
            { text: w.label, options: { fill: { color: bg }, fontSize: 8, fontFace: "Calibri" } },
            { text: `₹${fmt(w.spend)}`, options: { fill: { color: bg }, fontSize: 8, align: "right" } },
            { text: fmt(w.impressions), options: { fill: { color: bg }, fontSize: 8, align: "right" } },
            { text: `${fmt(w.ctr, 2)}%`, options: { fill: { color: bg }, fontSize: 8, align: "right", color: ctrColor(w.ctr) } },
            { text: wowText, options: { fill: { color: bg }, fontSize: 8, align: "center", color: i === 0 ? C.gray500 : wowColor, bold: true } },
        ]);
    });

    slide.addTable(wowRows, {
        x: 0.5, y: 3.7, w: 9, colW: [2, 1.8, 1.8, 1.2, 1.2],
        border: { pt: 0.5, color: C.gray200 }, rowH: 0.28,
    });
}

function addInsightsSlide(pres, data) {
    const slide = pres.addSlide();
    slide.background = { color: C.white };

    // Header
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.navyLight }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0.7, w: 10, h: 0.04, fill: { color: C.teal }
    });
    slide.addText("INSIGHTS & RECOMMENDATIONS", {
        x: 0.5, y: 0.1, w: 9, h: 0.5,
        fontSize: 18, fontFace: "Georgia", color: C.white, bold: true
    });

    // Generate insights based on data
    const insights = [];
    const ctr = data.totalCtr || 0;
    const cpm = data.totalCpm || 0;
    const metaPct = data.metaBudget > 0 ? safeDiv(data.metaMetrics?.spend || 0, data.metaBudget, 100) : 0;

    if (ctr < 1.0) {
        insights.push({ type: "critical", title: "CTR Below Benchmark", text: `Overall CTR of ${fmt(ctr, 2)}% is below the industry standard of 1.5%. Consider refreshing creative assets and refining audience targeting.` });
    } else if (ctr >= 2.0) {
        insights.push({ type: "positive", title: "Excellent CTR Performance", text: `CTR of ${fmt(ctr, 2)}% significantly exceeds industry benchmarks. Consider scaling budget to capitalize on strong creative performance.` });
    } else {
        insights.push({ type: "moderate", title: "CTR Within Range", text: `CTR of ${fmt(ctr, 2)}% is within acceptable range. Monitor for opportunities to optimize creative and targeting further.` });
    }

    if (cpm > 100) {
        insights.push({ type: "critical", title: "High CPM Alert", text: `CPM of ₹${fmt(cpm, 1)} is above the efficient range (₹30-80). Review ad placements and audience overlap to reduce costs.` });
    } else if (cpm < 40) {
        insights.push({ type: "positive", title: "Efficient CPM", text: `CPM of ₹${fmt(cpm, 1)} shows excellent cost efficiency. Maintaining quality at this price point demonstrates strong targeting.` });
    }

    if (metaPct > 90) {
        insights.push({ type: "critical", title: "Budget Nearly Exhausted", text: `Meta budget is ${fmt(metaPct, 0)}% utilized. Review daily spend caps to prevent early campaign termination.` });
    } else if (metaPct < 40) {
        insights.push({ type: "moderate", title: "Under-Pacing Budget", text: `Only ${fmt(metaPct, 0)}% of Meta budget utilized. Consider increasing bids or expanding targeting to improve delivery.` });
    }

    const metaCpm = data.metaMetrics?.cpm || 0;
    const ytCpm = data.ytMetrics?.cpm || 0;
    if (metaCpm > 0 && ytCpm > 0 && Math.abs(metaCpm - ytCpm) / Math.max(metaCpm, ytCpm) > 0.3) {
        const cheaper = metaCpm < ytCpm ? "Meta" : "YouTube";
        insights.push({ type: "moderate", title: "Platform Efficiency Gap", text: `${cheaper} is delivering significantly lower CPM. Consider shifting budget allocation to maximize reach.` });
    }

    if (insights.length === 0) {
        insights.push({ type: "positive", title: "Performance Status", text: "Campaign metrics are within normal parameters. Continue monitoring and optimizing based on business objectives." });
    }

    const colors = { critical: C.rose, moderate: C.gold, positive: C.emerald };
    const icons = { critical: "!", moderate: "~", positive: "✓" };

    insights.forEach((ins, i) => {
        const y = 1.0 + i * 1.05;
        const acColor = colors[ins.type] || C.gray500;

        // Card
        slide.addShape(pres.shapes.RECTANGLE, {
            x: 0.5, y, w: 9, h: 0.9, fill: { color: C.white }, shadow: makeShadow()
        });
        // Left accent
        slide.addShape(pres.shapes.RECTANGLE, {
            x: 0.5, y, w: 0.08, h: 0.9, fill: { color: acColor }
        });
        // Title
        slide.addText(ins.title, {
            x: 0.8, y, w: 8, h: 0.35,
            fontSize: 11, fontFace: "Calibri", color: C.navyLight, bold: true
        });
        // Text
        slide.addText(ins.text, {
            x: 0.8, y: y + 0.35, w: 8.5, h: 0.5,
            fontSize: 9, fontFace: "Calibri", color: C.gray600
        });
    });
}

function addClosingSlide(pres, data) {
    const slide = pres.addSlide();
    slide.background = { color: C.navy };

    slide.addText("Thank You", {
        x: 1, y: 1.5, w: 8, h: 1,
        fontSize: 40, fontFace: "Georgia", color: C.white, bold: true, align: "center"
    });

    slide.addShape(pres.shapes.LINE, {
        x: 3.5, y: 2.7, w: 3, h: 0,
        line: { color: C.teal, width: 3 }
    });

    slide.addText("For questions about this report, contact your dedicated account manager.", {
        x: 1, y: 3.0, w: 8, h: 0.5,
        fontSize: 12, fontFace: "Calibri", color: C.gray300, align: "center"
    });

    slide.addText([
        { text: "AdFlow Studio", options: { breakLine: true, fontSize: 11, color: C.tealLight, bold: true } },
        { text: `Generated: ${new Date().toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" })}`, options: { fontSize: 10, color: C.gray500 } },
    ], {
        x: 1, y: 3.8, w: 8, h: 0.8, fontFace: "Calibri", align: "center"
    });

    slide.addText("CONFIDENTIAL — This presentation contains proprietary information.", {
        x: 1, y: 5.0, w: 8, h: 0.3,
        fontSize: 8, fontFace: "Arial", color: C.gray600, align: "center"
    });
}


// ── Main Generator ───────────────────────────────────────────────────

function generatePptxReport(data, outputPath) {
    const pres = new pptxgen();
    pres.layout = "LAYOUT_16x9";
    pres.author = "AdFlow Studio";
    pres.title = `${data.brandName} — ${(data.reportType || "Full").toUpperCase()} Report`;

    // 1. Cover
    addCoverSlide(pres, data);

    // 2. Executive Summary
    addExecutiveSummarySlide(pres, data);

    // 3. Meta Campaign Performance
    if (data.metaCampaigns && data.metaCampaigns.length > 0) {
        addCampaignPerformanceSlide(pres, data, "meta");
    }

    // 4. YouTube Campaign Performance
    if (data.ytCampaigns && data.ytCampaigns.length > 0) {
        addCampaignPerformanceSlide(pres, data, "youtube");
    }

    // 5. Platform Comparison
    addPlatformComparisonSlide(pres, data);

    // 6. Budget Pacing
    addBudgetPacingSlide(pres, data);

    // 7. Weekly Trends
    addWeeklyTrendsSlide(pres, data);

    // 8. Insights
    addInsightsSlide(pres, data);

    // 9. Closing
    addClosingSlide(pres, data);

    return pres.writeFile({ fileName: outputPath }).then(() => {
        console.log(`PPTX report generated: ${outputPath}`);
        return outputPath;
    });
}


// ── CLI Entry Point ──────────────────────────────────────────────────

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.error("Usage: node pptx_report_generator.js <json_data_path> <output_path>");
        process.exit(1);
    }

    const jsonPath = args[0];
    const outputPath = args[1];

    try {
        const rawData = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
        generatePptxReport(rawData, outputPath)
            .then(() => process.exit(0))
            .catch(err => { console.error(err); process.exit(1); });
    } catch (e) {
        console.error("Failed to parse input JSON:", e.message);
        process.exit(1);
    }
}

module.exports = { generatePptxReport };
