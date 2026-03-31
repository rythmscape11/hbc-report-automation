"""
Email Notification Module
Sends email with the generated report attached.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from . import config

logger = logging.getLogger(__name__)


def send_report_email(report_path, status="success", error_msg=None):
    cfg = config.email
    if not cfg.enabled:
        logger.info("Email notifications disabled")
        return

    if not cfg.sender or not cfg.recipients:
        logger.warning("Email not configured properly - skipping")
        return

    msg = MIMEMultipart()
    msg["From"] = cfg.sender
    msg["To"] = ", ".join(cfg.recipients)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    if status == "success":
        msg["Subject"] = f"HBC Campaign Report Ready - {date_str}"
        body = f"""Hi,

Your HBC Soap Campaign report has been generated successfully.

Report: {Path(report_path).name}
Generated at: {date_str}

The report is attached to this email.

---
Automated Report System
"""
        # Attach the report
        if report_path and Path(report_path).exists():
            with open(report_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={Path(report_path).name}")
                msg.attach(part)
    else:
        msg["Subject"] = f"⚠ HBC Campaign Report FAILED - {date_str}"
        body = f"""Hi,

The HBC Soap Campaign report generation failed.

Time: {date_str}
Error: {error_msg or 'Unknown error'}

Please check the logs for details.

---
Automated Report System
"""

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port) as server:
            server.starttls()
            server.login(cfg.sender, cfg.password)
            server.send_message(msg)
        logger.info(f"Email sent to {cfg.recipients}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def send_test_email():
    """Send a test email to verify configuration."""
    cfg = config.email
    if not cfg.enabled:
        print("Email notifications are disabled. Set EMAIL_ENABLED=true in .env")
        return False

    msg = MIMEMultipart()
    msg["From"] = cfg.sender
    msg["To"] = ", ".join(cfg.recipients)
    msg["Subject"] = "HBC Campaign Report - Test Email"
    msg.attach(MIMEText("This is a test email from the HBC Campaign Report Automation system.\n\nIf you're seeing this, email notifications are working correctly!", "plain"))

    try:
        with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port) as server:
            server.starttls()
            server.login(cfg.sender, cfg.password)
            server.send_message(msg)
        print(f"✓ Test email sent to {cfg.recipients}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {e}")
        return False


def send_share_email(recipients, share_url, brand_name, access_level, expiry_days):
    """Send report share notification email."""
    cfg = config.email
    if not cfg.enabled:
        logger.info("Email disabled — share notification not sent")
        return False

    access_labels = {"view": "View Only", "comment": "Comment", "export": "Full Export"}

    msg = MIMEMultipart()
    msg["From"] = cfg.sender
    msg["To"] = ", ".join(recipients) if isinstance(recipients, list) else recipients
    msg["Subject"] = f"AdFlow Studio — Campaign Report Shared ({brand_name})"

    body = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
    <div style="background:#238BC3;padding:24px;text-align:center;">
        <h1 style="color:white;margin:0;font-size:20px;">AdFlow Studio</h1>
    </div>
    <div style="padding:24px;background:#f8f9fa;">
        <h2 style="color:#212529;margin-top:0;">Campaign Report Shared</h2>
        <p>A campaign analytics report for <strong>{brand_name}</strong> has been shared with you.</p>
        <p><strong>Access Level:</strong> {access_labels.get(access_level, access_level)}</p>
        <p><strong>Expires in:</strong> {expiry_days} days</p>
        <div style="text-align:center;margin:24px 0;">
            <a href="{share_url}" style="background:#238BC3;color:white;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600;">View Report</a>
        </div>
        <p style="font-size:12px;color:#6c757d;">Powered by SocialPanga</p>
    </div>
    </body></html>
    """

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port) as server:
            server.starttls()
            server.login(cfg.sender, cfg.password)
            server.send_message(msg)
        logger.info(f"Share email sent to {recipients}")
        return True
    except Exception as e:
        logger.error(f"Share email failed: {e}")
        return False
