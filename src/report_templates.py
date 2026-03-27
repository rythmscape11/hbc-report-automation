"""
Report Template System
======================
Allows full customization of report structure:
- Which sheets to include
- What metrics appear in each sheet
- Column definitions, ordering, and aggregation types
- Styling (colors, fonts)
- Per-brand template overrides

Templates are JSON-serializable dicts stored in brands.json under each brand's
"report_template" key. A global default template is used when a brand doesn't
define its own.
"""

import json
import os
import copy
import logging

logger = logging.getLogger(__name__)

# ── Default Template ─────────────────────────────────────────────────

DEFAULT_TEMPLATE = {
    "name": "HBC Standard Report",
    "version": "1.0",

    # ── Global styling ───────────────────────────────────────────────
    "styling": {
        "primary_color": "4472C4",
        "primary_dark": "2F5496",
        "accent_color": "70AD47",
        "warning_color": "FFC000",
        "header_bg": "D6E4F0",
        "font_family": "Arial",
        "title_size": 12,
        "header_size": 10,
        "data_size": 9,
    },

    # ── Sheets to include (in order) ────────────────────────────────
    "sheets": [
        {
            "id": "targeted_vs_achieved",
            "name": "Targeted  Vs Achieved",
            "type": "summary",
            "enabled": True,
            "description": "Overall + regional comparison of targets vs actuals",
            "platforms": {
                "meta": {
                    "start_col": 2,
                    "label": "META",
                    "volume_metrics": [
                        {"label": "Amount Spent", "target_key": "amount_spent", "data_col": "Amount spent (INR)", "agg": "sum"},
                        {"label": "Reach", "target_key": "reach", "data_col": "Reach", "agg": "sum"},
                        {"label": "Impr.", "target_key": "impressions", "data_col": "Impressions", "agg": "sum"},
                        {"label": "Engagement", "target_key": "engagement", "data_col": "Post engagements", "agg": "sum"},
                        {"label": "Thurplays", "target_key": "thruplay", "data_col": "ThruPlays", "agg": "sum"}
                    ],
                    "rate_metrics": [
                        {"label": "CPM", "target_key": "cpm", "formula": "spend/impressions*1000"},
                        {"label": "CPR", "target_key": "cpr", "formula": "spend/reach*1000", "prefix": "₹"},
                        {"label": "CPE", "target_key": "cpe", "formula": "spend/engagement", "prefix": "₹"},
                        {"label": "CPV", "target_key": "cpv", "formula": "spend/thruplay", "prefix": "₹"},
                        {"label": "ER", "target_key": "er", "formula": "engagement/impressions"},
                        {"label": "VTR", "target_key": "vtr", "formula": "thruplay/impressions"}
                    ],
                    "extra_metrics": [
                        {"label": "Completed Views", "data_col": "Completed Views", "agg": "sum"},
                        {"label": "VCR", "formula": "completed_views/impressions"},
                        {"label": "Clicks", "data_col": "Clicks (all)", "agg": "sum"},
                        {"label": "CTR", "formula": "clicks/impressions"},
                        {"label": "Frequency", "formula": "impressions/reach"}
                    ],
                    "regional_metrics": [
                        {"label": "Amount Spent", "data_col": "Amount spent (INR)", "agg": "sum", "show_budget": True},
                        {"label": "Reach", "data_col": "Reach", "agg": "sum"},
                        {"label": "Impr.", "data_col": "Impressions", "agg": "sum"},
                        {"label": "Engagement", "data_col": "Post engagements", "agg": "sum"},
                        {"label": "Thurplays", "data_col": "ThruPlays", "agg": "sum"},
                        {"label": "CPM", "formula": "spend/impressions*1000"},
                        {"label": "CPR", "formula": "spend/reach*1000"},
                        {"label": "CPE", "formula": "spend/engagement"},
                        {"label": "CPV", "formula": "spend/thruplay"},
                        {"label": "ER", "formula": "engagement/impressions"},
                        {"label": "VTR", "formula": "thruplay/impressions"},
                        {"label": "Completed Views", "data_col": "Completed Views", "agg": "sum"},
                        {"label": "Clicks", "data_col": "Clicks (all)", "agg": "sum"},
                        {"label": "CTR", "formula": "clicks/impressions"},
                        {"label": "Frequency", "formula": "impressions/reach"}
                    ]
                },
                "youtube": {
                    "start_col": 11,
                    "label": "GOOGLE",
                    "volume_metrics": [
                        {"label": "Amount Spent", "target_key": "amount_spent", "data_col": "Cost", "agg": "sum"},
                        {"label": "Reach", "target_key": None, "data_col": None, "agg": "none", "default": "--"},
                        {"label": "Impr.", "target_key": "impressions", "data_col": "Impr.", "agg": "sum"},
                        {"label": "Views", "target_key": "views", "data_col": "TrueView views", "agg": "sum"},
                        {"label": "CPV", "target_key": "cpv", "formula": "spend/views"},
                        {"label": "VTR", "target_key": "vtr", "formula": "views/impressions"}
                    ],
                    "rate_metrics": [],
                    "extra_metrics": [
                        {"label": "Completed Views", "data_col": "Complete Views", "agg": "sum"},
                        {"label": "VCR", "formula": "completed_views/views"},
                        {"label": "Video Played 25%", "data_col": "Video played to 25%", "agg": "mean"},
                        {"label": "Video Played 50%", "data_col": "Video played to 50%", "agg": "mean"},
                        {"label": "Video Played 75%", "data_col": "Video played to 75%", "agg": "mean"},
                        {"label": "Video Played 100%", "data_col": "Video played to 100%", "agg": "mean"},
                        {"label": "Clicks", "data_col": "Clicks", "agg": "sum"},
                        {"label": "CTR", "formula": "clicks/impressions"},
                        {"label": "Frequency", "formula": "impressions/views"}
                    ],
                    "regional_metrics": [
                        {"label": "Amount Spent", "data_col": "Cost", "agg": "sum", "show_budget": True},
                        {"label": "Reach", "default": "--"},
                        {"label": "Impr.", "data_col": "Impr.", "agg": "sum"},
                        {"label": "Views", "data_col": "TrueView views", "agg": "sum"},
                        {"label": "CPV", "formula": "spend/views"},
                        {"label": "VTR", "formula": "views/impressions"},
                        {"label": "Completed Views", "data_col": "Complete Views", "agg": "sum"},
                        {"label": "VCR", "formula": "completed_views/views"},
                        {"label": "Video Played 25%", "data_col": "Video played to 25%", "agg": "mean"},
                        {"label": "Video Played 50%", "data_col": "Video played to 50%", "agg": "mean"},
                        {"label": "Video Played 75%", "data_col": "Video played to 75%", "agg": "mean"},
                        {"label": "Video Played 100%", "data_col": "Video played to 100%", "agg": "mean"},
                        {"label": "Clicks", "data_col": "Clicks", "agg": "sum"},
                        {"label": "CTR", "formula": "clicks/impressions"},
                        {"label": "Frequency", "formula": "impressions/views"}
                    ]
                }
            }
        },
        {
            "id": "meta_campaign_overview",
            "name": "Meta - Campaign Overview",
            "type": "overview",
            "enabled": True,
            "platform": "meta",
            "group_col": "Campaign name",
            "metrics": [
                {"label": "Spent", "data_col": "Amount spent (INR)", "agg": "sum"},
                {"label": "Reach", "data_col": "Reach", "agg": "sum"},
                {"label": "Impressions", "data_col": "Impressions", "agg": "sum"},
                {"label": "CPR", "data_col": "Cost Per 1000 Reach", "agg": "wavg"},
                {"label": "CPM", "data_col": "CPM (cost per 1,000 impressions)", "agg": "wavg"},
                {"label": "Engagements", "data_col": "Post engagements", "agg": "sum"},
                {"label": "CPE", "data_col": "Cost per post engagement", "agg": "wavg"},
                {"label": "ER", "data_col": "Engagement Rate", "agg": "wavg"},
                {"label": "ThruPlays", "data_col": "ThruPlays", "agg": "sum"},
                {"label": "Cost per ThruPlay", "data_col": "Cost per ThruPlay", "agg": "wavg"},
                {"label": "VTR", "data_col": "VTR - Thruplays", "agg": "wavg"},
                {"label": "Clicks", "data_col": "Clicks (all)", "agg": "sum"},
                {"label": "CPC", "data_col": "CPC (all)", "agg": "wavg"},
                {"label": "CTR", "data_col": "CTR (all)", "agg": "wavg"},
                {"label": "Completed Views", "data_col": "Completed Views", "agg": "sum"}
            ]
        },
        {
            "id": "meta_adset_overview",
            "name": "Meta - Ad Set Overview",
            "type": "overview",
            "enabled": True,
            "platform": "meta",
            "group_col": "Ad set name",
            "metrics": "inherit:meta_campaign_overview"
        },
        {
            "id": "meta_ad_overview",
            "name": "Meta - Ad Overview",
            "type": "overview",
            "enabled": True,
            "platform": "meta",
            "group_col": "Ad name",
            "metrics": "inherit:meta_campaign_overview"
        },
        {
            "id": "meta_raw_data",
            "name": "Meta - Raw Data",
            "type": "raw",
            "enabled": True,
            "platform": "meta",
            "data_key": "raw_data",
            "columns": [
                "Day", "Campaign name", "Ad set name", "Ad name",
                "Amount spent (INR)", "Impressions", "Reach", "Post engagements",
                "ThruPlays", "Clicks (all)", "CPM (cost per 1,000 impressions)",
                "Cost Per 1000 Reach", "Cost per post engagement", "Engagement Rate",
                "Cost per ThruPlay", "VTR - Thruplays", "CPC (all)", "CTR (all)",
                "Video Plays 100%", "Completed Views"
            ]
        },
        {
            "id": "yt_campaign_overview",
            "name": "YT - Campaign Overview",
            "type": "overview",
            "enabled": True,
            "platform": "youtube",
            "group_col": "Campaign",
            "metrics": [
                {"label": "Cost", "data_col": "Cost", "agg": "sum"},
                {"label": "Impr.", "data_col": "Impr.", "agg": "sum"},
                {"label": "Avg. CPM", "data_col": "Avg. CPM", "agg": "wavg"},
                {"label": "TrueView views", "data_col": "TrueView views", "agg": "sum"},
                {"label": "TrueView avg. CPV", "data_col": "TrueView avg. CPV", "agg": "wavg"},
                {"label": "Video played to 25%", "data_col": "Video played to 25%", "agg": "wavg"},
                {"label": "Video played to 50%", "data_col": "Video played to 50%", "agg": "wavg"},
                {"label": "Video played to 75%", "data_col": "Video played to 75%", "agg": "wavg"},
                {"label": "Video played to 100%", "data_col": "Video played to 100%", "agg": "wavg"},
                {"label": "Clicks", "data_col": "Clicks", "agg": "sum"},
                {"label": "CTR", "data_col": "CTR", "agg": "wavg"},
                {"label": "Complete Views", "data_col": "Complete Views", "agg": "sum"}
            ]
        },
        {
            "id": "meta_creative_perf",
            "name": "Meta - Creative Performance",
            "type": "creative",
            "enabled": True,
            "platform": "meta",
            "group_col": "Ad name",
            "agg_columns": {
                "Amount spent (INR)": "sum",
                "Impressions": "sum",
                "Reach": "sum",
                "Post engagements": "sum",
                "ThruPlays": "sum",
                "Clicks (all)": "sum"
            },
            "calculated_columns": [
                {"name": "CTR", "formula": "Clicks (all) / Impressions"},
                {"name": "ER", "formula": "Post engagements / Impressions"},
                {"name": "VTR", "formula": "ThruPlays / Impressions"}
            ]
        },
        {
            "id": "yt_adgroup_overview",
            "name": "YT - Ad Group Overview",
            "type": "overview",
            "enabled": True,
            "platform": "youtube",
            "group_col": "Ad group",
            "metrics": "inherit:yt_campaign_overview"
        },
        {
            "id": "yt_ad_overview",
            "name": "YT - Ad Overview",
            "type": "overview",
            "enabled": True,
            "platform": "youtube",
            "group_col": "Ad name",
            "metrics": "inherit:yt_campaign_overview"
        },
        {
            "id": "yt_creative_perf",
            "name": "YT Creative Performance",
            "type": "creative",
            "enabled": True,
            "platform": "youtube",
            "group_col": "Ad name",
            "agg_columns": {
                "Cost": "sum",
                "Impr.": "sum",
                "TrueView views": "sum",
                "Clicks": "sum",
                "Complete Views": "sum"
            },
            "calculated_columns": [
                {"name": "CTR", "formula": "Clicks / Impr."},
                {"name": "VTR", "formula": "TrueView views / Impr."}
            ]
        },
        {
            "id": "sov",
            "name": "SOV",
            "type": "placeholder",
            "enabled": True,
            "title": "Share of Voice",
            "description": "Add SOV data manually or via custom columns"
        },
        {
            "id": "yt_raw_data",
            "name": "YT - Product Raw Data",
            "type": "raw",
            "enabled": True,
            "platform": "youtube",
            "data_key": "raw_data",
            "columns": [
                "Day", "Campaign", "Ad group", "Ad name", "Cost", "Impr.",
                "Avg. CPM", "TrueView views", "TrueView avg. CPV",
                "Video played to 25%", "Video played to 50%",
                "Video played to 75%", "Video played to 100%",
                "Clicks", "CTR", "VTR", "Complete Views"
            ]
        }
    ],

    # ── Custom sheet types users can add ─────────────────────────────
    "custom_sheets": []
}


