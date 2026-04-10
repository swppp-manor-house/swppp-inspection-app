"""Email Notifier for SWPPP Inspection Reminders
Uses Gmail SMTP (port 465 SSL) to send inspection reminders and confirmations.
""""

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime, date, timedelta

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

# Gmail SMTP works on Render free tier (port 465 SSL)
GMAIL_USER = os.environ.get("GMAIL_USER") or CONFIG["email"].get("gmail_user", "lbartee@vt.edu")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD") or CONFIG["email"].get("gmail_app_password", "")
NOTIFY_EMAIL = CONFIG["email"]["notify_email"]
CC_EMAILS = CONFIG["email"].get("cc_emails", [])
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL port, works on Render free tier


def send_inspection_reminder(inspection_date: date, form_url: str):
    """Send an email reminder that an inspection report is due."""
    date_str = inspection_date.strftime("%A, %B %d, %Y")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SWPPP Inspection Due — {date_str}"
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL

    text_body = f"""
SWPPP Inspection Reminder
==========================

Your SWPPP inspection report is due today: {date_str}

Project: {CONFIG['project']['location']}
Inspector: {CONFIG['project']['inspector_name']}
Schedule: {CONFIG['project']['inspection_schedule']}

Click the link below to open the inspection form:
{form_url}

This is an automated reminder from your SWPPP Inspection Workflow.
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
    .container {{ background: white; border-radius: 8px; padding: 30px; max-width: 600px; margin: 0 auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .header {{ background: #1a5276; color: white; padding: 20px; border-radius: 6px 6px 0 0; margin: -30px -30px 20px -30px; }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .header p {{ margin: 5px 0 0; opacity: 0.85; font-size: 14px; }}
    .info-box {{ background: #eaf4fb; border-left: 4px solid #1a5276; padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0; }}
    .info-box p {{ margin: 5px 0; font-size: 14px; }}
    .btn {{ display: inline-block; background: #1a5276; color: white; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-size: 16px; font-weight: bold; margin: 20px 0; }}
    .footer {{ font-size: 12px; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>SWPPP Inspection Due</h1>
      <p>{date_str}</p>
    </div>
    <p>Your SWPPP inspection report is due today. Please complete the inspection and submit the report.</p>
    <div class="info-box">
      <p><strong>Project:</strong> {CONFIG['project']['location']}</p>
      <p><strong>Inspector:</strong> {CONFIG['project']['inspector_name']}</p>
      <p><strong>Contact:</strong> {CONFIG['project']['inspector_contact']}</p>
      <p><strong>Schedule:</strong> {CONFIG['project']['inspection_schedule']}</p>
    </div>
    <p>Click the button below to open the inspection form. Weather data will be automatically populated for today's date.</p>
    <a href="{form_url}" class="btn">Open Inspection Form →</a>
    <div class="footer">
      <p>This is an automated reminder from your SWPPP Inspection Workflow.</p>
      <p>Next inspection will be due in 4 days: {(inspection_date + timedelta(days=4)).strftime('%B %d, %Y')}</p>
    </div>
  </div>
</body>
</html>
"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
        print(f"Reminder email sent to {NOTIFY_EMAIL}")
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def send_report_confirmation(inspection_date: date, filename: str, drive_link: str = None):
    """Send a confirmation email after a report is submitted."""
    date_str = inspection_date.strftime("%B %d, %Y")
    next_date = (inspection_date + timedelta(days=4)).strftime("%B %d, %Y")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SWPPP Report Submitted — {date_str}"
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    if CC_EMAILS:
        msg["Cc"] = ", ".join(CC_EMAILS)

    drive_section = ""
    if drive_link:
        drive_section = f'<p><strong>Google Drive:</strong> <a href="{drive_link}">View in Drive</a></p>'

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
    .container {{ background: white; border-radius: 8px; padding: 30px; max-width: 600px; margin: 0 auto; }}
    .header {{ background: #1e8449; color: white; padding: 20px; border-radius: 6px 6px 0 0; margin: -30px -30px 20px -30px; }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .info-box {{ background: #eafaf1; border-left: 4px solid #1e8449; padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0; }}
    .footer {{ font-size: 12px; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✅ Inspection Report Submitted</h1>
    </div>
    <p>Your SWPPP inspection report has been successfully generated and saved.</p>
    <div class="info-box">
      <p><strong>Inspection Date:</strong> {date_str}</p>
      <p><strong>Report File:</strong> {filename}</p>
      {drive_section}
    </div>
    <div class="footer">
      <p>Next inspection due: <strong>{next_date}</strong></p>
    </div>
  </div>
</body>
</html>
"""

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            all_recipients = [NOTIFY_EMAIL] + CC_EMAILS
            server.sendmail(GMAIL_USER, all_recipients, msg.as_string())
        print(f"Confirmation email sent to {NOTIFY_EMAIL}" + (f" (CC: {', '.join(CC_EMAILS)})" if CC_EMAILS else ""))
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


if __name__ == "__main__":
    # Test the email
    print("Sending test reminder email...")
    send_inspection_reminder(date.today(), "https://swppp-inspection-app.onrender.com")
    print("Done!")
