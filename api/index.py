#!/usr/bin/env python3
"""
HBC Campaign Report Automation — Vercel Serverless Entry Point
==============================================================
Adapted from the Flask desktop app for Vercel's serverless environment.

Key differences from desktop version:
- Uses /tmp for file storage (ephemeral per invocation, may persist across warm starts)
- No persistent scheduler (uses Vercel Cron Jobs instead)
- No threading (reports run synchronously within the serverless function)
- brands.json is bundled and copied to /tmp on cold start
"""

import json
import os
import sys
import logging
import traceback
import copy
import base64
import io
from datetime import datetime
from pathlib import Path

# Add parent dir to path so we can import src modules
PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ_DIR)

from flask import Flask, render_template, request, jsonify, send_file, Response

# ── Environment setup for Vercel ─────────────────────────────────────
os.environ.setdefault("VERCEL", "1")

REPORTS_DIR = "/tmp/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app")

# ── Flask App ────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(PROJ_DIR, "templates"),
    static_folder=os.path.join(PROJ_DIR, "static") if os.path.exists(os.path.join(PROJ_DIR, "static")) else None,
)

# In-memory log buffer (resets on cold start, persists during warm invocations)
_logs = []


def add_log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    _logs.append({"time": ts, "level": level, "message": msg})
    if len(_logs) > 300:
        del _logs[:len(_logs) - 300]
    logger.info(msg)


# ── Imports (lazy, after sys.path is set) ────────────────────────────
from src import config
from src.report_generator import generate
from src.sample_data import generate_meta_sample, generate_yt_sample
from src.brand_manager import (
    list_brands, get_brand, create_brand, update_brand, delete_brand,
    toggle_brand, get_brand_reports, get_report_filename,
    get_date_range_for_report_type, filter_campaigns
)
from src.report_templates import (
    get_default_template, get_template, save_template,
    list_templates, delete_template, resolve_metrics,
    get_brand_template
)

import pandas as pd

# ── Column definitions ───────────────────────────────────────────────
META_COLS = [
    "Day", "Campaign name", "Ad set name", "Ad name",
    "Amount spent (INR)", "Impressions", "Reach", "Post engagements",
    "ThruPlays", "Clicks (all)", "CPM (cost per 1,000 impressions)",
    "Cost Per 1000 Reach", "Cost per post engagement", "Engagement Rate",
    "Cost per ThruPlay", "VTR - Thruplays", "CPC (all)", "CTR (all)",
    "Video Plays 100%", "Completed Views"
]
YT_COLS = [
    "Day", "Campaign", "Ad group", "Ad name", "Cost", "Impr.",
    "Avg. CPM", "TrueView views", "TrueView avg. CPV",
    "Video played to 25%", "Video played to 50%",
    "Video played to 75%", "Video played to 100%",
    "Clicks", "CTR", "VTR", "Complete Views"
]


def empty_meta():
    e = pd.DataFrame(columns=META_COLS)
    return {"raw_data": e, "campaign_data": e.copy(), "adset_data": e.copy(), "ad_data": e.copy()}


def empty_yt():
    e = pd.DataFrame(columns=YT_COLS)
    return {"raw_data": e, "campaign_data": e.copy(), "ad_group_data": e.copy(), "ad_data": e.copy()}


# ── Pipeline (synchronous for serverless) ────────────────────────────

def _apply_brand_config(brand):
    """Temporarily apply brand-specific settings to the config module."""
    from src import config as cfg
    cfg.meta.start_date = brand["meta"].get("start_date", cfg.meta.start_date)
    cfg.meta.end_date = brand["meta"].get("end_date", cfg.meta.end_date)
    cfg.meta.budget = brand["meta"].get("budget", cfg.meta.budget)
    cfg.meta.regional_budgets = {r: v.get("budget", 0) for r, v in brand["meta"].get("regions", {}).items()}
    cfg.meta.targets = brand["meta"].get("targets", cfg.meta.targets)
    cfg.google.start_date = brand["youtube"].get("start_date", cfg.google.start_date)
    cfg.google.end_date = brand["youtube"].get("end_date", cfg.google.end_date)
    cfg.google.budget = brand["youtube"].get("budget", cfg.google.budget)
    cfg.google.regional_budgets = {r: v.get("budget", 0) for r, v in brand["youtube"].get("regions", {}).items()}
    cfg.google.targets = brand["youtube"].get("targets", cfg.google.targets)
    cfg.REGIONS = list(set(
        list(brand["meta"].get("regions", {}).keys()) +
        list(brand["youtube"].get("regions", {}).keys())
    ))


