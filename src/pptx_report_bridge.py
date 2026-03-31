"""
PPTX Report Bridge
==================
Python wrapper that converts pandas DataFrames to JSON, then calls
the Node.js pptx_report_generator.js to produce PowerPoint files.
"""

import os
import json
import logging
import subprocess
import tempfile
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def _safe_sum(series):
    if series is None or (hasattr(series, 'empty') and series.empty):
        return 0
    try:
        return float(series.sum())
    except:
        return 0


def _safe_div(a, b, mult=1):
    try:
        if b and b != 0:
            return (a / b) * mult
    except:
        pass
    return 0


def _extract_metrics(df, platform="meta"):
    """Extract metrics from a DataFrame."""
    if df is None or df.empty:
        return {"spend": 0, "impressions": 0, "reach": 0, "clicks": 0,
                "ctr": 0, "cpm": 0, "cpc": 0, "engagements": 0}

    if platform == "meta":
        spend = _safe_sum(df["Amount spent (INR)"]) if "Amount spent (INR)" in df.columns else 0
        impressions = _safe_sum(df["Impressions"]) if "Impressions" in df.columns else 0
        reach = _safe_sum(df["Reach"]) if "Reach" in df.columns else 0
        clicks = _safe_sum(df["Clicks (all)"]) if "Clicks (all)" in df.columns else 0
        engagements = _safe_sum(df["Post engagements"]) if "Post engagements" in df.columns else 0
    else:
        spend = _safe_sum(df["Cost"]) if "Cost" in df.columns else 0
        impressions = _safe_sum(df["Impr."]) if "Impr." in df.columns else 0
        reach = impressions * 0.65
        clicks = _safe_sum(df["Clicks"]) if "Clicks" in df.columns else 0
        engagements = _safe_sum(df["TrueView views"]) if "TrueView views" in df.columns else 0

    return {
        "spend": spend,
        "impressions": impressions,
        "reach": reach,
        "clicks": clicks,
        "ctr": _safe_div(clicks, impressions, 100),
        "cpm": _safe_div(spend, impressions, 1000),
        "cpc": _safe_div(spend, clicks),
        "engagements": engagements,
    }


def _get_campaign_summary(df, name_col, spend_col, impr_col, clicks_col):
    """Group by campaign and return list of dicts."""
    if df is None or df.empty or name_col not in df.columns:
        return []

    cols = {spend_col: "sum", impr_col: "sum", clicks_col: "sum"}
    available = {k: v for k, v in cols.items() if k in df.columns}
    if not available:
        return []

    grouped = df.groupby(name_col).agg(available).reset_index()
    campaigns = []
    for _, row in grouped.iterrows():
        spend = float(row.get(spend_col, 0) or 0)
        impr = float(row.get(impr_col, 0) or 0)
        clicks = float(row.get(clicks_col, 0) or 0)
        campaigns.append({
            "name": str(row[name_col]),
            "spend": spend,
            "impressions": impr,
            "clicks": clicks,
            "ctr": _safe_div(clicks, impr, 100),
            "cpm": _safe_div(spend, impr, 1000),
        })
    return campaigns


def _get_weekly_trends(meta_df, yt_df):
    """Calculate weekly spend/CTR/impressions trends."""
    dfs = []
    if meta_df is not None and not meta_df.empty and "Day" in meta_df.columns:
        subset = meta_df[["Day"]].copy()
        subset["spend"] = meta_df.get("Amount spent (INR)", 0)
        subset["impressions"] = meta_df.get("Impressions", 0)
        subset["clicks"] = meta_df.get("Clicks (all)", 0)
        dfs.append(subset)
    if yt_df is not None and not yt_df.empty and "Day" in yt_df.columns:
        subset = yt_df[["Day"]].copy()
        subset["spend"] = yt_df.get("Cost", 0)
        subset["impressions"] = yt_df.get("Impr.", 0)
        subset["clicks"] = yt_df.get("Clicks", 0)
        dfs.append(subset)

    if not dfs:
        return []

    combined = pd.concat(dfs, ignore_index=True)
    combined["Day"] = pd.to_datetime(combined["Day"], errors="coerce")
    combined = combined.dropna(subset=["Day"])
    combined["week"] = combined["Day"].dt.isocalendar().week

    weekly = combined.groupby("week").agg({"spend": "sum", "impressions": "sum", "clicks": "sum"}).reset_index()
    trends = []
    for _, row in weekly.iterrows():
        sp = float(row["spend"] or 0)
        imp = float(row["impressions"] or 0)
        cl = float(row["clicks"] or 0)
        trends.append({
            "label": f"W{int(row['week'])}",
            "spend": sp,
            "impressions": imp,
            "clicks": cl,
            "ctr": _safe_div(cl, imp, 100),
        })
    return trends[:8]


