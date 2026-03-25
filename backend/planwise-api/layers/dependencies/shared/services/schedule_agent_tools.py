"""OpenAI tool definitions and executor for the schedule agent."""
import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import ValidationError

from shared.models.board import Board
from shared.models.event import Event, Recurrence
from shared.models.folder import Folder
from shared.models.note import Note
from shared.models.task import Task
from shared.services.board_service import BoardService
from shared.services.event_service import EventService
from shared.services.folder_service import FolderService
from shared.services.note_service import NoteService
from shared.services.task_service import TaskService
from shared.services.canvas_assignments_service import fetch_canvas_snapshot
from shared.utils.errors import InvalidEventTimeError, NotFoundError

DEFAULT_BOARD_COLOR = "#4a7c59"
DEFAULT_EVENT_COLOR = "#3b82f6"
_HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")


class PlanPreviewRegistry:
    """In-memory fld_*/bd_* from plan-only previews (not in DynamoDB yet)."""

    __slots__ = ("folders", "boards")

    def __init__(self) -> None:
        self.folders: dict[str, Folder] = {}
        self.boards: dict[str, Board] = {}


def _get_folder_for_parent(
    folder_id: str, user_id: str, preview: Optional[PlanPreviewRegistry] = None
) -> Optional[Folder]:
    fs = FolderService()
    fs.ensure_root_folder(user_id)
    parent = fs.get_folder_by_id(folder_id, user_id)
    if parent is not None:
        return parent
    if preview is not None and folder_id in preview.folders:
        return preview.folders[folder_id]
    return None


def _resolve_folder_id(
    raw: Any, user_id: str, preview: Optional[PlanPreviewRegistry] = None
) -> str:
    if raw is None:
        raise ValueError("parent_folder_id is required (use get_folders: 'root' or a folder id)")
    s = str(raw).strip()
    if not s:
        raise ValueError("parent_folder_id is required")
    if s.lower() == "root":
        return "root"
    fs = FolderService()
    fs.ensure_root_folder(user_id)
    rows = fs.get_boards_by_user_id(user_id) or []
    for f in rows:
        if f is None:
            continue
        if f.id == s:
            return f.id
        if (getattr(f, "name", None) or "").strip().lower() == s.lower():
            return f.id
    if preview is not None and s in preview.folders:
        return s
    raise ValueError(
        f'Unknown folder "{s}". If this folder is new, call create_folder first under '
        "`root` (or an existing parent), then create_board using that folder's `id` from "
        "the tool result or get_folders. Otherwise use `id` or the exact name from get_folders."
    )


def _resolve_board_id(
    raw: Any, user_id: str, preview: Optional[PlanPreviewRegistry] = None
) -> str:
    if raw is None:
        raise ValueError("board_id is required (use get_boards for ids)")
    s = str(raw).strip()
    if not s:
        raise ValueError("board_id is required")
    svc = BoardService()
    boards = svc.get_boards_by_user_id(user_id) or []
    for b in boards:
        if b.id == s:
            return b.id
        if (b.name or "").strip().lower() == s.lower():
            return b.id
    if preview is not None and s in preview.boards:
        return s
    raise ValueError(
        f'Unknown board "{s}". Call get_boards and use a board `id` or exact name from the list.'
    )


def _oa_params(
    properties: dict[str, Any], required: list[str] | None = None
) -> dict[str, Any]:
    p: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        p["required"] = required
    return p


def _oa_tool(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }


SCHEDULE_AGENT_TOOLS: list[dict[str, Any]] = [
    _oa_tool("get_boards", "List boards (id, name, path, depth, color).", _oa_params({})),
    _oa_tool(
        "get_events",
        "Events on a board.",
        _oa_params({"board_id": {"type": "string"}}, ["board_id"]),
    ),
    _oa_tool(
        "get_tasks",
        "Tasks on a board.",
        _oa_params({"board_id": {"type": "string"}}, ["board_id"]),
    ),
    _oa_tool(
        "get_folders",
        "List folders (id, name, path, depth). Use real parent_folder_id (often root) before creates.",
        _oa_params({}),
    ),
    _oa_tool(
        "get_canvas_assignments",
        "Fetch the user's Canvas LMS courses and assignments (titles, due_at ISO times, points, links). "
        "Call when the user asks about homework, Canvas, syllabus, grades, or what's due. "
        "Also call before proposing create_task or create_event for schoolwork so due dates and titles match Canvas.",
        _oa_params({}),
    ),
    _oa_tool(
        "create_board",
        "Create board under an existing folder only. parent_folder_id = root, fld id, or folder name "
        "(from get_folders or a prior create_folder result). If folders are new, create_folder first.",
        _oa_params(
            {
                "name": {"type": "string"},
                "color": {"type": "string"},
                "parent_folder_id": {"type": "string"},
                "id": {"type": "string"},
            },
            ["name", "parent_folder_id"],
        ),
    ),
    _oa_tool(
        "create_folder",
        "Create folder: same parent_folder_id rules as create_board.",
        _oa_params(
            {
                "name": {"type": "string"},
                "parent_folder_id": {"type": "string"},
                "id": {"type": "string"},
            },
            ["name", "parent_folder_id"],
        ),
    ),
    _oa_tool(
        "delete_board",
        "Delete board (id or name).",
        _oa_params({"board_id": {"type": "string"}}, ["board_id"]),
    ),
    _oa_tool(
        "create_event",
        "Create event: board_id id or name; start_time ISO; end_time optional (+1h default).",
        _oa_params(
            {
                "board_id": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "description": {"type": "string"},
                "location": {"type": "string"},
                "event_color": {"type": "string"},
                "is_all_day": {"type": "boolean", "default": False},
                "recurrence": {
                    "type": "object",
                    "properties": {
                        "frequency": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly", "yearly"],
                        },
                        "day_of_week": {"type": "array", "items": {"type": "string"}},
                        "termination_date": {"type": "string"},
                        "date_start": {"type": "string"},
                    },
                },
            },
            ["board_id", "start_time"],
        ),
    ),
    _oa_tool(
        "update_event",
        "Update event (id + board_id + fields to change).",
        _oa_params(
            {
                "id": {"type": "string"},
                "board_id": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "description": {"type": "string"},
                "location": {"type": "string"},
                "event_color": {"type": "string"},
                "is_all_day": {"type": "boolean"},
                "recurrence": {"type": "object"},
            },
            ["id", "board_id"],
        ),
    ),
    _oa_tool(
        "delete_event",
        "Delete event.",
        _oa_params(
            {"event_id": {"type": "string"}, "board_id": {"type": "string"}},
            ["event_id", "board_id"],
        ),
    ),
    _oa_tool(
        "create_task",
        "Create task: board_id id or name; optional progress/due_date/tag_ids.",
        _oa_params(
            {
                "board_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "progress": {
                    "type": "string",
                    "enum": ["to-do", "in-progress", "done", "pending"],
                },
                "priority_level": {"type": "integer"},
                "due_date": {"type": "string"},
                "tag_ids": {"type": "array", "items": {"type": "string"}},
            },
            ["board_id", "name"],
        ),
    ),
    _oa_tool(
        "update_task",
        "Update task (id + board_id + fields).",
        _oa_params(
            {
                "id": {"type": "string"},
                "board_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "progress": {
                    "type": "string",
                    "enum": ["to-do", "in-progress", "done", "pending"],
                },
                "priority_level": {"type": "integer"},
                "due_date": {"type": "string"},
                "tag_ids": {"type": "array", "items": {"type": "string"}},
            },
            ["id", "board_id"],
        ),
    ),
    _oa_tool(
        "delete_task",
        "Delete task.",
        _oa_params(
            {"task_id": {"type": "string"}, "board_id": {"type": "string"}},
            ["task_id", "board_id"],
        ),
    ),
    _oa_tool(
        "get_notes",
        "List sticky notes; use get_note(id) for one.",
        _oa_params({}),
    ),
    _oa_tool(
        "get_note",
        "Get one note by id.",
        _oa_params({"note_id": {"type": "string"}}, ["note_id"]),
    ),
    _oa_tool(
        "create_note",
        "Create note; optional board_id; title/body may be empty.",
        _oa_params(
            {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "color": {"type": "string"},
                "board_id": {"type": "string"},
                "position_x": {"type": "number"},
                "position_y": {"type": "number"},
                "width": {"type": "number"},
                "height": {"type": "number"},
                "archived": {"type": "boolean"},
                "links": {"type": "array", "items": {"type": "string"}},
                "id": {"type": "string"},
            },
            ["title", "body"],
        ),
    ),
    _oa_tool(
        "update_note",
        "Update note by id.",
        _oa_params(
            {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "color": {"type": "string"},
                "board_id": {"type": "string"},
                "position_x": {"type": "number"},
                "position_y": {"type": "number"},
                "width": {"type": "number"},
                "height": {"type": "number"},
                "archived": {"type": "boolean"},
                "links": {"type": "array", "items": {"type": "string"}},
            },
            ["id"],
        ),
    ),
    _oa_tool(
        "delete_note",
        "Delete note by id.",
        _oa_params({"note_id": {"type": "string"}}, ["note_id"]),
    ),
]