def run_brand_pipeline(brand_slug, report_type="full", dry_run=False):
    """Run the pipeline for a single brand (synchronous)."""
    brand = get_brand(brand_slug)
    if not brand:
        add_log(f"Brand '{brand_slug}' not found", "error")
        return None

    brand_name = brand.get("name", brand_slug)
    add_log(f"━━━ {brand_name} — {report_type.upper()} report ━━━")

    try:
        from src import config as cfg

        # Determine date range
        if report_type == "full":
            meta_from = brand["meta"].get("start_date")
            meta_to = min(brand["meta"].get("end_date", "2099-12-31"), datetime.now().strftime("%Y-%m-%d"))
            yt_from = brand["youtube"].get("start_date")
            yt_to = min(brand["youtube"].get("end_date", "2099-12-31"), datetime.now().strftime("%Y-%m-%d"))
        else:
            meta_from, meta_to = get_date_range_for_report_type(brand, report_type)
            yt_from, yt_to = meta_from, meta_to

        add_log(f"  Meta: {meta_from} → {meta_to}")
        add_log(f"  YouTube: {yt_from} → {yt_to}")

        if dry_run:
            add_log("  [DRY RUN] Using sample data...")
            meta_data = generate_meta_sample()
            google_data = generate_yt_sample()
            meta_filter = brand["meta"].get("campaign_filter", "")
            yt_filter = brand["youtube"].get("campaign_filter", "")
            if meta_filter:
                for key in meta_data:
                    meta_data[key] = filter_campaigns(meta_data[key], "Campaign name", meta_filter) if "Campaign name" in meta_data[key].columns else meta_data[key]
            if yt_filter:
                for key in google_data:
                    google_data[key] = filter_campaigns(google_data[key], "Campaign", yt_filter) if "Campaign" in google_data[key].columns else google_data[key]
        else:
            meta_data = None
            google_data = None

            if cfg.meta.is_configured:
                try:
                    add_log(f"  Fetching Meta data (filter: {brand['meta'].get('campaign_filter', 'all')})...")
                    from src.fetch_meta import fetch_all
                    meta_data = fetch_all(meta_from, meta_to)
                    meta_filter = brand["meta"].get("campaign_filter", "")
                    if meta_filter:
                        for key in meta_data:
                            if "Campaign name" in meta_data[key].columns:
                                meta_data[key] = filter_campaigns(meta_data[key], "Campaign name", meta_filter)
                    add_log(f"  Meta: {len(meta_data['raw_data'])} rows", "success")
                except Exception as e:
                    add_log(f"  Meta fetch failed: {e}", "error")
            else:
                add_log("  Meta API not configured — using sample data", "warn")

            if cfg.google.is_configured:
                try:
                    add_log(f"  Fetching YouTube data (filter: {brand['youtube'].get('campaign_filter', 'all')})...")
                    from src.fetch_google import fetch_all
                    google_data = fetch_all(yt_from, yt_to)
                    yt_filter = brand["youtube"].get("campaign_filter", "")
                    if yt_filter:
                        for key in google_data:
                            if "Campaign" in google_data[key].columns:
                                google_data[key] = filter_campaigns(google_data[key], "Campaign", yt_filter)
                    add_log(f"  YouTube: {len(google_data['raw_data'])} rows", "success")
                except Exception as e:
                    add_log(f"  YouTube fetch failed: {e}", "error")
            else:
                add_log("  Google Ads API not configured — using sample data", "warn")

            # Fall back to sample data if APIs not configured
            if meta_data is None:
                meta_data = generate_meta_sample()
                meta_filter = brand["meta"].get("campaign_filter", "")
                if meta_filter:
                    for key in meta_data:
                        if "Campaign name" in meta_data[key].columns:
                            meta_data[key] = filter_campaigns(meta_data[key], "Campaign name", meta_filter)

            if google_data is None:
                google_data = generate_yt_sample()
                yt_filter = brand["youtube"].get("campaign_filter", "")
                if yt_filter:
                    for key in google_data:
                        if "Campaign" in google_data[key].columns:
                            google_data[key] = filter_campaigns(google_data[key], "Campaign", yt_filter)

        # Apply brand config
        _apply_brand_config(brand)

        # Generate report
        filename = get_report_filename(brand_name, report_type.capitalize())
        output_path = os.path.join(REPORTS_DIR, filename)

        # Load brand-specific report template
        brand_tmpl = get_brand_template(brand)
        tmpl_name = brand.get("report_template", "default")
        enabled_sheets = sum(1 for s in brand_tmpl.get("sheets", []) if s.get("enabled", True))
        add_log(f"  Template: {tmpl_name} ({enabled_sheets} sheets)")

        add_log(f"  Generating Excel report...")
        report_path = generate(meta_data, google_data, output_path, template=brand_tmpl)

        add_log(f"  ✓ Report: {filename}", "success")
        return report_path

    except Exception as e:
        add_log(f"  ✗ Failed: {e}", "error")
        logger.error(traceback.format_exc())
        return None


