#!/usr/bin/env python3
"""
SWPPP Inspection Report Web Application
Fauquier County - 9561 Springs Road, Warrenton, VA 20186
"""

import json
import os
import smtplib
import threading
import webbrowser
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

import requests
from flask import Flask, render_template, request, jsonify, send_file

# Load config
CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

app = Flask(__name__)
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def get_weather_data(inspection_date_str: str, last_inspection_date_str: str = None):
    """
    Fetch historical weather data from Open-Meteo API for the inspection site.
    Returns weather conditions at the time of inspection and storm event data.
    """
    lat = CONFIG["project"]["gps_lat"]
    lon = CONFIG["project"]["gps_lon"]

    try:
        inspection_date = datetime.strptime(inspection_date_str, "%Y-%m-%d").date()
    except Exception:
        inspection_date = date.today()

    # Use archive API for past dates (more reliable), forecast API for today/future
    today = date.today()
    if inspection_date <= today:
        url = "https://archive-api.open-meteo.com/v1/archive"
        # Archive API doesn't support hourly for old dates in same call, use daily only
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum,precipitation_hours,weathercode,temperature_2m_max,temperature_2m_min,windspeed_10m_max",
            "temperature_unit": "fahrenheit",
            "windspeed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "America/New_York",
            "start_date": inspection_date_str,
            "end_date": inspection_date_str,
        }
    else:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum,precipitation_hours,weathercode,temperature_2m_max,temperature_2m_min,windspeed_10m_max",
            "hourly": "temperature_2m,precipitation,weathercode,windspeed_10m,cloudcover",
            "temperature_unit": "fahrenheit",
            "windspeed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "America/New_York",
            "start_date": inspection_date_str,
            "end_date": inspection_date_str,
        }

    result = {
        "storm_event": False,
        "storm_start_date": "",
        "storm_start_time": "",
        "storm_duration_hrs": "",
        "storm_precipitation_in": "",
        "weather_condition": "Clear",
        "temperature": "",
        "weather_options": {
            "Clear": False, "Cloudy": False, "Rain": False,
            "Fog": False, "Sleet": False, "Snowing": False, "High Winds": False
        }
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        # Get daily summary
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})

        # Daily precipitation
        daily_precip = 0
        if daily.get("precipitation_sum") and daily["precipitation_sum"]:
            daily_precip = daily["precipitation_sum"][0] or 0

        daily_precip_hours = 0
        if daily.get("precipitation_hours") and daily["precipitation_hours"]:
            daily_precip_hours = daily["precipitation_hours"][0] or 0

        # Max wind speed
        max_wind = 0
        if daily.get("windspeed_10m_max") and daily["windspeed_10m_max"]:
            max_wind = daily["windspeed_10m_max"][0] or 0

        # Max/min temp
        temp_max = None
        temp_min = None
        if daily.get("temperature_2m_max"):
            temp_max = daily["temperature_2m_max"][0]
        if daily.get("temperature_2m_min"):
            temp_min = daily["temperature_2m_min"][0]

        # Weather code for the day
        weather_code = 0
        if daily.get("weathercode"):
            weather_code = daily["weathercode"][0] or 0

        # Determine weather conditions from WMO weather code
        # https://open-meteo.com/en/docs#weathervariables
        if weather_code in range(0, 2):  # Clear
            result["weather_options"]["Clear"] = True
            result["weather_condition"] = "Clear"
        elif weather_code in range(2, 4):  # Partly cloudy / overcast
            result["weather_options"]["Cloudy"] = True
            result["weather_condition"] = "Cloudy"
        elif weather_code in [45, 48]:  # Fog
            result["weather_options"]["Fog"] = True
            result["weather_condition"] = "Fog"
        elif weather_code in list(range(51, 68)) + list(range(80, 83)):  # Rain/drizzle
            result["weather_options"]["Rain"] = True
            result["weather_condition"] = "Rain"
        elif weather_code in list(range(71, 78)) + list(range(85, 87)):  # Snow
            result["weather_options"]["Snowing"] = True
            result["weather_condition"] = "Snowing"
        elif weather_code in list(range(68, 70)):  # Sleet
            result["weather_options"]["Sleet"] = True
            result["weather_condition"] = "Sleet"
        else:
            result["weather_options"]["Clear"] = True

        # High winds check
        if max_wind >= 25:
            result["weather_options"]["High Winds"] = True

        # Temperature
        if temp_max is not None and temp_min is not None:
            avg_temp = round((temp_max + temp_min) / 2)
            result["temperature"] = f"{avg_temp}°F"
        elif temp_max is not None:
            result["temperature"] = f"{round(temp_max)}°F"

        # Storm event detection
        if daily_precip > 0.1:  # More than 0.1 inch = storm event
            result["storm_event"] = True
            result["storm_precipitation_in"] = f"{daily_precip:.2f}"
            result["storm_duration_hrs"] = str(int(daily_precip_hours)) if daily_precip_hours else ""

            # Find storm start time from hourly data
            if hourly.get("precipitation") and hourly.get("time"):
                for i, (t, p) in enumerate(zip(hourly["time"], hourly["precipitation"])):
                    if p and p > 0:
                        storm_dt = datetime.fromisoformat(t)
                        result["storm_start_date"] = storm_dt.strftime("%m/%d/%Y")
                        result["storm_start_time"] = storm_dt.strftime("%I:%M %p")
                        break

    except Exception as e:
        import traceback
        print(f"Weather API error: {e}")
        print(traceback.format_exc())
        result["weather_options"]["Clear"] = True

    # Also check for storm events since last inspection
    if last_inspection_date_str and last_inspection_date_str != inspection_date_str:
        try:
            storm_url = "https://api.open-meteo.com/v1/forecast"
            storm_params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "precipitation_sum,precipitation_hours",
                "precipitation_unit": "inch",
                "timezone": "America/New_York",
                "start_date": last_inspection_date_str,
                "end_date": inspection_date_str,
            }
            storm_resp = requests.get(storm_url, params=storm_params, timeout=10)
            storm_data = storm_resp.json()
            daily_precips = storm_data.get("daily", {}).get("precipitation_sum", [])
            daily_times = storm_data.get("daily", {}).get("time", [])
            daily_hours = storm_data.get("daily", {}).get("precipitation_hours", [])

            for i, (t, p) in enumerate(zip(daily_times, daily_precips)):
                if p and p > 0.1:
                    result["storm_event"] = True
                    if not result["storm_start_date"]:
                        storm_dt = datetime.strptime(t, "%Y-%m-%d")
                        result["storm_start_date"] = storm_dt.strftime("%m/%d/%Y")
                        result["storm_precipitation_in"] = f"{p:.2f}"
                        if daily_hours and i < len(daily_hours):
                            result["storm_duration_hrs"] = str(int(daily_hours[i])) if daily_hours[i] else ""
                    break
        except Exception as e:
            print(f"Storm check error: {e}")

    return result


