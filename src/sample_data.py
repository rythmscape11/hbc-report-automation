"""
Sample Data Generator
Used for --dry-run testing without API credentials.
"""

import pandas as pd
import numpy as np
from datetime import datetime


def _seed_val(date, campaign, base, spread):
    h = hash(str(date) + campaign) % 1000
    return base + spread * h / 1000


def generate_meta_sample():
    dates = pd.date_range("2026-02-27", "2026-03-25", freq="D")
    campaigns = [
        "SP - Engagement - Soap - Karnataka  - 27th Feb'26",
        "SP - Engagement - Soap - Tamil Nadu - 27th Feb'26",
        "SP - Engagement - Soap - Telangana - 27th Feb'26",
        "SP - Video Views - Soap - Maharashtra - 27th Feb'26",
        "SP - Engagement - Shampoo - Delhi NCR - 1st Mar'26",
        "SP - Engagement - Shampoo - Mumbai - 1st Mar'26",
        "SP - Engagement - Shampoo - Bangalore - 1st Mar'26",
        "SP - Video Views - Shampoo - Kolkata - 1st Mar'26",
        "SP - Engagement - Facewash - Delhi NCR - 1st Apr'26",
        "SP - Engagement - Facewash - Pune - 1st Apr'26",
        "MGD - Engagement - UAE - 1st Feb'26",
        "MGD - Engagement - KSA - 1st Feb'26",
        "MGD - Video Views - Singapore - 1st Feb'26",
        "MGD - Video Views - USA - 1st Feb'26",
        "MGD - Engagement - Malaysia - 1st Feb'26",
        "MGD - Video Views - Australia - 1st Feb'26",
    ]
    ad_sets = ["Parents + Product + Competitors - Urban", "Parents + Product + Competitors - Rural"]
    ad_names = ["Ad - Hindi", "Ad - Kannada", "Ad - Tamil", "Ad - English"]

    rows = []
    for date in dates:
        for campaign in campaigns:
            for ad_set in ad_sets[:1]:
                for ad_name in ad_names[:1]:
                    spend = round(_seed_val(date, campaign, 3000, 4000), 2)
                    impr = int(_seed_val(date, campaign, 20000, 15000))
                    reach = int(impr * 0.7)
                    eng = int(impr * 0.2)
                    thru = int(impr * 0.04)
                    clicks = int(impr * 0.01)

                    rows.append({
                        "Day": date.strftime("%Y-%m-%d"),
                        "Campaign name": campaign,
                        "Ad set name": ad_set,
                        "Ad name": ad_name,
                        "Amount spent (INR)": spend,
                        "Impressions": impr,
                        "CPM (cost per 1,000 impressions)": round(spend / impr * 1000, 2) if impr else 0,
                        "Reach": reach,
                        "Cost Per 1000 Reach": round(spend / reach * 1000, 2) if reach else 0,
                        "Post engagements": eng,
                        "Cost per post engagement": round(spend / eng, 4) if eng else 0,
                        "Engagement Rate": round(eng / impr, 4) if impr else 0,
                        "ThruPlays": thru,
                        "Cost per ThruPlay": round(spend / thru, 4) if thru else 0,
                        "VTR - Thruplays": round(thru / impr, 4) if impr else 0,
                        "Clicks (all)": clicks,
                        "CPC (all)": round(spend / clicks, 4) if clicks else 0,
                        "CTR (all)": round(clicks / impr, 6) if impr else 0,
                        "Video Plays 100%": round(impr * 0.01, 4),
                        "Completed Views": round(thru * 0.3, 2)
                    })

    df = pd.DataFrame(rows)
    return {
        "raw_data": df,
        "campaign_data": df.groupby(["Day", "Campaign name"]).agg({
            c: "sum" for c in ["Amount spent (INR)", "Impressions", "Reach", "Post engagements",
                               "ThruPlays", "Clicks (all)", "Video Plays 100%", "Completed Views"]
        }).reset_index(),
        "adset_data": df.copy(),
        "ad_data": df.copy()
    }


def generate_yt_sample():
    dates = pd.date_range("2026-02-06", "2026-03-05", freq="D")
    campaigns = [
        "SP - Video Views - Soap - Tamil Nadu - Urban - 6th Feb'26",
        "SP - Video Views - Soap - Karnataka - Urban - 6th Feb'26",
        "SP - Video Views - Soap - Telangana - Rural - 6th Feb'26",
        "SP - Video Views - Soap - Maharashtra - Rural - 6th Feb'26",
        "SP - Video Views - Shampoo - Delhi NCR - Urban - 1st Mar'26",
        "SP - Video Views - Shampoo - Mumbai - Urban - 1st Mar'26",
        "SP - Video Views - Shampoo - Bangalore - Rural - 1st Mar'26",
        "SP - Video Views - Shampoo - Kolkata - Rural - 1st Mar'26",
        "SP - Video Views - Facewash - Delhi NCR - Urban - 1st Apr'26",
        "SP - Video Views - Facewash - Pune - Rural - 1st Apr'26",
        "MGD - Video Views - UAE - Urban - 1st Feb'26",
        "MGD - Video Views - KSA - Urban - 1st Feb'26",
        "MGD - Video Views - Singapore - Urban - 1st Feb'26",
        "MGD - Video Views - USA - Urban - 1st Feb'26",
        "MGD - Video Views - Australia - Rural - 1st Feb'26",
        "MGD - Video Views - Malaysia - Rural - 1st Feb'26",
    ]

    rows = []
    for date in dates:
        for campaign in campaigns:
            cost = round(_seed_val(date, campaign, 2000, 3000), 2)
            impr = int(_seed_val(date, campaign, 25000, 25000))
            views = int(impr * 0.55)
            clicks = int(impr * 0.001)

            rows.append({
                "Day": date.strftime("%Y-%m-%d"),
                "Campaign": campaign,
                "Ad group": campaign.split(" - ")[4].strip() if len(campaign.split(" - ")) > 4 else "Default",
                "Ad name": f"{campaign.split(' - ')[2].strip()}_{campaign.split(' - ')[3].strip().split(' ')[0] if len(campaign.split(' - ')) > 3 else 'Default'}",
                "Cost": cost,
                "Impr.": impr,
                "Avg. CPM": round(cost / impr * 1000, 2) if impr else 0,
                "TrueView views": views,
                "TrueView avg. CPV": round(cost / views, 4) if views else 0,
                "Video played to 25%": round(0.80 + 0.1 * (hash(str(date)) % 10) / 10, 4),
                "Video played to 50%": round(0.65 + 0.1 * (hash(str(date)) % 10) / 10, 4),
                "Video played to 75%": round(0.55 + 0.1 * (hash(str(date)) % 10) / 10, 4),
                "Video played to 100%": round(0.50 + 0.1 * (hash(str(date)) % 10) / 10, 4),
                "Clicks": clicks,
                "CTR": round(clicks / impr, 6) if impr else 0,
                "VTR": round(views / impr, 4) if impr else 0,
                "Complete Views": round(views * 0.55, 2)
            })

    df = pd.DataFrame(rows)
    return {
        "raw_data": df,
        "campaign_data": df.groupby(["Day", "Campaign"]).agg({
            c: "sum" for c in ["Cost", "Impr.", "TrueView views", "Clicks", "Complete Views"]
        }).reset_index(),
        "ad_group_data": df.copy(),
        "ad_data": df.copy()
    }