def run_all_brands(report_type="daily", dry_run=False):
    """Run pipeline for all active brands."""
    brands = list_brands()
    active = [b for b in brands if b["active"]]
    add_log(f"Running {report_type} reports for {len(active)} active brand(s)...")

    results = []
    for brand_info in active:
        result = run_brand_pipeline(brand_info["slug"], report_type, dry_run)
        results.append({"brand": brand_info["name"], "report": os.path.basename(result) if result else None})

    successes = sum(1 for r in results if r["report"])
    add_log(f"Batch complete: {successes}/{len(active)} reports generated",
            "success" if successes == len(active) else "warn")
    return results


# ── Routes: Pages ────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


# ── Routes: Status ───────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    from src import config as cfg
    brands = list_brands()

    # List reports in /tmp
    reports_list = []
    if os.path.exists(REPORTS_DIR):
        for f in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if f.endswith(".xlsx"):
                fpath = os.path.join(REPORTS_DIR, f)
                reports_list.append({
                    "filename": f,
                    "size_kb": round(os.path.getsize(fpath) / 1024, 1)
                })

    return jsonify({
        "pipeline": {
            "status": "idle",
            "last_run": None,
            "last_report": None,
            "last_error": None,
            "current_brand": None,
            "scheduler_active": False,
            "logs": _logs[-100:]
        },
        "config": {
            "meta_configured": cfg.meta.is_configured,
            "meta_account": cfg.meta.ad_account_id if cfg.meta.is_configured else None,
            "google_configured": cfg.google.is_configured,
            "google_customer": cfg.google.customer_id if cfg.google.is_configured else None,
            "email_enabled": cfg.email.enabled,
        },
        "brands": brands,
        "active_brands": sum(1 for b in brands if b["active"]),
        "total_brands": len(brands),
        "reports": reports_list[:20],
        "scheduler_active": False,
        "next_run": None,
        "scheduled_jobs": 0,
        "vercel": True,
    })


# ── Routes: API Credentials (via env vars on Vercel) ─────────────────

