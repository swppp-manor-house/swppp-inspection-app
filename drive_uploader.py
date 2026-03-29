"""
Google Drive Uploader for SWPPP Inspection Reports
Uses OAuth2 token (with auto-refresh) to upload PDF reports to the user's Google Drive folder.
Token is stored in token.json (or GOOGLE_TOKEN_JSON env var on Render) and refreshes automatically.
"""

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
FOLDER_ID = CONFIG["google_drive"].get("folder_id", "1pu9pVgsSA159NHxkMyAlpZAxfDmIPuD2")
FOLDER_NAME = CONFIG["google_drive"]["folder_name"]

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _ensure_token_file():
    """If token.json doesn't exist but GOOGLE_TOKEN_JSON env var is set, write it."""
    if not TOKEN_FILE.exists():
        token_json = os.environ.get("GOOGLE_TOKEN_JSON")
        if token_json:
            with open(TOKEN_FILE, "w") as f:
                f.write(token_json)
            print("Google Drive token loaded from environment variable.")


def _ensure_credentials_file():
    """If credentials.json doesn't exist but GOOGLE_CREDENTIALS_JSON env var is set, write it."""
    if not CREDENTIALS_FILE.exists():
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            with open(CREDENTIALS_FILE, "w") as f:
                f.write(creds_json)
            print("Google credentials loaded from environment variable.")


def _get_credentials():
    """Load and auto-refresh OAuth2 credentials from token.json."""
    _ensure_token_file()
    if not TOKEN_FILE.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            print("Google Drive token refreshed successfully.")
            return creds
    except Exception as e:
        print(f"Credential load/refresh error: {e}")
    return None


def is_authorized():
    """Check if Google Drive is authorized."""
    return _get_credentials() is not None


def get_auth_url():
    """Generate OAuth2 authorization URL (for re-authorization if needed)."""
    _ensure_credentials_file()
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"credentials.json not found")
    from google_auth_oauthlib.flow import Flow
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI",
        "https://7861-i0wo5nb4yh6gb17w4aizq-744f7aaf.us1.manus.computer/oauth/callback")
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return auth_url, state


def handle_oauth_callback(code: str):
    """Exchange auth code for token and save it."""
    _ensure_credentials_file()
    from google_auth_oauthlib.flow import Flow
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI",
        "https://7861-i0wo5nb4yh6gb17w4aizq-744f7aaf.us1.manus.computer/oauth/callback")
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"Google Drive token saved to {TOKEN_FILE}")


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

    return uploaded.get("webViewLink", f"https://drive.google.com/file/d/{uploaded['id']}/view")