@app.route("/")
def index():
    """Main inspection form page."""
    today = date.today().strftime("%Y-%m-%d")
    # Calculate last inspection date (4 days ago by default)
    from datetime import timedelta
    last_date = (date.today() - timedelta(days=4)).strftime("%Y-%m-%d")

    weather = get_weather_data(today, last_date)

    return render_template("index.html",
                           config=CONFIG,
                           today=today,
                           last_date=last_date,
                           weather=weather)


@app.route("/api/weather")
def api_weather():
    """API endpoint to fetch weather for a specific date."""
    inspection_date = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    last_date = request.args.get("last_date", "")
    weather = get_weather_data(inspection_date, last_date)
    return jsonify(weather)


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    """Generate the SWPPP inspection report PDF."""
    from pdf_generator import generate_swppp_pdf

    form_data = request.json
    inspection_date = form_data.get("inspection_date", date.today().strftime("%Y-%m-%d"))
    safe_date = inspection_date.replace("-", "")
    filename = f"SWPPP_Inspection_{safe_date}.pdf"
    output_path = REPORTS_DIR / filename

    # Add formatted date display for PDF
    try:
        from datetime import datetime as dt
        form_data["inspection_date_display"] = dt.strptime(inspection_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    except Exception:
        form_data["inspection_date_display"] = inspection_date

    # The frontend sends site_items as a dict keyed by item number.
    # Ensure all keys are strings so pdf_generator lookups work correctly.
    raw_items = form_data.get("site_items", {})
    form_data["site_items"] = {str(k): v for k, v in raw_items.items()}

    # Legacy support: if an "items" array was sent instead, remap it.
    if not form_data["site_items"] and "items" in form_data:
        items_list = form_data.get("items", [])
        site_items = {}
        for idx, item in enumerate(items_list, start=1):
            site_items[str(idx)] = {
                "implemented": item.get("impl", ""),
                "maintenance": item.get("maint", ""),
                "notes": item.get("notes", "")
            }
        form_data["site_items"] = site_items

    # weather_options is sent directly by the frontend as a dict.
    # Legacy support: if weather_conditions list was sent instead, remap it.
    if "weather_options" not in form_data or not form_data["weather_options"]:
        weather_list = form_data.get("weather_conditions", [])
        form_data["weather_options"] = {w: True for w in weather_list}

    # Normalize storm_event to boolean
    storm_raw = form_data.get("storm_event", "no")
    form_data["storm_event"] = (storm_raw == "yes" or storm_raw is True)

    try:
        generate_swppp_pdf(form_data, str(output_path))

        # Upload to Google Drive and send confirmation email in background
        threading.Thread(
            target=post_submit_tasks,
            args=(str(output_path), filename, inspection_date)
        ).start()

        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": f"/download/{filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/download/<filename>")
def download(filename):
    """Download a generated PDF report."""
    file_path = REPORTS_DIR / filename
    if file_path.exists():
        return send_file(str(file_path), as_attachment=True, download_name=filename)
    return "File not found", 404


def post_submit_tasks(file_path: str, filename: str, inspection_date: str):
    """Upload to Google Drive and send confirmation email (runs in background thread)."""
    drive_link = None

    # Upload to Google Drive (with one retry after token refresh)
    for attempt in range(2):
        try:
            from drive_uploader import upload_file_to_drive, is_authorized, refresh_token_now
            if attempt == 1:
                print("Drive upload retry: refreshing token first...")
                refresh_token_now()
            if is_authorized():
                drive_link = upload_file_to_drive(file_path, filename, inspection_date)
                print(f"Uploaded {filename} to Google Drive: {drive_link}")
                break
            else:
                print(f"Google Drive not authorized (attempt {attempt+1}) — {'retrying' if attempt == 0 else 'skipping upload'}")
        except Exception as e:
            print(f"Drive upload error (attempt {attempt+1}): {e}")
            if attempt == 1:
                print("Drive upload failed after retry — giving up.")

    # Send confirmation email
    try:
        from email_notifier import send_report_confirmation
        from datetime import datetime
        date_obj = datetime.strptime(inspection_date, "%Y-%m-%d").date()
        send_report_confirmation(date_obj, filename, drive_link)
    except Exception as e:
        print(f"Confirmation email error: {e}")


@app.route("/oauth/callback")
def oauth_callback():
    """Handle Google OAuth callback."""
    from drive_uploader import handle_oauth_callback
    code = request.args.get("code")
    if code:
        try:
            handle_oauth_callback(code)
            return """
            <html><body style="font-family:sans-serif;text-align:center;padding:50px;">
            <h2 style="color:green;">&#10003; Google Drive Connected!</h2>
            <p>Your reports will now be automatically saved to Google Drive.</p>
            <p><a href="/">Return to Inspection Form</a></p>
            </body></html>
            """
        except Exception as e:
            return f"<html><body><h2>Authorization failed</h2><p>{e}</p></body></html>", 400
    return "Authorization failed", 400


@app.route("/drive/authorize")
def drive_authorize():
    """Initiate Google Drive OAuth authorization."""
    from drive_uploader import get_auth_url
    auth_url, _ = get_auth_url()
    from flask import redirect
    return redirect(auth_url)


@app.route("/drive/status")
def drive_status():
    """Check Google Drive authorization status."""
    from drive_uploader import is_authorized
    return jsonify({"authorized": is_authorized()})


@app.route("/drive/debug")
def drive_debug():
    """Detailed Drive token diagnostics — shows token state and attempts a refresh."""
    import os, json
    info = {}

    # Check env vars
    info["GOOGLE_TOKEN_JSON_set"] = bool(os.environ.get("GOOGLE_TOKEN_JSON"))
    info["TOKEN_JSON_set"] = bool(os.environ.get("TOKEN_JSON"))

    # Check token file
    from pathlib import Path
    token_file = Path(__file__).parent / "token.json"
    info["token_file_exists"] = token_file.exists()

    # Try to load and inspect token
    try:
        from drive_uploader import _load_token_data
        token_data = _load_token_data()
        if token_data:
            info["token_keys"] = list(token_data.keys())
            info["has_refresh_token"] = bool(token_data.get("refresh_token"))
            info["has_access_token"] = bool(token_data.get("token") or token_data.get("access_token"))
            info["token_expiry"] = token_data.get("expiry", token_data.get("token_expiry", "not set"))
        else:
            info["token_data"] = None
    except Exception as e:
        info["token_load_error"] = str(e)

    # Try to get credentials
    try:
        from drive_uploader import _get_credentials
        creds = _get_credentials()
        if creds:
            info["creds_valid"] = creds.valid
            info["creds_expired"] = creds.expired
            info["creds_has_refresh"] = bool(creds.refresh_token)
            info["authorized"] = True
        else:
            info["authorized"] = False
            info["creds"] = None
    except Exception as e:
        info["creds_error"] = str(e)

    return jsonify(info)


def _start_token_refresh_scheduler():
    """Run a background thread that refreshes the Google Drive token every 45 minutes.
    The OAuth access token expires after 1 hour; refreshing every 45 min keeps it alive indefinitely.
    The refresh_token itself never expires as long as it is used at least once every 6 months.
    """
    import time
    def refresh_loop():
        # Refresh immediately on startup so token is valid right away
        try:
            from drive_uploader import refresh_token_now
            success = refresh_token_now()
            if success:
                print("[scheduler] Google Drive token refreshed on startup.")
            else:
                print("[scheduler] Startup token refresh returned False — may need re-authorization.")
        except Exception as e:
            print(f"[scheduler] Startup token refresh error: {e}")
        # Then refresh every 45 minutes to keep it alive
        while True:
            time.sleep(45 * 60)
            try:
                from drive_uploader import refresh_token_now
                success = refresh_token_now()
                if success:
                    print("[scheduler] Google Drive token refreshed successfully.")
                else:
                    print("[scheduler] Token refresh returned False — may need re-authorization.")
            except Exception as e:
                print(f"[scheduler] Token refresh error: {e}")

    t = threading.Thread(target=refresh_loop, daemon=True)
    t.start()
    print("[scheduler] Google Drive token refresh scheduler started (startup + every 45 min).")


# Start the token refresh scheduler when the app loads (works with gunicorn too)
_start_token_refresh_scheduler()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SWPPP Inspection Report System")
    print("  9561 Springs Road, Warrenton, VA 20186")
    print("="*60)
    print(f"\n  Open your browser to: http://localhost:7861")
    print("  Press Ctrl+C to stop\n")
    port = int(os.environ.get("PORT", 7861))
    app.run(host="0.0.0.0", port=port, debug=False)