@app.route("/api/config", methods=["GET"])
def api_get_config():
    """Return config status (not actual secrets on Vercel)."""
    from src import config as cfg
    return jsonify({
        "META_ACCESS_TOKEN": "••••" if cfg.meta.access_token else "",
        "META_AD_ACCOUNT_ID": cfg.meta.ad_account_id or "",
        "META_APP_ID": cfg.meta.app_id or "",
        "META_APP_SECRET": "••••" if cfg.meta.app_secret else "",
        "GOOGLE_ADS_DEVELOPER_TOKEN": "••••" if cfg.google.developer_token else "",
        "GOOGLE_ADS_CLIENT_ID": cfg.google.client_id or "",
        "GOOGLE_ADS_CUSTOMER_ID": cfg.google.customer_id or "",
        "_note": "On Vercel, update API credentials via Vercel Dashboard → Settings → Environment Variables"
    })


@app.route("/api/config", methods=["POST"])
def api_save_config():
    """Config saving is not supported on Vercel — use Vercel Dashboard."""
    return jsonify({
        "ok": False,
        "message": "On Vercel, update API credentials via Vercel Dashboard → Settings → Environment Variables, then redeploy."
    }), 400


# ── Routes: Brand Management ─────────────────────────────────────────

@app.route("/api/brands", methods=["GET"])
def api_list_brands():
    return jsonify(list_brands())


@app.route("/api/brands/<slug>", methods=["GET"])
def api_get_brand(slug):
    brand = get_brand(slug)
    if brand:
        return jsonify(brand)
    return jsonify({"error": "Brand not found"}), 404


@app.route("/api/brands", methods=["POST"])
def api_create_brand():
    data = request.json
    slug = data.pop("slug", "").strip().lower().replace(" ", "-")
    if not slug:
        return jsonify({"error": "Slug is required"}), 400
    brand = create_brand(slug, data)
    add_log(f"Brand created: {data.get('name', slug)}", "success")
    return jsonify(brand), 201


@app.route("/api/brands/<slug>", methods=["PUT"])
def api_update_brand(slug):
    data = request.json
    brand = update_brand(slug, data)
    if brand:
        add_log(f"Brand updated: {brand.get('name', slug)}")
        return jsonify(brand)
    return jsonify({"error": "Brand not found"}), 404


@app.route("/api/brands/<slug>", methods=["DELETE"])
def api_delete_brand(slug):
    if delete_brand(slug):
        add_log(f"Brand deleted: {slug}")
        return jsonify({"ok": True})
    return jsonify({"error": "Brand not found"}), 404


@app.route("/api/brands/<slug>/toggle", methods=["POST"])
def api_toggle_brand(slug):
    active = request.json.get("active", True)
    toggle_brand(slug, active)
    return jsonify({"ok": True})


# ── Routes: Run Pipeline ─────────────────────────────────────────────

@app.route("/api/run", methods=["POST"])
def api_run():
    """Run pipeline synchronously (no threading in serverless)."""
    data = request.json or {}
    brand_slug = data.get("brand")
    report_type = data.get("report_type", "full")
    dry_run = data.get("dry_run", False)
    run_all = data.get("run_all", False)

    if run_all:
        results = run_all_brands(report_type, dry_run)
        successes = sum(1 for r in results if r["report"])
        return jsonify({
            "ok": True,
            "message": f"Generated {successes}/{len(results)} reports",
            "results": results
        })
    elif brand_slug:
        report_path = run_brand_pipeline(brand_slug, report_type, dry_run)
        if report_path:
            return jsonify({
                "ok": True,
                "message": f"Report generated: {os.path.basename(report_path)}",
                "filename": os.path.basename(report_path)
            })
        return jsonify({"ok": False, "message": "Pipeline failed — check logs"}), 500
    else:
        return jsonify({"error": "Specify 'brand' slug or set 'run_all': true"}), 400


# ── Routes: Report Templates ─────────────────────────────────────────

@app.route("/api/templates", methods=["GET"])
def api_list_templates():
    """List all available report templates."""
    return jsonify(list_templates())


@app.route("/api/templates/default", methods=["GET"])
def api_default_template():
    """Get the full default template structure."""
    return jsonify(resolve_metrics(get_default_template()))


