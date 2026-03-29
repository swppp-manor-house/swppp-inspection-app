"""
Startup script for Railway deployment.
Writes JSON credential files from environment variables before the app starts.
"""
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

def write_env_json(env_var: str, file_path: Path):
    """Write a JSON environment variable to a file."""
    value = os.environ.get(env_var)
    if value:
        try:
            # Validate it's valid JSON
            json.loads(value)
            file_path.write_text(value)
            print(f"[startup] Wrote {file_path.name} from env var {env_var}")
        except json.JSONDecodeError as e:
            print(f"[startup] ERROR: {env_var} is not valid JSON: {e}")
    else:
        if file_path.exists():
            print(f"[startup] {file_path.name} already exists on disk, skipping")
        else:
            print(f"[startup] WARNING: {env_var} not set and {file_path.name} not found")

# Write all credential files from environment variables
write_env_json("CONFIG_JSON", BASE_DIR / "config.json")
write_env_json("TOKEN_JSON", BASE_DIR / "token.json")
write_env_json("CREDENTIALS_JSON", BASE_DIR / "credentials.json")

# Ensure reports directory exists
(BASE_DIR / "reports").mkdir(exist_ok=True)

print("[startup] Startup complete")
