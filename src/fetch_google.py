"""
Google Ads API Data Fetcher
Fetches YouTube/Video campaign data from Google Ads.
"""

import logging
import pandas as pd
from datetime import datetime
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from . import config

logger = logging.getLogger(__name__)


def _get_client():
    cfg = config.google
    creds = {
        "developer_token": cfg.developer_token,
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "refresh_token": cfg.refresh_token,
        "use_proto_plus": True
    }
    if cfg.login_customer_id:
        creds["login_customer_id"] = cfg.login_customer_id
    return GoogleAdsClient.load_from_dict(creds)


QUERIES = {
    "campaign": """
        SELECT segments.date, campaign.name,
               metrics.cost_micros, metrics.impressions, metrics.video_views,
               metrics.video_quartile_p25_rate, metrics.video_quartile_p50_rate,
               metrics.video_quartile_p75_rate, metrics.video_quartile_p100_rate,
               metrics.clicks, metrics.ctr
        FROM campaign
        WHERE segments.date BETWEEN '{from_}' AND '{to_}'
          AND campaign.advertising_channel_type = 'VIDEO'
        ORDER BY segments.date
    """,
    "ad_group": """
        SELECT segments.date, campaign.name, ad_group.name,
               metrics.cost_micros, metrics.impressions, metrics.video_views,
               metrics.video_quartile_p25_rate, metrics.video_quartile_p50_rate,
               metrics.video_quartile_p75_rate, metrics.video_quartile_p100_rate,
               metrics.clicks, metrics.ctr
        FROM ad_group
        WHERE segments.date BETWEEN '{from_}' AND '{to_}'
          AND campaign.advertising_channel_type = 'VIDEO'
        ORDER BY segments.date
    """,
    "ad": """
        SELECT segments.date, campaign.name, ad_group.name, ad_group_ad.ad.name,
               metrics.cost_micros, metrics.impressions, metrics.video_views,
               metrics.video_quartile_p25_rate, metrics.video_quartile_p50_rate,
               metrics.video_quartile_p75_rate, metrics.video_quartile_p100_rate,
               metrics.clicks, metrics.ctr
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{from_}' AND '{to_}'
          AND campaign.advertising_channel_type = 'VIDEO'
        ORDER BY segments.date
    """
}


def _run_query(client, customer_id, level, date_from, date_to):
    ga_service = client.get_service("GoogleAdsService")
    query = QUERIES[level].format(from_=date_from, to_=date_to)

    rows = []
    try:
        response = ga_service.search_stream(customer_id=customer_id, query=query)
        for batch in response:
            for r in batch.results:
                cost = r.metrics.cost_micros / 1_000_000
                impr = r.metrics.impressions
                views = r.metrics.video_views
                cpv = cost / views if views else 0
                cpm = cost / impr * 1000 if impr else 0
                p25 = r.metrics.video_quartile_p25_rate
                p50 = r.metrics.video_quartile_p50_rate
                p75 = r.metrics.video_quartile_p75_rate
                p100 = r.metrics.video_quartile_p100_rate
                completed = views * p100 if p100 else 0

                entry = {
                    "Day": r.segments.date,
                    "Campaign": r.campaign.name,
                    "Cost": cost,
                    "Impr.": impr,
                    "Avg. CPM": cpm,
                    "TrueView views": views,
                    "TrueView avg. CPV": cpv,
                    "Video played to 25%": p25,
                    "Video played to 50%": p50,
                    "Video played to 75%": p75,
                    "Video played to 100%": p100,
                    "Clicks": r.metrics.clicks,
                    "CTR": r.metrics.ctr,
                    "VTR": views / impr if impr else 0,
                    "Complete Views": completed,
                }
                if level in ("ad_group", "ad"):
                    entry["Ad group"] = r.ad_group.name
                if level == "ad":
                    entry["Ad name"] = r.ad_group_ad.ad.name
                rows.append(entry)

    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex.failure.errors[0].message}")
        raise

    return pd.DataFrame(rows)


def fetch_all(date_from=None, date_to=None):
    cfg = config.google
    date_from = date_from or cfg.start_date
    date_to = date_to or min(datetime.now().strftime("%Y-%m-%d"), cfg.end_date)

    logger.info(f"Fetching Google Ads data: {date_from} → {date_to}")

    client = _get_client()
    cid = cfg.customer_id.replace("-", "")

    campaign_df = _run_query(client, cid, "campaign", date_from, date_to)
    logger.info(f"Google Ads campaigns: {len(campaign_df)} rows")

    ad_group_df = _run_query(client, cid, "ad_group", date_from, date_to)
    logger.info(f"Google Ads ad groups: {len(ad_group_df)} rows")

    ad_df = _run_query(client, cid, "ad", date_from, date_to)
    logger.info(f"Google Ads ads: {len(ad_df)} rows")

    return {
        "raw_data": ad_df,
        "campaign_data": campaign_df,
        "ad_group_data": ad_group_df,
        "ad_data": ad_df
    }
