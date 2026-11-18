"""YouTube Data API v3 OAuth authentication manager.

Strictly follows docs/GEMINI.md Section 5 & 6:
- Never log, print, or commit client secrets or refresh tokens.
- Sources credentials from environment variables or local credentials file.
- Uses HTTPS token refresh endpoint without external heavy SDK dependencies.
"""

import base64
import hashlib
import json
import os
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import httpx


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Local HTTP callback listener for receiving the Google OAuth code."""

    server_auth_code: str | None = None
    server_error: str | None = None

    def log_message(self, format: str, *args: Any) -> None:
        """Silence default console access logs."""
        pass

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_url.query)

        if "code" in params:
            OAuthCallbackHandler.server_auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head><title>Authorization Successful</title></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0A0A0A; color: #F2EFE6; text-align: center; padding: 60px;">
  <h2 style="color: #D4AF37;">✓ Authorization Successful</h2>
  <p style="font-size: 16px;">GoldReel has received your YouTube authorization token.</p>
  <p style="color: #A8A294; font-size: 14px;">You can safely close this browser tab and return to your terminal.</p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
        elif "error" in params:
            OAuthCallbackHandler.server_error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            err_msg = OAuthCallbackHandler.server_error
            html = f"""<!DOCTYPE html>
<html>
<head><title>Authorization Failed</title></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0A0A0A; color: #F2EFE6; text-align: center; padding: 60px;">
  <h2 style="color: #E5484D;">✗ Authorization Failed</h2>
  <p style="font-size: 16px;">Error: {err_msg}</p>
  <p style="color: #A8A294; font-size: 14px;">Please return to your terminal.</p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class YouTubeAuth:
    """OAuth 2.0 client credentials and access token manager for YouTube Data API v3."""

    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def __init__(self, credentials_path: Path | str | None = None):
        self.credentials_path = Path(credentials_path or "youtube_credentials.json")
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._refresh_token: str | None = None
        self._access_token: str | None = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load credentials from environment variables or local credentials file."""
        # 1. Environment variables (primary for CI and secure deployments)
        self._client_id = os.environ.get("YOUTUBE_CLIENT_ID")
        self._client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
        self._refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

        # 2. Local credentials file fallback
        if not (self._client_id and self._client_secret and self._refresh_token):
            if self.credentials_path.exists():
                try:
                    with open(self.credentials_path, encoding="utf-8") as f:
                        data = json.load(f)
                    installed = data.get("installed") or data.get("web") or data
                    self._client_id = self._client_id or installed.get("client_id")
                    self._client_secret = self._client_secret or installed.get("client_secret")
                    self._refresh_token = self._refresh_token or installed.get("refresh_token")
                except Exception:
                    pass

    def has_credentials(self) -> bool:
        """Check whether valid OAuth client and refresh token parameters exist."""
        return bool(self._client_id and self._client_secret and self._refresh_token)

    def start_desktop_auth(self, timeout_sec: int = 120, open_browser: bool = True) -> str:
        """Run one-time browser OAuth flow to acquire and save refresh token."""
        if not (self._client_id and self._client_secret):
            raise RuntimeError(
                f"Cannot start OAuth flow: client_id and client_secret not found in {self.credentials_path}"
            )

        OAuthCallbackHandler.server_auth_code = None
        OAuthCallbackHandler.server_error = None

        server = HTTPServer(("127.0.0.1", 0), OAuthCallbackHandler)
        server.timeout = timeout_sec
        port = server.server_port
        redirect_uri = f"http://localhost:{port}"

        # Generate PKCE verifier & challenge
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        state = secrets.token_urlsafe(16)

        scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
        ]

        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

        print(f"\nAuthorization link:\n{auth_url}\n")
        print("Opening in default browser. If you see 'Access blocked', copy the link above into an Incognito / Private window.")

        if open_browser:
            try:
                webbrowser.open(auth_url)
            except Exception:
                pass

        # Handle one callback request
        server.handle_request()
        server.server_close()

        code = OAuthCallbackHandler.server_auth_code
        err = OAuthCallbackHandler.server_error

        if err:
            raise RuntimeError(f"Google OAuth rejected with error: {err}")
        if not code:
            raise TimeoutError(f"OAuth authorization timed out or was cancelled (waited {timeout_sec}s).")

        # Exchange authorization code for tokens
        exchange_payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        with httpx.Client(timeout=20.0) as client:
            res = client.post(self.TOKEN_ENDPOINT, data=exchange_payload)
            if res.status_code != 200:
                raise RuntimeError(f"Token exchange failed (HTTP {res.status_code}): {res.text}")
            token_data = res.json()

        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(f"Google did not return a refresh_token in response: {list(token_data.keys())}")

        # Update in-memory
        self._refresh_token = refresh_token
        self._access_token = token_data.get("access_token")

        # Save to youtube_credentials.json directly
        if self.credentials_path.exists():
            try:
                with open(self.credentials_path, encoding="utf-8") as f:
                    data = json.load(f)
                installed = data.get("installed") or data.get("web") or data
                installed["refresh_token"] = refresh_token
                with open(self.credentials_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

        return refresh_token

    def get_access_token(self) -> str | None:
        """Request a fresh OAuth 2.0 access token using the stored refresh token."""
        if not self.has_credentials():
            return None

        if self._access_token:
            return self._access_token

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(self.TOKEN_ENDPOINT, data=payload)
                if res.status_code == 200:
                    token_data = res.json()
                    self._access_token = token_data.get("access_token")
                    return self._access_token
                return None
        except Exception:
            return None