def generate_pptx_report(meta_data, google_data, brand_config, report_type="full", output_path=None):
    """Generate a premium PPTX report.

    Args:
        meta_data: dict with raw_data, campaign_data, etc.
        google_data: dict with raw_data, campaign_data, etc.
        brand_config: brand configuration dict
        report_type: 'daily', 'weekly', 'monthly', 'full'
        output_path: where to save the .pptx file

    Returns:
        path to generated PPTX file, or None on failure
    """
    if output_path is None:
        output_path = f"/tmp/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    meta_raw = meta_data.get("raw_data", pd.DataFrame()) if meta_data else pd.DataFrame()
    yt_raw = google_data.get("raw_data", pd.DataFrame()) if google_data else pd.DataFrame()

    meta_metrics = _extract_metrics(meta_raw, "meta")
    yt_metrics = _extract_metrics(yt_raw, "youtube")

    total_spend = meta_metrics["spend"] + yt_metrics["spend"]
    total_impr = meta_metrics["impressions"] + yt_metrics["impressions"]
    total_clicks = meta_metrics["clicks"] + yt_metrics["clicks"]
    total_reach = meta_metrics["reach"] + yt_metrics["reach"]

    brand_name = brand_config.get("name", "Campaign Report") if isinstance(brand_config, dict) else "Campaign Report"
    meta_cfg = brand_config.get("meta", {}) if isinstance(brand_config, dict) else {}
    yt_cfg = brand_config.get("youtube", {}) if isinstance(brand_config, dict) else {}

    # Build JSON payload for Node.js
    payload = {
        "brandName": brand_name,
        "reportType": report_type,
        "metaDateRange": f"{meta_cfg.get('start_date', '')} to {meta_cfg.get('end_date', '')}",
        "ytDateRange": f"{yt_cfg.get('start_date', '')} to {yt_cfg.get('end_date', '')}",
        "totalSpend": total_spend,
        "totalImpressions": total_impr,
        "totalClicks": total_clicks,
        "totalReach": total_reach,
        "totalCtr": _safe_div(total_clicks, total_impr, 100),
        "totalCpm": _safe_div(total_spend, total_impr, 1000),
        "metaBudget": meta_cfg.get("budget", 0),
        "ytBudget": yt_cfg.get("budget", 0),
        "metaMetrics": meta_metrics,
        "ytMetrics": yt_metrics,
        "metaCampaigns": _get_campaign_summary(meta_raw, "Campaign name", "Amount spent (INR)", "Impressions", "Clicks (all)"),
        "ytCampaigns": _get_campaign_summary(yt_raw, "Campaign", "Cost", "Impr.", "Clicks"),
        "weeklyTrends": _get_weekly_trends(meta_raw, yt_raw),
    }

    # Write JSON to temp file
    json_path = output_path.replace(".pptx", "_data.json")
    try:
        with open(json_path, "w") as f:
            json.dump(payload, f, default=str)

        # Call Node.js generator
        script_path = os.path.join(os.path.dirname(__file__), "pptx_report_generator.js")
        node_modules = os.path.join(os.path.dirname(os.path.dirname(__file__)), "node_modules")

        env = os.environ.copy()
        env["NODE_PATH"] = node_modules

        result = subprocess.run(
            ["node", script_path, json_path, output_path],
            capture_output=True, text=True, timeout=30, env=env
        )

        if result.returncode != 0:
            logger.error(f"PPTX generation failed: {result.stderr}")
            return None

        logger.info(f"PPTX report generated: {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        logger.error("PPTX generation timed out")
        return None
    except Exception as e:
        logger.error(f"PPTX generation error: {e}")
        return None
    finally:
        # Clean up temp JSON
        try:
            os.unlink(json_path)
        except:
            pass
