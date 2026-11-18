"""YouTube Data API v3 OAuth authentication manager.

Strictly follows docs/GEMINI.md Section 5 & 6:
- Never log, print, or commit client secrets or refresh tokens.
- Sources credentials from environment variables or local credentials file.
- Uses HTTPS token refresh endpoint without external heavy SDK dependencies.
"""

import json
import os
from pathlib import Path

import httpx


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
