"""
Configuration loader - reads from .env file
All settings are customizable via .env
"""

import os
from dotenv import load_dotenv

load_dotenv()


def env(key, default=None, cast=str):
    val = os.getenv(key, default)
    if val is None:
        return None
    if cast == bool:
        return val.lower() in ("true", "1", "yes")
    if cast == int:
        return int(val)
    if cast == float:
        return float(val)
    return val


class MetaConfig:
    access_token = env("META_ACCESS_TOKEN", "")
    ad_account_id = env("META_AD_ACCOUNT_ID", "")
    app_id = env("META_APP_ID", "")
    app_secret = env("META_APP_SECRET", "")
    api_version = env("META_API_VERSION", "v21.0")

    # Campaign settings
    start_date = env("META_START_DATE", "2026-02-27")
    end_date = env("META_END_DATE", "2026-03-27")
    budget = env("META_BUDGET", "500000", cast=float)
    regional_budgets = {
        "Tamil Nadu": env("META_BUDGET_TN", "166667", cast=float),
        "Karnataka": env("META_BUDGET_KA", "166668", cast=float),
        "Telangana": env("META_BUDGET_TS", "0", cast=float),
        "Maharashtra": env("META_BUDGET_MH", "166665", cast=float),
    }
    targets = {
        "amount_spent": env("META_BUDGET", "500000", cast=float),
        "reach": env("META_TARGET_REACH", "7936508", cast=float),
        "impressions": env("META_TARGET_IMPRESSIONS", "48257882", cast=float),
        "engagement": env("META_TARGET_ENGAGEMENT", "2380957", cast=float),
        "thruplay": env("META_TARGET_THRUPLAY", "367003", cast=float),
        "cpm": env("META_TARGET_CPM", "10.36", cast=float),
        "cpr": env("META_TARGET_CPR", "21", cast=float),
        "cpe": env("META_TARGET_CPE", "0.07", cast=float),
        "cpv": env("META_TARGET_CPV", "0.45", cast=float),
        "er": env("META_TARGET_ER", "0.1959", cast=float),
        "vtr": env("META_TARGET_VTR", "0.1005", cast=float),
    }

    @property
    def is_configured(self):
        return bool(self.access_token and self.ad_account_id)


class GoogleConfig:
    developer_token = env("GOOGLE_ADS_DEVELOPER_TOKEN", "")
    client_id = env("GOOGLE_ADS_CLIENT_ID", "")
    client_secret = env("GOOGLE_ADS_CLIENT_SECRET", "")
    refresh_token = env("GOOGLE_ADS_REFRESH_TOKEN", "")
    customer_id = env("GOOGLE_ADS_CUSTOMER_ID", "")
    login_customer_id = env("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")

    # Campaign settings
    start_date = env("YT_START_DATE", "2026-02-06")
    end_date = env("YT_END_DATE", "2026-03-05")
    budget = env("YT_BUDGET", "1000000", cast=float)
    regional_budgets = {
        "Tamil Nadu": env("YT_BUDGET_TN", "153333", cast=float),
        "Karnataka": env("YT_BUDGET_KA", "333333", cast=float),
        "Telangana": env("YT_BUDGET_TS", "313333", cast=float),
        "Maharashtra": env("YT_BUDGET_MH", "200001", cast=float),
    }
    targets = {
        "amount_spent": env("YT_BUDGET", "1000000", cast=float),
        "impressions": env("YT_TARGET_IMPRESSIONS", "19011388", cast=float),
        "views": env("YT_TARGET_VIEWS", "10171092", cast=float),
        "cpv": env("YT_TARGET_CPV", "0.10", cast=float),
        "vtr": env("YT_TARGET_VTR", "0.535", cast=float),
    }

    @property
    def is_configured(self):
        return bool(self.developer_token and self.client_id and self.refresh_token and self.customer_id)


class EmailConfig:
    enabled = env("EMAIL_ENABLED", "false", cast=bool)
    smtp_server = env("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    smtp_port = env("EMAIL_SMTP_PORT", "587", cast=int)
    sender = env("EMAIL_SENDER", "")
    password = env("EMAIL_PASSWORD", "")
    recipients = [r.strip() for r in env("EMAIL_RECIPIENTS", "").split(",") if r.strip()]


class ScheduleConfig:
    time = env("SCHEDULE_TIME", "09:00")
    days = env("SCHEDULE_DAYS", "daily")


class ReportConfig:
    output_dir = env("REPORT_OUTPUT_DIR", "./reports")
    filename_pattern = env("REPORT_FILENAME_PATTERN", "HBC - Soap Campaign Tracker - {date}.xlsx")


# Singletons
meta = MetaConfig()
google = GoogleConfig()
email = EmailConfig()
schedule_cfg = ScheduleConfig()
report = ReportConfig()

REGIONS = ["Tamil Nadu", "Karnataka", "Telangana", "Maharashtra"]