# ── Template Management ──────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
TEMPLATES_FILE = "/tmp/report_templates.json" if IS_VERCEL else os.path.join(BASE_DIR, "report_templates.json")


def _load_templates():
    """Load custom templates from disk."""
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE) as f:
            return json.load(f)
    return {}


def _save_templates(templates):
    """Save custom templates to disk."""
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(templates, f, indent=2)


def get_default_template():
    """Return a deep copy of the default template."""
    return copy.deepcopy(DEFAULT_TEMPLATE)


def get_template(template_name=None):
    """Get a template by name, falling back to default."""
    if not template_name or template_name == "default":
        return get_default_template()

    templates = _load_templates()
    if template_name in templates:
        # Merge with default to fill any missing keys
        tmpl = get_default_template()
        _deep_merge(tmpl, templates[template_name])
        return tmpl

    return get_default_template()


def save_template(name, template_data):
    """Save a custom template."""
    templates = _load_templates()
    templates[name] = template_data
    _save_templates(templates)
    return template_data


def list_templates():
    """List all available template names."""
    templates = _load_templates()
    result = [{"name": "default", "label": "HBC Standard Report", "custom": False}]
    for name, tmpl in templates.items():
        result.append({
            "name": name,
            "label": tmpl.get("name", name),
            "custom": True,
            "sheets": len([s for s in tmpl.get("sheets", []) if s.get("enabled", True)])
        })
    return result


