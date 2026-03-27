"""
Brand Manager
Handles multi-brand configuration, CRUD, and per-brand pipeline execution.
"""

import json
import os
import copy
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# On Vercel, use /tmp for writable storage; locally use project dir
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

if IS_VERCEL:
    BRANDS_FILE = "/tmp/brands.json"
    REPORTS_DIR = "/tmp/reports"
    # Copy bundled brands.json to /tmp on cold start if not already there
    _bundled = os.path.join(BASE_DIR, "brands.json")
    if not os.path.exists(BRANDS_FILE) and os.path.exists(_bundled):
        import shutil
        os.makedirs(os.path.dirname(BRANDS_FILE), exist_ok=True)
        shutil.copy2(_bundled, BRANDS_FILE)
else:
    BRANDS_FILE = os.path.join(BASE_DIR, "brands.json")
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def _load_brands_file():
    if os.path.exists(BRANDS_FILE):
        with open(BRANDS_FILE) as f:
            return json.load(f)
    return {"brands": {}, "_template": _default_template()}


def _save_brands_file(data):
    with open(BRANDS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def _default_template():
    return {
        "name": "",
        "active": False,
        "meta": {
            "ad_account_id": "", "campaign_filter": "",
            "start_date": "", "end_date": "", "budget": 0,
            "regions": {},
            "targets": {"reach": 0, "impressions": 0, "engagement": 0, "thruplay": 0,
                        "cpm": 0, "cpr": 0, "cpe": 0, "cpv": 0, "er": 0, "vtr": 0}
        },
        "youtube": {
            "customer_id": "", "campaign_filter": "",
            "start_date": "", "end_date": "", "budget": 0,
            "regions": {},
            "targets": {"impressions": 0, "views": 0, "cpv": 0, "vtr": 0}
        },
        "schedule": {"daily": "09:00", "weekly": "monday 09:00", "monthly": "1st 09:00"}
    }


# ── CRUD ────────────────────────────────────────────────────────────────

def list_brands():
    data = _load_brands_file()
    brands = []
    for slug, brand in data.get("brands", {}).items():
        brand_info = {
            "slug": slug,
            "name": brand.get("name", slug),
            "active": brand.get("active", False),
            "meta_dates": f"{brand['meta'].get('start_date', '?')} → {brand['meta'].get('end_date', '?')}",
            "yt_dates": f"{brand['youtube'].get('start_date', '?')} → {brand['youtube'].get('end_date', '?')}",
            "meta_budget": brand["meta"].get("budget", 0),
            "yt_budget": brand["youtube"].get("budget", 0),
            "regions_meta": list(brand["meta"].get("regions", {}).keys()),
            "regions_yt": list(brand["youtube"].get("regions", {}).keys()),
            "schedule": brand.get("schedule", {}),
        }
        brands.append(brand_info)
    return brands


def get_brand(slug):
    data = _load_brands_file()
    return data.get("brands", {}).get(slug)


def create_brand(slug, brand_data):
    data = _load_brands_file()
    template = copy.deepcopy(data.get("_template", _default_template()))
    _deep_update(template, brand_data)
    data.setdefault("brands", {})[slug] = template
    _save_brands_file(data)
    logger.info(f"Brand created: {slug}")
    return template


def update_brand(slug, brand_data):
    data = _load_brands_file()
    if slug not in data.get("brands", {}):
        return None
    _deep_update(data["brands"][slug], brand_data)
    _save_brands_file(data)
    logger.info(f"Brand updated: {slug}")
    return data["brands"][slug]


def delete_brand(slug):
    data = _load_brands_file()
    if slug in data.get("brands", {}):
        del data["brands"][slug]
        _save_brands_file(data)
        logger.info(f"Brand deleted: {slug}")
        return True
    return False


def toggle_brand(slug, active):
    data = _load_brands_file()
    if slug in data.get("brands", {}):
        data["brands"][slug]["active"] = active
        _save_brands_file(data)
        return True
    return False


def _deep_update(base, updates):
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


# ── Report History ──────────────────────────────────────────────────────

def get_brand_reports(slug=None):
    """Get list of generated reports, optionally filtered by brand."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    reports = []
    for f in sorted(os.listdir(REPORTS_DIR), reverse=True):
        if not f.endswith(".xlsx"):
            continue
        fpath = os.path.join(REPORTS_DIR, f)
        stat = os.stat(fpath)
        info = {
            "filename": f,
            "size_kb": round(stat.st_size / 1024, 1),
            "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        # Parse brand from filename pattern: "BrandName - Type - Date.xlsx"
        parts = f.replace(".xlsx", "").split(" - ")
        if len(parts) >= 3:
            info["brand"] = parts[0].strip()
            info["report_type"] = parts[1].strip()
            info["date"] = parts[2].strip()

        if slug:
            brand = get_brand(slug)
            if brand and brand.get("name", "").lower() in f.lower():
                reports.append(info)
        else:
            reports.append(info)

    return reports[:50]  # Max 50 recent reports


# ── Per-Brand Pipeline ──────────────────────────────────────────────────

def get_report_filename(brand_name, report_type, date=None):
    date_str = date or datetime.now().strftime("%Y-%m-%d")
    return f"{brand_name} - {report_type} Report - {date_str}.xlsx"


def get_date_range_for_report_type(brand, report_type):
    """Calculate the date range based on report type."""
    today = datetime.now()

    if report_type == "daily":
        # Yesterday's data (or today if before noon)
        target_date = today - timedelta(days=1) if today.hour >= 12 else today
        return target_date.strftime("%Y-%m-%d"), target_date.strftime("%Y-%m-%d")

    elif report_type == "weekly":
        # Last 7 days
        end = today - timedelta(days=1)
        start = end - timedelta(days=6)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    elif report_type == "monthly":
        # Previous month or month-to-date
        if today.day <= 5:
            # First few days → last month
            first_of_month = today.replace(day=1)
            last_month_end = first_of_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return last_month_start.strftime("%Y-%m-%d"), last_month_end.strftime("%Y-%m-%d")
        else:
            # Month-to-date
            start = today.replace(day=1)
            return start.strftime("%Y-%m-%d"), (today - timedelta(days=1)).strftime("%Y-%m-%d")

    else:
        # Full campaign period
        meta_start = brand["meta"].get("start_date", today.strftime("%Y-%m-%d"))
        meta_end = brand["meta"].get("end_date", today.strftime("%Y-%m-%d"))
        return meta_start, min(meta_end, today.strftime("%Y-%m-%d"))


def filter_campaigns(df, campaign_col, filter_keyword):
    """Filter dataframe to only campaigns matching brand's keyword."""
    if filter_keyword and campaign_col in df.columns:
        mask = df[campaign_col].str.contains(filter_keyword, case=False, na=False)
        return df[mask]
    return df
