"""
SWPPP Inspection Reminder Script
Runs on the Manus scheduled task every Monday and Thursday at 8 AM Eastern.
Always sends the permanent Render URL — no sandbox URL, no expose needed.
"""

import sys
import os
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Permanent Render URL — never changes
FORM_URL = "https://swppp-inspection-app.onrender.com"


def main():
    print(f"\n{'='*50}")
    print(f"SWPPP Reminder Script — {date.today().strftime('%A, %B %d, %Y')}")
    print(f"{'='*50}")
    print(f"Form URL: {FORM_URL}")

    sys.path.insert(0, str(SCRIPT_DIR))
    from email_notifier import send_inspection_reminder
    today = date.today()
    success = send_inspection_reminder(today, FORM_URL)

    if success:
        print(f"Reminder email sent successfully for {today}")
    else:
        print("ERROR: Failed to send reminder email")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