WRITE_TOOL_NAMES: frozenset[str] = frozenset({
    "create_board", "create_folder", "delete_board",
    "create_event", "update_event", "delete_event",
    "create_task", "update_task", "delete_task",
    "create_note", "update_note", "delete_note",
})


def prepare_write_arguments(
    tool_name: str,
    arguments: dict[str, Any],
    user_id: str,
    preview: Optional[PlanPreviewRegistry] = None,
) -> dict[str, Any]:
    """Defaults, name→id resolution, stable ids for create_* (aligns preview + execute_plan)."""
    out = dict(arguments)

    if tool_name == "create_board":
        out["parent_folder_id"] = _resolve_folder_id(
            out.get("parent_folder_id"), user_id, preview
        )
        name = str(out.get("name") or "").strip()
        if not name:
            raise ValueError("create_board requires a non-empty name")
        out["name"] = name
        c = str(out.get("color") or "").strip()
        out["color"] = c if _HEX6.fullmatch(c) else DEFAULT_BOARD_COLOR
        if not out.get("id"):
            out["id"] = f"bd_{uuid.uuid4().hex[:12]}"
        return out

    if tool_name == "create_folder":
        out["parent_folder_id"] = _resolve_folder_id(
            out.get("parent_folder_id"), user_id, preview
        )
        name = str(out.get("name") or "").strip()
        if not name:
            raise ValueError("create_folder requires a non-empty name")
        out["name"] = name
        if not out.get("id"):
            out["id"] = f"fld_{uuid.uuid4().hex[:12]}"
        return out

    if tool_name == "create_event":
        out["board_id"] = _resolve_board_id(out.get("board_id"), user_id, preview)
        st = out.get("start_time")
        if not st:
            raise ValueError("create_event requires start_time")
        et = out.get("end_time")
        dt_s = _parse_event_time(str(st))
        if et:
            dt_e = _parse_event_time(str(et))
        else:
            dt_e = dt_s + timedelta(hours=1)
        if dt_e <= dt_s:
            dt_e = dt_s + timedelta(hours=1)
        out["start_time"] = dt_s.isoformat()
        out["end_time"] = dt_e.isoformat()
        out.setdefault("description", "")
        out.setdefault("location", "")
        ec = str(out.get("event_color") or "").strip()
        out["event_color"] = ec if _HEX6.fullmatch(ec) else DEFAULT_EVENT_COLOR
        if "is_all_day" not in out:
            out["is_all_day"] = False
        if not out.get("id"):
            out["id"] = f"evt_{uuid.uuid4().hex[:12]}"
        return out

    if tool_name == "create_task":
        out["board_id"] = _resolve_board_id(out.get("board_id"), user_id, preview)
        name = str(out.get("name") or "").strip()
        if not name:
            raise ValueError("create_task requires a non-empty name")
        out["name"] = name
        out.setdefault("description", "")
        out.setdefault("progress", "to-do")
        if out["progress"] not in ("to-do", "in-progress", "done", "pending"):
            out["progress"] = "to-do"
        try:
            out["priority_level"] = int(out.get("priority_level", 0))
        except (TypeError, ValueError):
            out["priority_level"] = 0
        if not out.get("due_date"):
            out["due_date"] = date.today().isoformat()
        if not out.get("id"):
            out["id"] = f"tsk_{uuid.uuid4().hex[:12]}"
        return out

    if tool_name == "create_note":
        out.setdefault("title", "")
        out.setdefault("body", "")
        raw_bid = out.get("board_id")
        if raw_bid not in (None, ""):
            out["board_id"] = _resolve_board_id(raw_bid, user_id, preview)
        if not out.get("id"):
            out["id"] = f"nt_{uuid.uuid4().hex[:12]}"
        return out

    if tool_name in (
        "delete_board",
        "delete_event",
        "delete_task",
        "update_event",
        "update_task",
    ):
        out["board_id"] = _resolve_board_id(out.get("board_id"), user_id, preview)
        return out

    if tool_name == "update_note":
        raw_bid = out.get("board_id")
        if raw_bid not in (None, ""):
            out["board_id"] = _resolve_board_id(raw_bid, user_id, preview)
        return out

    return out


