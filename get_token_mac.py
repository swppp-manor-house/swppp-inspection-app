"""
Run this script on your Mac to authorize Google Drive access.
It will open a browser tab, you sign in and click Allow,
then it prints the token JSON for you to paste back into Manus.

Requirements (install if needed):
  pip3 install google-auth-oauthlib google-auth-httplib2

Usage:
  python3 get_token_mac.py
"""

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

CLIENT_ID = "902973773881-1nneqbaagoihg2bsu5i783ic5034ef71.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h2 style='color:green;'>&#10003; Authorization successful!</h2>
                <p>You can close this tab and return to Manus.</p>
                </body></html>
            """)
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed")

    def log_message(self, format, *args):
        pass  # Suppress server logs


def main():
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    print("\n" + "="*60)
    print("Opening browser for Google authorization...")
    print("="*60)
    print("\nIf the browser doesn't open, visit this URL manually:")
    print(auth_url)
    print()

    webbrowser.open(auth_url)

    # Start local server to catch the callback
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.timeout = 120  # 2 minute timeout

    print("Waiting for authorization (use Touch ID when prompted)...")
    server.handle_request()

    if not auth_code:
        print("ERROR: No authorization code received.")
        return

    # Exchange code for token
    flow.fetch_token(code=auth_code)
    creds = flow.credentials

    token_data = json.loads(creds.to_json())
    print("\n" + "="*60)
    print("SUCCESS! Copy everything between the lines below")
    print("and paste it into Manus:")
    print("="*60)
    print(json.dumps(token_data, indent=2))
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
