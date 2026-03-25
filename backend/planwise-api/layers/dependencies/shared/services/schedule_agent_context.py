"""Builds schedule context (boards, events, tasks) for the schedule agent."""
from datetime import date, datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from shared.models.board import Board
from shared.models.event import Event
from shared.models.note import Note
from shared.models.task import Task
from shared.services.board_service import BoardService
from shared.services.event_service import EventService
from shared.services.folder_service import FolderService
from shared.services.note_service import NoteService
from shared.services.task_service import TaskService


def _parse_user_local_date(s: Optional[str]) -> Optional[date]:
    if not s or not isinstance(s, str):
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


def resolve_calendar_today(
    user_timezone: Optional[str] = None,
    user_local_date: Optional[str] = None,
) -> tuple[date, str, str]:
    """
    Returns (today_date, timezone_label, source).
    Prefer explicit user_local_date from the client, then IANA timezone, else UTC.
    """
    parsed = _parse_user_local_date(user_local_date)
    if parsed is not None:
        return parsed, "client", "user_local_date"

    if user_timezone and isinstance(user_timezone, str):
        tz_name = user_timezone.strip()
        if tz_name:
            try:
                z = ZoneInfo(tz_name)
                today = datetime.now(z).date()
                return today, tz_name, "iana_timezone"
            except Exception:
                pass

    today = datetime.now(timezone.utc).date()
    return today, "UTC", "utc_fallback"


def build_schedule_context(
    user_id: str,
    board_ids: Optional[list[str]] = None,
    *,
    user_timezone: Optional[str] = None,
    user_local_date: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build a JSON-serializable schedule context for the given user.
    If board_ids is provided, only include those boards; otherwise all boards for the user.
    """
    board_svc = BoardService()
    event_svc = EventService()
    task_svc = TaskService()
    folder_svc = FolderService()
    folder_svc.ensure_root_folder(user_id)
    folder_rows = [f for f in (folder_svc.get_boards_by_user_id(user_id) or []) if f is not None]
    folders_out: list[dict[str, Any]] = []
    for f in folder_rows:
        folders_out.append(
            {"id": f.id, "name": f.name, "path": f.path, "depth": f.depth}
        )
    folders_out.sort(key=lambda x: (int(x.get("depth") or 0), str(x.get("name") or "")))

    boards: list[Board] = board_svc.get_boards_by_user_id(user_id) or []
    if board_ids is not None:
        boards = [b for b in boards if b.id in board_ids]

    result: list[dict[str, Any]] = []
    for board in boards:
        events: list[Event] = event_svc.get_event_by_board(board.id) or []
        tasks: list[Task] = task_svc.get_tasks_by_board(board.id)

        board_data: dict[str, Any] = {
            "id": board.id,
            "name": board.name,
            "path": board.path,
            "depth": board.depth,
            "color": board.color,
            "events": [_event_to_context(e) for e in events],
            "tasks": [_task_to_context(t) for t in tasks],
        }
        result.append(board_data)

    note_svc = NoteService()
    notes_raw = note_svc.get_notes_by_user_id(user_id)
    notes_out = [_note_to_context(n) for n in notes_raw]

    today_d, tz_label, tz_source = resolve_calendar_today(user_timezone, user_local_date)
    utc_now = datetime.now(timezone.utc)

    return {
        "today": today_d.isoformat(),
        "calendar": {
            "today": today_d.isoformat(),
            "timezone": tz_label,
            "resolved_from": tz_source,
            "utc_now_iso": utc_now.isoformat(),
        },
        "folders": folders_out,
        "boards": result,
        "notes": notes_out,
    }


def _event_to_context(e: Event) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": e.id,
        "board_id": e.board_id,
        "start_time": e.start_time.isoformat() if hasattr(e.start_time, "isoformat") else str(e.start_time),
        "end_time": e.end_time.isoformat() if hasattr(e.end_time, "isoformat") else str(e.end_time),
        "event_color": e.event_color,
        "is_all_day": e.is_all_day,
        "description": e.description,
        "location": e.location,
    }
    if e.recurrence is not None:
        out["recurrence"] = e.recurrence.model_dump(mode="json")
    else:
        out["recurrence"] = None
    return out


def _note_to_context(n: Note) -> dict[str, Any]:
    body = n.body or ""
    if len(body) > 4000:
        body = body[:4000] + "… [truncated]"
    return {
        "id": n.id,
        "title": n.title,
        "body": body,
        "color": n.color,
        "archived": n.archived,
        "board_id": n.board_id,
        "updated_at": n.updated_at,
    }


def _task_to_context(t: Task) -> dict[str, Any]:
    return {
        "id": t.id,
        "board_id": t.board_id,
        "name": t.name,
        "description": t.description,
        "progress": t.progress,
        "priority_level": t.priority_level,
        "due_date": t.due_date.isoformat() if hasattr(t.due_date, "isoformat") else str(t.due_date),
        "tag_ids": t.tag_ids,
    }