def normalize_tool_arguments(
    tool_name: str,
    arguments: Optional[dict[str, Any]],
    user_id: str,
    preview: Optional[PlanPreviewRegistry] = None,
) -> dict[str, Any]:
    """Name→id resolution and defaults for tool arguments."""
    out = dict(arguments or {})
    if tool_name in ("get_events", "get_tasks"):
        if out.get("board_id") not in (None, ""):
            out["board_id"] = _resolve_board_id(out.get("board_id"), user_id, preview)
        return out
    if tool_name in WRITE_TOOL_NAMES:
        return prepare_write_arguments(tool_name, out, user_id, preview)
    return out


def _preview_queued(action: str, **fields: Any) -> str:
    return json.dumps(
        {"message": f"{action} queued for confirmation (not applied yet).", **fields}
    )


def preview_write_tool(
    tool_name: str,
    arguments: dict[str, Any],
    user_id: str,
    preview: Optional[PlanPreviewRegistry] = None,
) -> str:
    """Plan-only dry run; same JSON shape as execute where applicable."""
    a = arguments
    if tool_name == "create_board":
        return _create_board(a, user_id, persist=False, preview=preview)
    if tool_name == "create_folder":
        return _create_folder(a, user_id, persist=False, preview=preview)
    if tool_name == "create_event":
        return _create_event(a, persist=False)
    if tool_name == "create_task":
        return _create_task(a, user_id, persist=False)
    if tool_name == "create_note":
        return _create_note(a, user_id, persist=False)
    if tool_name == "delete_board":
        return _preview_queued("Deletion", board_id=a.get("board_id"))
    if tool_name == "delete_event":
        return _preview_queued(
            "Deletion", event_id=a.get("event_id"), board_id=a.get("board_id")
        )
    if tool_name == "delete_task":
        return _preview_queued(
            "Deletion", task_id=a.get("task_id"), board_id=a.get("board_id")
        )
    if tool_name == "delete_note":
        return _preview_queued("Deletion", note_id=a.get("note_id"))
    if tool_name == "update_event":
        return _preview_queued("Update", event_id=a.get("id"), board_id=a.get("board_id"))
    if tool_name == "update_task":
        return _preview_queued("Update", task_id=a.get("id"), board_id=a.get("board_id"))
    if tool_name == "update_note":
        return _preview_queued("Update", note_id=a.get("id"))
    return json.dumps({"error": f"No plan preview for write tool: {tool_name}"})