@app.route("/api/templates/<name>", methods=["GET"])
def api_get_template(name):
    """Get a specific template by name."""
    tmpl = get_template(name)
    return jsonify(resolve_metrics(tmpl))


@app.route("/api/templates/<name>", methods=["PUT"])
def api_save_template(name):
    """Save/update a custom template."""
    data = request.json
    if not data:
        return jsonify({"error": "Template data required"}), 400
    result = save_template(name, data)
    add_log(f"Template saved: {name}", "success")
    return jsonify({"ok": True, "template": result})


@app.route("/api/templates/<name>", methods=["DELETE"])
def api_delete_template(name):
    """Delete a custom template."""
    if delete_template(name):
        add_log(f"Template deleted: {name}")
        return jsonify({"ok": True})
    return jsonify({"error": "Cannot delete default template or template not found"}), 400


@app.route("/api/templates/preview", methods=["POST"])
def api_preview_template():
    """Preview what sheets a template will produce."""
    data = request.json or {}
    template = data.get("template") or get_default_template()
    template = resolve_metrics(template)
    sheets = []
    for s in template.get("sheets", []):
        sheets.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "type": s.get("type"),
            "enabled": s.get("enabled", True),
            "platform": s.get("platform", "both" if s.get("type") == "summary" else ""),
            "metrics_count": len(s.get("metrics", [])) if isinstance(s.get("metrics"), list) else 0,
        })
    return jsonify({"sheets": sheets, "total_enabled": sum(1 for s in sheets if s["enabled"])})


# ── Routes: Cron Endpoints (called by Vercel Cron Jobs) ──────────────

@app.route("/api/cron/daily")
def cron_daily():
    """Vercel Cron: runs daily reports for all active brands."""
    # Verify cron secret (optional security)
    auth = request.headers.get("Authorization")
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret and auth != f"Bearer {cron_secret}":
        return jsonify({"error": "Unauthorized"}), 401

    results = run_all_brands("daily", dry_run=False)
    return jsonify({"ok": True, "type": "daily", "results": results})


@app.route("/api/cron/weekly")
def cron_weekly():
    auth = request.headers.get("Authorization")
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret and auth != f"Bearer {cron_secret}":
        return jsonify({"error": "Unauthorized"}), 401

    results = run_all_brands("weekly", dry_run=False)
    return jsonify({"ok": True, "type": "weekly", "results": results})


@app.route("/api/cron/monthly")
def cron_monthly():
    auth = request.headers.get("Authorization")
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret and auth != f"Bearer {cron_secret}":
        return jsonify({"error": "Unauthorized"}), 401

    results = run_all_brands("monthly", dry_run=False)
    return jsonify({"ok": True, "type": "monthly", "results": results})


# ── Routes: Scheduler (no-op on Vercel, uses Cron instead) ───────────

@app.route("/api/scheduler", methods=["POST"])
def api_scheduler():
    return jsonify({
        "ok": True,
        "active": False,
        "message": "On Vercel, scheduling is handled by Vercel Cron Jobs (configured in vercel.json). "
                   "Daily: 03:00 UTC, Weekly: Monday 03:00 UTC, Monthly: 1st 03:00 UTC."
    })


# ── Routes: Reports & Downloads ──────────────────────────────────────

@app.route("/api/download/<filename>")
def api_download(filename):
    path = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=filename)
    return jsonify({"error": "File not found. Reports on Vercel are stored in /tmp and may be cleared between requests."}), 404


@app.route("/api/logs")
def api_logs():
    return jsonify(_logs[-100:])


@app.route("/api/test-email", methods=["POST"])
def api_test_email():
    try:
        from src.notifier import send_test_email
        result = send_test_email()
        return jsonify({"ok": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Health check ─────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "platform": "vercel",
        "timestamp": datetime.now().isoformat(),
        "brands": len(list_brands()),
    })


# ── For local development ────────────────────────────────────────────

if __name__ == "__main__":
    os.environ.pop("VERCEL", None)
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  HBC Reports — Local Development Server")
    print(f"  Open: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