def delete_template(name):
    """Delete a custom template."""
    if name == "default":
        return False
    templates = _load_templates()
    if name in templates:
        del templates[name]
        _save_templates(templates)
        return True
    return False


def resolve_metrics(template):
    """Resolve 'inherit:' references in sheet metrics."""
    sheets_by_id = {s["id"]: s for s in template.get("sheets", [])}

    for sheet in template.get("sheets", []):
        metrics = sheet.get("metrics")
        if isinstance(metrics, str) and metrics.startswith("inherit:"):
            parent_id = metrics.split(":", 1)[1]
            if parent_id in sheets_by_id:
                sheet["metrics"] = copy.deepcopy(sheets_by_id[parent_id].get("metrics", []))

    return template


def get_brand_template(brand):
    """Get the report template for a specific brand."""
    template_name = brand.get("report_template", "default")
    tmpl = get_template(template_name)

    # Apply any per-brand sheet overrides
    brand_overrides = brand.get("sheet_overrides", {})
    if brand_overrides:
        for sheet in tmpl.get("sheets", []):
            if sheet["id"] in brand_overrides:
                override = brand_overrides[sheet["id"]]
                if "enabled" in override:
                    sheet["enabled"] = override["enabled"]
                if "name" in override:
                    sheet["name"] = override["name"]
                if "metrics" in override:
                    sheet["metrics"] = override["metrics"]

    return resolve_metrics(tmpl)


def _deep_merge(base, override):
    """Recursively merge override into base dict."""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
