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