def execute_tool(tool_name: str, arguments: dict[str, Any], user_id: str) -> str:
    a, u = arguments, user_id
    try:
        if tool_name == "get_boards":
            return _get_boards(u)
        if tool_name == "get_folders":
            return _get_folders(u)
        if tool_name == "get_canvas_assignments":
            return _get_canvas_assignments()
        if tool_name == "get_events":
            return _get_events(a["board_id"])
        if tool_name == "get_tasks":
            return _get_tasks(a["board_id"])
        if tool_name == "create_board":
            return _create_board(a, u)
        if tool_name == "create_folder":
            return _create_folder(a, u)
        if tool_name == "delete_board":
            return _delete_board(a["board_id"], u)
        if tool_name == "create_event":
            return _create_event(a)
        if tool_name == "update_event":
            return _update_event(a)
        if tool_name == "delete_event":
            return _delete_event(a["event_id"], a["board_id"])
        if tool_name == "create_task":
            return _create_task(a, u)
        if tool_name == "update_task":
            return _update_task(a)
        if tool_name == "delete_task":
            return _delete_task(a["task_id"], a["board_id"])
        if tool_name == "get_notes":
            return _get_notes(u)
        if tool_name == "get_note":
            return _get_note(a["note_id"], u)
        if tool_name == "create_note":
            return _create_note(a, u)
        if tool_name == "update_note":
            return _update_note(a, u)
        if tool_name == "delete_note":
            return _delete_note(a["note_id"], u)
        return f"Unknown tool: {tool_name}"
    except NotFoundError:
        return "Not found (e.g. missing board, event, task, folder, or note)."
    except ValidationError as e:
        return f"Validation failed: {e.errors()}"
    except InvalidEventTimeError:
        return "Event start time must be before end time."
    except Exception as e:
        return f"Error: {e!s}"


def _slug_segment(name: str, default: str = "item") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    s = s.strip("-")
    return s or default


def _path_and_depth_under_parent(
    parent: Folder, child_name: str, slug_default: str = "board"
) -> tuple[str, int]:
    base = (parent.path or "/root").rstrip("/") or "/root"
    segment = _slug_segment(child_name, default=slug_default)
    suffix = uuid.uuid4().hex[:8]
    child_path = f"{base}/{segment}-{suffix}"
    child_depth = int(parent.depth) + 1
    return child_path, child_depth


def _get_boards(user_id: str) -> str:
    svc = BoardService()
    boards = svc.get_boards_by_user_id(user_id) or []
    return json.dumps(
        [
            {
                "id": b.id,
                "name": b.name,
                "path": b.path,
                "depth": b.depth,
                "color": b.color,
            }
            for b in boards
        ]
    )


def _get_canvas_assignments() -> str:
    snap = fetch_canvas_snapshot()
    if not snap.get("ok"):
        return json.dumps(snap)
    return json.dumps(
        {
            "ok": True,
            "courses": snap["digest"],
            "course_count": snap.get("course_count"),
            "assignment_count": snap.get("assignment_count"),
        }
    )


def _get_folders(user_id: str) -> str:
    fs = FolderService()
    fs.ensure_root_folder(user_id)
    rows = fs.get_boards_by_user_id(user_id) or []
    out = []
    for f in rows:
        if f is None:
            continue
        out.append(
            {
                "id": f.id,
                "name": f.name,
                "path": f.path,
                "depth": f.depth,
            }
        )
    out.sort(key=lambda x: (int(x.get("depth") or 0), str(x.get("name") or "")))
    return json.dumps(out)


