# HBC Campaign Reports — Vercel Deployment Guide

## Quick Deploy (3 steps)

### Step 1: Push to GitHub
```bash
cd hbc-report-automation-vercel
git init
git add .
git commit -m "HBC Report Automation - Vercel"
gh repo create hbc-report-automation --private --push
```

### Step 2: Deploy on Vercel
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repo (`hbc-report-automation`)
3. Framework Preset: **Other**
4. Click **Deploy**

### Step 3: Add API Credentials
1. Go to your project on Vercel Dashboard
2. **Settings → Environment Variables**
3. Add these variables:

| Variable | Description |
|----------|-------------|
| `META_ACCESS_TOKEN` | Your Meta Marketing API token |
| `META_AD_ACCOUNT_ID` | e.g., `act_123456789` |
| `META_APP_ID` | Meta App ID |
| `META_APP_SECRET` | Meta App Secret |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API developer token |
| `GOOGLE_ADS_CLIENT_ID` | OAuth client ID |
| `GOOGLE_ADS_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | OAuth refresh token |
| `GOOGLE_ADS_CUSTOMER_ID` | e.g., `1234567890` |

4. Click **Redeploy** for changes to take effect

## How It Works on Vercel

**Dashboard**: Your app URL (e.g., `hbc-reports.vercel.app`) shows the same dashboard UI.

**On-demand reports**: Click any report button in the dashboard — reports generate in real-time and download immediately.

**Scheduled reports**: Vercel Cron Jobs handle automation:
- **Daily**: Every day at 03:00 UTC (08:30 IST)
- **Weekly**: Every Monday at 03:00 UTC
- **Monthly**: 1st of each month at 03:00 UTC

**Important notes**:
- Reports are stored in `/tmp` (ephemeral) — they persist during warm function invocations but may be cleared. For permanent storage, download reports when generated.
- Brand configuration changes persist during warm invocations but reset on cold starts to the bundled `brands.json`. For permanent brand changes, update `brands.json` in your repo and redeploy.
- API credentials are managed via Vercel Environment Variables, not through the dashboard UI.

## Testing Without API Keys

The app works in **dry-run mode** when API keys aren't configured — it uses realistic sample data to generate reports. This is great for testing the UI and report format.

## Local Development

```bash
cd hbc-report-automation-vercel
pip install -r requirements.txt
python api/index.py
# Opens at http://localhost:5000
```

## Project Structure

```
hbc-report-automation-vercel/
├── api/
│   └── index.py          ← Vercel serverless entry point (Flask app)
├── src/
│   ├── brand_manager.py   ← Brand CRUD + report utilities
│   ├── config.py          ← Environment config loader
│   ├── fetch_meta.py      ← Meta Marketing API client
│   ├── fetch_google.py    ← Google Ads API client
│   ├── report_generator.py ← 12-sheet Excel report builder
│   ├── sample_data.py     ← Sample data for dry runs
│   └── notifier.py        ← Email notifications
├── templates/
│   └── dashboard.html     ← Web dashboard UI
├── brands.json            ← Brand configurations
├── vercel.json            ← Vercel deployment config
├── requirements.txt       ← Python dependencies
└── DEPLOY.md              ← This file
```
