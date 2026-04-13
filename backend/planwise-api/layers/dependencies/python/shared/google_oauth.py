"""Google OAuth token exchange and Calendar API helpers (requests-only)."""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Optional
from urllib.parse import quote, urlencode

import requests

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


def encode_state(user_id: str) -> str:
    raw = json.dumps({"user_id": user_id}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_state(state: str) -> str:
    if not state:
        raise ValueError("missing state")
    pad = "=" * (-len(state) % 4)
    raw = base64.urlsafe_b64decode(state + pad)
    obj = json.loads(raw.decode("utf-8"))
    uid = obj.get("user_id")
    if not uid or not isinstance(uid, str):
        raise ValueError("invalid state")
    return uid


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": CALENDAR_SCOPE,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH}?{urlencode(params)}"


def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    r = requests.post(GOOGLE_TOKEN, data=data, timeout=15)
    r.raise_for_status()
    return r.json()


def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    r = requests.post(GOOGLE_TOKEN, data=data, timeout=15)
    r.raise_for_status()
    return r.json()


def access_token_expiry_epoch(expires_in: int | None) -> int | None:
    if expires_in is None:
        return None
    return int(time.time()) + int(expires_in)


def list_calendar_events(
    access_token: str,
    calendar_id: str,
    time_min: str,
    time_max: str,
) -> list[dict[str, Any]]:
    base = "https://www.googleapis.com/calendar/v3/calendars"
    cal = quote(calendar_id, safe="")
    url = f"{base}/{cal}/events"
    headers = {"Authorization": f"Bearer {access_token}"}
    items: list[dict[str, Any]] = []
    page_token: Optional[str] = None
    while True:
        params: dict[str, str] = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "2500",
        }
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        batch = body.get("items") or []
        items.extend(batch)
        page_token = body.get("nextPageToken")
        if not page_token:
            break
    return items
