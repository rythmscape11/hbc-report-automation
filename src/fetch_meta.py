"""
Meta Marketing API Data Fetcher
Fetches campaign, ad set, and ad level data from Meta Ads Manager.
"""

import json
import logging
import requests
import pandas as pd
from datetime import datetime
from . import config

logger = logging.getLogger(__name__)

BASE_URL = f"https://graph.facebook.com/{config.meta.api_version}"

INSIGHT_FIELDS = [
    "campaign_name", "adset_name", "ad_name",
    "spend", "impressions", "cpm", "reach",
    "actions", "cost_per_action_type",
    "video_thru_play_actions", "cost_per_thru_play",
    "clicks", "cpc", "ctr",
    "video_p25_watched_actions", "video_p50_watched_actions",
    "video_p75_watched_actions", "video_p100_watched_actions",
    "inline_post_engagement", "cost_per_inline_post_engagement"
]


def _paginate(url, params):
    all_data = []
    while url:
        resp = requests.get(url, params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        all_data.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}
    return all_data


def fetch_insights(level, date_from, date_to):
    url = f"{BASE_URL}/{config.meta.ad_account_id}/insights"
    params = {
        "access_token": config.meta.access_token,
        "level": level,
        "fields": ",".join(INSIGHT_FIELDS),
        "time_range": json.dumps({"since": date_from, "until": date_to}),
        "time_increment": 1,
        "limit": 500
    }
    return _paginate(url, params)


def _extract_action_value(actions, action_type):
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == action_type:
            return float(a.get("value", 0))
    return 0


def parse_raw_data(insights):
    rows = []
    for r in insights:
        spend = float(r.get("spend", 0))
        impressions = int(r.get("impressions", 0))
        reach = int(r.get("reach", 0))
        cpm = float(r.get("cpm", 0))

        engagements = _extract_action_value(r.get("actions"), "post_engagement")
        cpe_list = r.get("cost_per_action_type", [])
        cpe = _extract_action_value(cpe_list, "post_engagement") if cpe_list else (spend / engagements if engagements else 0)
        er = engagements / impressions if impressions else 0

        thru_plays = _extract_action_value(r.get("video_thru_play_actions"), "video_view")
        cost_per_thru = spend / thru_plays if thru_plays else 0
        vtr = thru_plays / impressions if impressions else 0

        clicks = int(r.get("clicks", 0))
        cpc = float(r.get("cpc", 0))
        ctr = float(r.get("ctr", 0)) / 100

        video_p100 = _extract_action_value(r.get("video_p100_watched_actions"), "video_view")
        cpr = (spend / reach * 1000) if reach else 0

        rows.append({
            "Day": r.get("date_start", ""),
            "Campaign name": r.get("campaign_name", ""),
            "Ad set name": r.get("adset_name", ""),
            "Ad name": r.get("ad_name", ""),
            "Amount spent (INR)": spend,
            "Impressions": impressions,
            "CPM (cost per 1,000 impressions)": cpm,
            "Reach": reach,
            "Cost Per 1000 Reach": cpr,
            "Post engagements": engagements,
            "Cost per post engagement": cpe,
            "Engagement Rate": er,
            "ThruPlays": thru_plays,
            "Cost per ThruPlay": cost_per_thru,
            "VTR - Thruplays": vtr,
            "Clicks (all)": clicks,
            "CPC (all)": cpc,
            "CTR (all)": ctr,
            "Video Plays 100%": video_p100,
            "Completed Views": video_p100
        })
    return pd.DataFrame(rows)


def _recalc_rates(df):
    df["CPM (cost per 1,000 impressions)"] = (df["Amount spent (INR)"] / df["Impressions"] * 1000).fillna(0)
    df["Cost Per 1000 Reach"] = (df["Amount spent (INR)"] / df["Reach"] * 1000).fillna(0)
    df["Cost per post engagement"] = (df["Amount spent (INR)"] / df["Post engagements"]).fillna(0)
    df["Engagement Rate"] = (df["Post engagements"] / df["Impressions"]).fillna(0)
    df["Cost per ThruPlay"] = (df["Amount spent (INR)"] / df["ThruPlays"]).fillna(0)
    df["VTR - Thruplays"] = (df["ThruPlays"] / df["Impressions"]).fillna(0)
    df["CTR (all)"] = (df["Clicks (all)"] / df["Impressions"]).fillna(0)
    df["CPC (all)"] = (df["Amount spent (INR)"] / df["Clicks (all)"]).fillna(0)
    return df


SUM_COLS = ["Amount spent (INR)", "Impressions", "Reach", "Post engagements",
            "ThruPlays", "Clicks (all)", "Video Plays 100%", "Completed Views"]


def fetch_all(date_from=None, date_to=None):
    cfg = config.meta
    date_from = date_from or cfg.start_date
    date_to = date_to or min(datetime.now().strftime("%Y-%m-%d"), cfg.end_date)

    logger.info(f"Fetching Meta data: {date_from} → {date_to}")

    insights = fetch_insights("ad", date_from, date_to)
    raw_df = parse_raw_data(insights)
    logger.info(f"Meta: {len(raw_df)} rows fetched")

    # Aggregate to campaign level
    campaign_df = raw_df.groupby(["Day", "Campaign name"]).agg({c: "sum" for c in SUM_COLS}).reset_index()
    campaign_df = _recalc_rates(campaign_df)

    # Aggregate to ad set level
    adset_df = raw_df.groupby(["Day", "Campaign name", "Ad set name"]).agg({c: "sum" for c in SUM_COLS}).reset_index()
    adset_df = _recalc_rates(adset_df)

    return {
        "raw_data": raw_df,
        "campaign_data": campaign_df,
        "adset_data": adset_df,
        "ad_data": raw_df.copy()
    }
