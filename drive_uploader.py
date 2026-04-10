"""
Google Drive Uploader for SWPPP Inspection Reports
Uses OAuth2 with automatic token refresh. The refresh_token never expires,
so as long as the app refreshes the access token before it expires (every hour),
Drive uploads work indefinitely without manual re-authorization.
"""

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

TOKEN_FILE = Path(__file__).parent / "token.json"
FOLDER_ID = CONFIG["google_drive"].get("folder_id", "1pu9pVgsSA159NHxkMyAlpZAxfDmIPuD2")
FOLDER_NAME = CONFIG["google_drive"]["folder_name"]

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# In-memory cache of credentials so we don't reload from disk every time
_cached_creds = None


def _load_token_data():
    """Load token JSON from env var (Render) or local file."""
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        try:
            return json.loads(token_json)
        except Exception as e:
            print(f"Failed to parse GOOGLE_TOKEN_JSON env var: {e}")

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            return json.load(f)

    return None


def _save_token(creds):
    """Save refreshed token to local file and update in-memory env var."""
    token_data = json.loads(creds.to_json())
    compact = json.dumps(token_data, separators=(',', ':'))

    # Save to local file
    with open(TOKEN_FILE, "w") as f:
        f.write(compact)

    # Update in-memory env var so subsequent calls in same process use fresh token
    os.environ["GOOGLE_TOKEN_JSON"] = compact
    print("Google Drive token refreshed and saved.")


def _get_credentials():
    """Load and auto-refresh OAuth2 credentials. Uses in-memory cache."""
    global _cached_creds

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    # Try to use cached credentials first
    if _cached_creds and _cached_creds.valid:
        return _cached_creds

    # Load from storage
    token_data = _load_token_data()
    if not token_data:
        print("No Google Drive token found.")
        return None

    try:
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
        elif not creds or not creds.valid:
            print("Google Drive credentials invalid and cannot be refreshed.")
            return None

        _cached_creds = creds
        return creds

    except Exception as e:
        print(f"Google Drive credential error: {e}")
        return None


def refresh_token_now():
    """Force a token refresh. Called by the keep-alive scheduler."""
    global _cached_creds
    _cached_creds = None  # Clear cache to force reload

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_data = _load_token_data()
    if not token_data:
        print("Token refresh failed: no token data found.")
        return False

    try:
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
            _cached_creds = creds
            print("Token proactively refreshed successfully.")
            return True
        else:
            print("No refresh_token available.")
            return False
    except Exception as e:
        print(f"Proactive token refresh failed: {e}")
        return False


def is_authorized():
    """Check if Google Drive is authorized."""
    return _get_credentials() is not None


def upload_file_to_drive(file_path: str, filename: str, inspection_date: str) -> str:
    """Upload a PDF file to the user's Google Drive folder and return the shareable link."""
    creds = _get_credentials()
    if not creds:
        raise RuntimeError("Google Drive not authorized. Token missing or expired.")

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    service = build("drive", "v3", credentials=creds)

    # Check if a file with this name already exists in the folder and delete it
    query = f"name='{filename}' and '{FOLDER_ID}' in parents and trashed=false"
    existing = service.files().list(q=query, fields="files(id)").execute().get("files", [])
    for f in existing:
        service.files().delete(fileId=f["id"]).execute()

    # Upload the file into the user's shared folder
    file_metadata = {
        "name": filename,
        "parents": [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype="application/pdf", resumable=True)
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    # Make the file readable by anyone with the link
    service.permissions().create(
        fileId=uploaded["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    link = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{uploaded['id']}/view")
    print(f"Uploaded {filename} to Google Drive: {link}")
    return link