def _create_board(
    args: dict[str, Any],
    user_id: str,
    *,
    persist: bool = True,
    preview: Optional[PlanPreviewRegistry] = None,
) -> str:
    FolderService().ensure_root_folder(user_id)
    parent = _get_folder_for_parent(str(args["parent_folder_id"]), user_id, preview)
    if not parent:
        raise NotFoundError(
            "Parent folder not found. Create the folder with create_folder first, "
            "then use its folder_id or the folder name from get_folders / prior tool results."
        )
    path, depth = _path_and_depth_under_parent(parent, str(args["name"]))
    board_id = args.get("id") or f"bd_{uuid.uuid4().hex[:12]}"
    board = Board(
        id=board_id,
        user_id=user_id,
        name=args["name"],
        path=path,
        depth=depth,
        color=args["color"],
    )
    if persist:
        BoardService().create_board(board)
    elif preview is not None:
        preview.boards[board.id] = board
    msg = "Board created successfully" if persist else "Board would be created (plan only — not applied yet)."
    return json.dumps(
        {
            "message": msg,
            "board_id": board_id,
            "path": path,
            "depth": depth,
            "parent_folder_id": parent.id,
        }
    )


def _create_folder(
    args: dict[str, Any],
    user_id: str,
    *,
    persist: bool = True,
    preview: Optional[PlanPreviewRegistry] = None,
) -> str:
    fs = FolderService()
    fs.ensure_root_folder(user_id)
    parent = _get_folder_for_parent(str(args["parent_folder_id"]), user_id, preview)
    if not parent:
        raise NotFoundError(
            "Parent folder not found. Use root or an existing folder id/name from get_folders."
        )
    path, depth = _path_and_depth_under_parent(parent, str(args["name"]), slug_default="folder")
    folder_id = args.get("id") or f"fld_{uuid.uuid4().hex[:12]}"
    folder = Folder(
        id=folder_id,
        user_id=user_id,
        name=args["name"],
        path=path,
        depth=depth,
    )
    if persist:
        fs.create_folder(folder)
    elif preview is not None:
        preview.folders[folder.id] = folder
    msg = "Folder created successfully" if persist else "Folder would be created (plan only — not applied yet)."
    return json.dumps(
        {
            "message": msg,
            "folder_id": folder_id,
            "path": path,
            "depth": depth,
            "parent_folder_id": parent.id,
        }
    )


def _delete_board(board_id: str, user_id: str) -> str:
    BoardService().delete_board(board_id, user_id)
    return json.dumps({"message": "Board deleted successfully"})


def _get_events(board_id: str) -> str:
    svc = EventService()
    events = svc.get_event_by_board(board_id) or []
    out = []
    for e in events:
        rec = e.recurrence.model_dump(mode="json") if e.recurrence else None
        out.append({
            "id": e.id,
            "board_id": e.board_id,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat(),
            "event_color": e.event_color,
            "is_all_day": e.is_all_day,
            "description": e.description,
            "location": e.location,
            "recurrence": rec,
        })
    return json.dumps(out)


def _get_tasks(board_id: str) -> str:
    svc = TaskService()
    tasks = svc.get_tasks_by_board(board_id)
    out = [
        {
            "id": t.id,
            "board_id": t.board_id,
            "name": t.name,
            "description": t.description,
            "progress": t.progress,
            "priority_level": t.priority_level,
            "due_date": t.due_date.isoformat(),
            "tag_ids": t.tag_ids,
        }
        for t in tasks
    ]
    return json.dumps(out)


def _parse_recurrence(data: Any) -> Recurrence | None:
    if not data:
        return None
    if isinstance(data, Recurrence):
        return data
    return Recurrence(**data)


