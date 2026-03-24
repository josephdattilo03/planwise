import json
import os
import time
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

import requests
from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2
from shared.google_oauth import (
    access_token_expiry_epoch,
    list_calendar_events,
    refresh_access_token,
)
from shared.models.event import Event
from shared.models.user import User
from shared.services.event_service import EventService
from shared.services.user_service import UserService
from shared.utils.errors import (
    BadRequestError,
    GoogleCalendarAuthError,
    GoogleOAuthConfigurationError,
    NotFoundError,
    ValidationAppError,
)
from shared.utils.lambda_error_wrapper import lambda_http_handler

DEFAULT_GOOGLE_COLOR = "#4285F4"


def _google_board_id_for_user(user_id: str) -> str:
    return f"gcal:{user_id}"


def _google_event_id(ge: dict[str, Any]) -> str:
    gid = ge.get("id") or uuid4().hex
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(gid))[:180]
    return f"gcal-{safe}"


def _parse_google_times(ge: dict[str, Any]) -> tuple[date, date, bool]:
    start = ge.get("start") or {}
    end = ge.get("end") or {}
    if "date" in start:
        sd = date.fromisoformat(start["date"])
        ed_ex = date.fromisoformat(end["date"])
        ed = ed_ex - timedelta(days=1)
        if ed < sd:
            ed = sd
        return sd, ed, True
    st = start.get("dateTime")
    et = end.get("dateTime")
    if not st or not et:
        raise ValueError("missing start/end time")
    sdt = datetime.fromisoformat(st.replace("Z", "+00:00"))
    edt = datetime.fromisoformat(et.replace("Z", "+00:00"))
    return sdt.date(), edt.date(), False


def _google_to_event(ge: dict[str, Any], board_id: str) -> Event:
    event_id = _google_event_id(ge)
    start_d, end_d, all_day = _parse_google_times(ge)
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    summary = ge.get("summary") or "(no title)"
    desc = ge.get("description") or ""
    location = ge.get("location") or ""
    body = f"{summary}\n{desc}".strip() if desc else summary
    return Event(
        id=event_id,
        board_id=board_id,
        start_time=start_d,
        end_time=end_d,
        event_color=DEFAULT_GOOGLE_COLOR,
        is_all_day=all_day,
        description=body[:2000],
        location=location[:500],
        recurrence=None,
    )


def _ensure_user(user_service: UserService, user_id: str) -> User:
    try:
        return user_service.get_user_by_id(user_id)
    except NotFoundError:
        label = user_id.split("@")[0] if "@" in user_id else user_id
        u = User(
            id=user_id,
            name=label,
            timezone="UTC",
            created_at=date.today(),
        )
        return user_service.create_user(u)


def _apply_tokens_from_body(user: User, body: dict[str, Any]) -> None:
    at = body.get("access_token")
    if at:
        user.google_access_token = at
    rt = body.get("refresh_token")
    if rt:
        user.google_refresh_token = rt
    exp = body.get("access_token_expires_at")
    if exp is not None:
        user.google_token_expiry = int(exp)


def _ensure_access_token(
    user: Any,
    client_id: str,
    client_secret: str,
    user_service: UserService,
) -> Any:
    now = int(time.time())
    exp = user.google_token_expiry or 0
    if user.google_access_token and exp > now + 90:
        return user
    if not user.google_refresh_token:
        raise GoogleCalendarAuthError()
    try:
        payload = refresh_access_token(
            user.google_refresh_token, client_id, client_secret
        )
    except requests.HTTPError:
        raise GoogleCalendarAuthError()
    access = payload.get("access_token")
    if not access:
        raise GoogleCalendarAuthError()
    user.google_access_token = access
    user.google_token_expiry = access_token_expiry_epoch(payload.get("expires_in"))
    if payload.get("refresh_token"):
        user.google_refresh_token = payload["refresh_token"]
    user_service.update_user(user)
    return user


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise GoogleOAuthConfigurationError()

    path = event.get("pathParameters") or {}
    user_id = path.get("user_id")
    if not user_id:
        raise BadRequestError()
    board_id = _google_board_id_for_user(user_id)

    qs = event.get("queryStringParameters") or {}
    calendar_id = qs.get("calendar_id")
    time_min = qs.get("time_min")
    time_max = qs.get("time_max")
    if not calendar_id or not time_min or not time_max:
        raise ValidationAppError(
            [
                {
                    "loc": ["query"],
                    "msg": "calendar_id, time_min, and time_max are required",
                }
            ]
        )

    insert_only = (qs.get("insert_only") or "").lower() in ("1", "true", "yes")

    body: dict[str, Any] = {}
    raw_body = event.get("body")
    if raw_body:
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = {}

    user_service = UserService()
    event_service = EventService()

    user = _ensure_user(user_service, user_id)
    if body.get("access_token"):
        _apply_tokens_from_body(user, body)
        user_service.update_user(user)
        user = user_service.get_user_by_id(user_id)

    user = _ensure_access_token(user, client_id, client_secret, user_service)

    if not user.google_access_token:
        raise GoogleCalendarAuthError()

    try:
        raw_events = list_calendar_events(
            user.google_access_token,
            calendar_id,
            time_min,
            time_max,
        )
    except requests.HTTPError:
        raise GoogleCalendarAuthError()
    except requests.RequestException as e:
        return {
            "statusCode": 502,
            "body": json.dumps(
                {"error": f"Google Calendar request failed: {str(e)}"}
            ),
        }

    existing_ids = event_service.get_google_calendar_event_ids(board_id)

    to_write: list[Event] = []
    errors: list[dict[str, Any]] = []
    out_events: list[dict[str, Any]] = []

    for ge in raw_events:
        if ge.get("status") == "cancelled":
            continue
        try:
            ev = _google_to_event(ge, board_id)
        except (ValueError, TypeError) as exc:
            errors.append(
                {"event_id": ge.get("id"), "error": str(exc) or "parse error"}
            )
            continue

        if insert_only and ev.id in existing_ids:
            continue
        to_write.append(ev)

    imported = 0
    updated = 0
    if insert_only:
        imported = len(to_write)
        event_service.create_events_batch(to_write)
        for ev in to_write:
            ge = next(
                (g for g in raw_events if _google_event_id(g) == ev.id),
                None,
            )
            title = (
                (ge or {}).get("summary") or "(no title)"
            )
            out_events.append(
                {
                    "id": ev.id,
                    "title": title,
                    "start": ev.start_time.isoformat(),
                    "end": ev.end_time.isoformat(),
                    "color": DEFAULT_GOOGLE_COLOR,
                    "allDay": ev.is_all_day,
                }
            )
    else:
        for ev in to_write:
            if ev.id in existing_ids:
                updated += 1
            else:
                imported += 1
        event_service.create_events_batch(to_write)
        for ev in to_write:
            ge = next(
                (g for g in raw_events if _google_event_id(g) == ev.id),
                None,
            )
            title = (ge or {}).get("summary") or "(no title)"
            out_events.append(
                {
                    "id": ev.id,
                    "title": title,
                    "start": ev.start_time.isoformat(),
                    "end": ev.end_time.isoformat(),
                    "color": DEFAULT_GOOGLE_COLOR,
                    "allDay": ev.is_all_day,
                }
            )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Import completed",
                "imported_count": imported,
                "updated_count": updated,
                "total_google_events": len(raw_events),
                "events": out_events[:200],
                "errors": errors[:50] if errors else [],
                "insert_only": insert_only,
            }
        ),
    }
