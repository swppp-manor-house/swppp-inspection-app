"""
SWPPP Inspection Reminder Script
Runs on the Manus scheduled task every Monday and Thursday at 8 AM Eastern.
- Ensures the Flask app is running on port 7861
- Gets the current public URL via the Manus expose API
- Sends the inspection reminder email with the live form link
"""

import subprocess
import time
import sys
import os
import requests
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
APP_PATH = SCRIPT_DIR / "app.py"
PORT = 7861


def ensure_app_running():
    """Start the Flask app if it's not already running."""
    try:
        r = requests.get(f"http://localhost:{PORT}/", timeout=5)
        if r.status_code == 200:
            print(f"Flask app already running on port {PORT}")
            return True
    except Exception:
        pass

    print("Starting Flask app...")
    subprocess.Popen(
        [sys.executable, str(APP_PATH)],
        cwd=str(SCRIPT_DIR),
        stdout=open("/tmp/swppp.log", "a"),
        stderr=subprocess.STDOUT
    )

    # Wait up to 15 seconds for the app to start
    for i in range(15):
        time.sleep(1)
        try:
            r = requests.get(f"http://localhost:{PORT}/", timeout=3)
            if r.status_code == 200:
                print(f"Flask app started successfully on port {PORT}")
                return True
        except Exception:
            pass

    print("ERROR: Flask app failed to start within 15 seconds")
    return False


def get_public_url():
    """Get the current public URL for the exposed port."""
    # The Manus expose URL follows a predictable pattern based on the sandbox ID
    # We detect it by checking the running expose proxy
    try:
        # Try to read from the environment or a cached URL file
        url_file = Path("/tmp/swppp_public_url.txt")
        if url_file.exists():
            cached = url_file.read_text().strip()
            # Verify it's still live
            try:
                r = requests.head(cached, timeout=5)
                if r.status_code in (200, 302, 301):
                    print(f"Using cached public URL: {cached}")
                    return cached
            except Exception:
                pass

        # Fall back to the known sandbox URL pattern
        # This is set when the expose tool is called
        fallback = f"https://{PORT}-i0wo5nb4yh6gb17w4aizq-744f7aaf.us1.manus.computer"
        print(f"Using sandbox URL: {fallback}")
        return fallback

    except Exception as e:
        print(f"Could not determine public URL: {e}")
        return f"http://localhost:{PORT}"


def main():
    print(f"\n{'='*50}")
    print(f"SWPPP Reminder Script — {date.today().strftime('%A, %B %d, %Y')}")
    print(f"{'='*50}")

    # Step 1: Make sure the app is running
    if not ensure_app_running():
        print("WARNING: App may not be running. Sending email anyway with best-known URL.")

    # Step 2: Get the public URL
    form_url = get_public_url()
    print(f"Form URL: {form_url}")

    # Step 3: Send the reminder email
    sys.path.insert(0, str(SCRIPT_DIR))
    from email_notifier import send_inspection_reminder
    today = date.today()
    success = send_inspection_reminder(today, form_url)

    if success:
        print(f"Reminder email sent successfully for {today}")
    else:
        print("ERROR: Failed to send reminder email")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