def _parse_event_time(s: str) -> datetime:
    if not s:
        raise ValueError("Empty event time")
    s = s.strip().replace("Z", "+00:00")
    if "T" in s:
        return datetime.fromisoformat(s)
    return datetime.fromisoformat(s + "T00:00:00")


def _create_event(args: dict[str, Any], *, persist: bool = True) -> str:
    event_id = args.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
    recurrence = _parse_recurrence(args.get("recurrence"))
    event = Event(
        id=event_id,
        board_id=args["board_id"],
        start_time=_parse_event_time(args["start_time"]),
        end_time=_parse_event_time(args["end_time"]),
        event_color=args["event_color"],
        is_all_day=args.get("is_all_day", False),
        description=args["description"],
        location=args["location"],
        recurrence=recurrence,
    )
    if persist:
        EventService().create_event(event)
    msg = "Event created successfully" if persist else "Event would be created (plan only — not applied yet)."
    return json.dumps({"message": msg, "event_id": event_id, "board_id": args["board_id"]})


def _update_event(args: dict[str, Any]) -> str:
    event_id = args["id"]
    board_id = args["board_id"]
    svc = EventService()
    existing = svc.get_event_by_id(event_id, board_id)
    if not existing:
        raise NotFoundError()
    recurrence = _parse_recurrence(args.get("recurrence")) if "recurrence" in args else existing.recurrence
    event = Event(
        id=existing.id,
        board_id=existing.board_id,
        start_time=_parse_event_time(args["start_time"]) if args.get("start_time") else existing.start_time,
        end_time=_parse_event_time(args["end_time"]) if args.get("end_time") else existing.end_time,
        event_color=args.get("event_color") or existing.event_color,
        is_all_day=args.get("is_all_day") if "is_all_day" in args else existing.is_all_day,
        description=args.get("description") or existing.description,
        location=args.get("location") or existing.location,
        recurrence=recurrence,
    )
    svc.update_event(event)
    return json.dumps({"message": "Event updated successfully", "event_id": event_id})


def _delete_event(event_id: str, board_id: str) -> str:
    EventService().delete_event(event_id, board_id)
    return json.dumps({"message": "Event deleted successfully"})


def _create_task(args: dict[str, Any], user_id: str, *, persist: bool = True) -> str:
    task_id = args.get("id") or f"tsk_{uuid.uuid4().hex[:12]}"
    raw_tags = args.get("tag_ids")
    if raw_tags is None:
        tag_ids: list[str] = []
    elif isinstance(raw_tags, list):
        tag_ids = [str(x) for x in raw_tags]
    else:
        tag_ids = []
    priority_level = int(args["priority_level"])
    task = Task(
        id=task_id,
        board_id=args["board_id"],
        user_id=user_id,
        name=args["name"],
        description=args["description"],
        progress=args["progress"],
        priority_level=priority_level,
        due_date=date.fromisoformat(str(args["due_date"]).split("T")[0]),
        tag_ids=tag_ids,
    )
    if persist:
        TaskService().create_task(task)
    msg = "Task created successfully" if persist else "Task would be created (plan only — not applied yet)."
    return json.dumps({"message": msg, "task_id": task_id, "board_id": args["board_id"]})


def _update_task(args: dict[str, Any]) -> str:
    task_id = args["id"]
    board_id = args["board_id"]
    svc = TaskService()
    existing = svc.get_task(board_id, task_id)
    if "priority_level" in args:
        new_priority = int(args["priority_level"])
    else:
        new_priority = existing.priority_level
    if "tag_ids" in args and isinstance(args["tag_ids"], list):
        new_tags = [str(x) for x in args["tag_ids"]]
    else:
        new_tags = existing.tag_ids
    task = Task(
        id=existing.id,
        board_id=existing.board_id,
        user_id=existing.user_id,
        name=args.get("name") or existing.name,
        description=args.get("description") or existing.description,
        progress=args.get("progress") or existing.progress,
        priority_level=new_priority,
        due_date=date.fromisoformat(str(args["due_date"]).split("T")[0])
        if args.get("due_date")
        else existing.due_date,
        tag_ids=new_tags,
    )
    svc.update_task(task)
    return json.dumps({"message": "Task updated successfully", "task_id": task_id})


def _delete_task(task_id: str, board_id: str) -> str:
    TaskService().delete_task(board_id, task_id)
    return json.dumps({"message": "Task deleted successfully"})


def _note_to_tool_dict(n: Note) -> dict[str, Any]:
    return {
        "id": n.id,
        "title": n.title,
        "body": n.body,
        "color": n.color,
        "position_x": n.position_x,
        "position_y": n.position_y,
        "width": n.width,
        "height": n.height,
        "links": n.links,
        "archived": n.archived,
        "updated_at": n.updated_at,
        "board_id": n.board_id,
    }


def _get_notes(user_id: str) -> str:
    notes = NoteService().get_notes_by_user_id(user_id)
    return json.dumps([_note_to_tool_dict(n) for n in notes])


def _get_note(note_id: str, user_id: str) -> str:
    n = NoteService().get_note_by_id(note_id, user_id)
    return json.dumps(_note_to_tool_dict(n))


def _create_note(args: dict[str, Any], user_id: str, *, persist: bool = True) -> str:
    note_id = args.get("id") or f"nt_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    raw_links = args.get("links")
    if isinstance(raw_links, list):
        links = [str(x) for x in raw_links]
    else:
        links = []
    raw_bid = args.get("board_id")
    board_id: Optional[str] = str(raw_bid) if raw_bid not in (None, "") else None
    note = Note(
        id=note_id,
        user_id=user_id,
        title=str(args.get("title") or ""),
        body=str(args.get("body") or ""),
        color=str(args.get("color") or "bg-pink"),
        position_x=float(args.get("position_x", 0.0)),
        position_y=float(args.get("position_y", 0.0)),
        width=float(args.get("width", 380.0)),
        height=float(args.get("height", 300.0)),
        links=links,
        archived=bool(args.get("archived", False)),
        updated_at=now,
        board_id=board_id,
    )
    if persist:
        NoteService().create_note(note)
    msg = "Note created successfully" if persist else "Note would be created (plan only — not applied yet)."
    return json.dumps({"message": msg, "note_id": note_id})


def _update_note(args: dict[str, Any], user_id: str) -> str:
    note_id = str(args["id"])
    svc = NoteService()
    existing = svc.get_note_by_id(note_id, user_id)
    now = datetime.now(timezone.utc).isoformat()
    if "links" in args and isinstance(args["links"], list):
        new_links = [str(x) for x in args["links"]]
    else:
        new_links = existing.links
    if "board_id" in args:
        raw_b = args.get("board_id")
        new_board_id: Optional[str] = str(raw_b) if raw_b not in (None, "") else None
    else:
        new_board_id = existing.board_id
    note = Note(
        id=existing.id,
        user_id=existing.user_id,
        title=str(args["title"]) if "title" in args else existing.title,
        body=str(args["body"]) if "body" in args else existing.body,
        color=str(args["color"]) if "color" in args else existing.color,
        position_x=float(args["position_x"]) if "position_x" in args else existing.position_x,
        position_y=float(args["position_y"]) if "position_y" in args else existing.position_y,
        width=float(args["width"]) if "width" in args else existing.width,
        height=float(args["height"]) if "height" in args else existing.height,
        links=new_links,
        archived=bool(args["archived"]) if "archived" in args else existing.archived,
        updated_at=now,
        board_id=new_board_id,
    )
    svc.update_note(note)
    return json.dumps({"message": "Note updated successfully", "note_id": note_id})


def _delete_note(note_id: str, user_id: str) -> str:
    NoteService().delete_note(note_id, user_id)
    return json.dumps({"message": "Note deleted successfully"})
