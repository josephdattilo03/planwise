"""OpenAI tool definitions and executor for the schedule agent."""
import json
import re
import uuid
from datetime import date, datetime, timezone
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
from shared.utils.errors import InvalidEventTimeError, NotFoundError

# ---------------------------------------------------------------------------
# OpenAI tool definitions (function-calling format)
# ---------------------------------------------------------------------------

SCHEDULE_AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_boards",
            "description": "List all boards for the user. Returns id, name, path, depth, and color (same fields the app uses for boards).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_events",
            "description": "Get all events for a given board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {"type": "string", "description": "The board ID"},
                },
                "required": ["board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tasks",
            "description": "Get all tasks for a given board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {"type": "string", "description": "The board ID"},
                },
                "required": ["board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_folders",
            "description": (
                "List all folders for the user (workspace tree). Returns id, name, path, depth. "
                "Use this before create_board or create_folder so you use a real parent_folder_id "
                "(e.g. \"root\" for top-level). Boards appear under a parent folder when path/depth match that folder; "
                "the app computes path from the parent — do not invent path strings yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_board",
            "description": (
                "Create a new board under a parent folder (same rules as the Planwise UI). "
                "Always set parent_folder_id from get_folders (typically \"root\" for workspace root). "
                "Path and depth are computed from the parent so the board shows in the folder tree."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Board display name"},
                    "color": {"type": "string", "description": "Hex color e.g. #3b82f6"},
                    "parent_folder_id": {
                        "type": "string",
                        "description": 'Parent folder id, e.g. "root" for boards at workspace root',
                    },
                    "id": {
                        "type": "string",
                        "description": "Optional; omit to auto-generate",
                    },
                },
                "required": ["name", "color", "parent_folder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": (
                "Create a subfolder under a parent folder. Path and depth are derived from the parent "
                "like the rest of the app so the folder appears in the tree."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Folder display name"},
                    "parent_folder_id": {"type": "string", "description": "Parent folder id (use get_folders)"},
                    "id": {"type": "string", "description": "Optional; omit to auto-generate"},
                },
                "required": ["name", "parent_folder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_board",
            "description": "Delete a board. Events and tasks on the board may need to be deleted separately depending on backend behavior.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {"type": "string", "description": "The board ID to delete"},
                },
                "required": ["board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create a new event on a board. Dates in YYYY-MM-DD. You may omit id; one will be generated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO date or datetime: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"},
                    "end_time": {"type": "string", "description": "ISO date or datetime: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "event_color": {"type": "string", "description": "Hex color e.g. #3b82f6"},
                    "is_all_day": {"type": "boolean", "default": False},
                    "recurrence": {
                        "type": "object",
                        "description": "Optional. frequency: daily|weekly|monthly|yearly; day_of_week: list of weekday names; termination_date: YYYY-MM-DD; date_start: optional YYYY-MM-DD",
                        "properties": {
                            "frequency": {"type": "string", "enum": ["daily", "weekly", "monthly", "yearly"]},
                            "day_of_week": {"type": "array", "items": {"type": "string"}},
                            "termination_date": {"type": "string"},
                            "date_start": {"type": "string"},
                        },
                    },
                },
                "required": ["board_id", "start_time", "end_time", "description", "location", "event_color", "is_all_day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_event",
            "description": "Update an existing event. Provide event id, board_id, and any fields to update.",
            "parameters": {
                "type": "object",
                "properties": {
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
                "required": ["id", "board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "Delete an event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "board_id": {"type": "string"},
                },
                "required": ["event_id", "board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task on a board. due_date is YYYY-MM-DD. You may omit id and tag_ids. Call get_boards first to use a real board_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "progress": {"type": "string", "enum": ["to-do", "in-progress", "done", "pending"]},
                    "priority_level": {"type": "integer"},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tag ids; omit or use empty array if none",
                    },
                },
                "required": ["board_id", "name", "description", "progress", "priority_level", "due_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update an existing task. Provide task id, board_id, and any fields to update.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "board_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "progress": {"type": "string", "enum": ["to-do", "in-progress", "done", "pending"]},
                    "priority_level": {"type": "integer"},
                    "due_date": {"type": "string"},
                    "tag_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Delete a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "board_id": {"type": "string"},
                },
                "required": ["task_id", "board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_notes",
            "description": (
                "List all sticky notes for the user (title, body, color, layout, archived, optional board_id). "
                "Use get_note for one note if you already know the id."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_note",
            "description": "Fetch a single note by id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note id"},
                },
                "required": ["note_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": (
                "Create a sticky note. Optional board_id ties it to a board in the UI. "
                "Color uses UI tokens like bg-pink, bg-yellow (default bg-pink). "
                "Omit id to auto-generate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "May be empty string"},
                    "body": {"type": "string", "description": "Note text content"},
                    "color": {
                        "type": "string",
                        "description": "e.g. bg-pink, bg-yellow, bg-blue",
                    },
                    "board_id": {
                        "type": "string",
                        "description": "Optional board id to associate the note",
                    },
                    "position_x": {"type": "number"},
                    "position_y": {"type": "number"},
                    "width": {"type": "number"},
                    "height": {"type": "number"},
                    "archived": {"type": "boolean"},
                    "links": {"type": "array", "items": {"type": "string"}},
                    "id": {"type": "string"},
                },
                "required": ["title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_note",
            "description": "Update an existing note. Provide note id and any fields to change.",
            "parameters": {
                "type": "object",
                "properties": {
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
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_note",
            "description": "Delete a note by id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {"type": "string"},
                },
                "required": ["note_id"],
            },
        },
    },
]

# Tool names that modify data; in plan_only mode these are recorded, not executed.
WRITE_TOOL_NAMES: frozenset[str] = frozenset({
    "create_board", "create_folder", "delete_board",
    "create_event", "update_event", "delete_event",
    "create_task", "update_task", "delete_task",
    "create_note", "update_note", "delete_note",
})


def enrich_write_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure create_* calls have stable ids before plan preview and execute_plan.
    Matches id generation in _create_* so preview tool results and execution stay aligned.
    """
    out = dict(arguments)
    if tool_name == "create_board" and not out.get("id"):
        out["id"] = f"bd_{uuid.uuid4().hex[:12]}"
    elif tool_name == "create_folder" and not out.get("id"):
        out["id"] = f"fld_{uuid.uuid4().hex[:12]}"
    elif tool_name == "create_event" and not out.get("id"):
        out["id"] = f"evt_{uuid.uuid4().hex[:12]}"
    elif tool_name == "create_task" and not out.get("id"):
        out["id"] = f"tsk_{uuid.uuid4().hex[:12]}"
    elif tool_name == "create_note" and not out.get("id"):
        out["id"] = f"nt_{uuid.uuid4().hex[:12]}"
    return out


def preview_write_tool(tool_name: str, arguments: dict[str, Any], user_id: str) -> str:
    """
    Plan-only: return the same JSON shape as execute_tool would, without persisting.
    Lets the model chain tools (e.g. create_board then create_event with board_id).
    """
    if tool_name == "create_board":
        return _create_board(arguments, user_id, persist=False)
    if tool_name == "create_folder":
        return _create_folder(arguments, user_id, persist=False)
    if tool_name == "create_event":
        return _create_event(arguments, persist=False)
    if tool_name == "create_task":
        return _create_task(arguments, user_id, persist=False)
    if tool_name == "create_note":
        return _create_note(arguments, user_id, persist=False)
    if tool_name == "delete_board":
        return json.dumps({
            "message": "Deletion queued for confirmation (not applied yet).",
            "board_id": arguments.get("board_id"),
        })
    if tool_name == "delete_event":
        return json.dumps({
            "message": "Deletion queued for confirmation (not applied yet).",
            "event_id": arguments.get("event_id"),
            "board_id": arguments.get("board_id"),
        })
    if tool_name == "delete_task":
        return json.dumps({
            "message": "Deletion queued for confirmation (not applied yet).",
            "task_id": arguments.get("task_id"),
            "board_id": arguments.get("board_id"),
        })
    if tool_name == "delete_note":
        return json.dumps({
            "message": "Deletion queued for confirmation (not applied yet).",
            "note_id": arguments.get("note_id"),
        })
    if tool_name == "update_event":
        return json.dumps({
            "message": "Update queued for confirmation (not applied yet).",
            "event_id": arguments.get("id"),
            "board_id": arguments.get("board_id"),
        })
    if tool_name == "update_task":
        return json.dumps({
            "message": "Update queued for confirmation (not applied yet).",
            "task_id": arguments.get("id"),
            "board_id": arguments.get("board_id"),
        })
    if tool_name == "update_note":
        return json.dumps({
            "message": "Update queued for confirmation (not applied yet).",
            "note_id": arguments.get("id"),
        })
    return json.dumps({"error": f"No plan preview for write tool: {tool_name}"})


def execute_tool(tool_name: str, arguments: dict[str, Any], user_id: str) -> str:
    """
    Execute a single tool and return a short result string for the LLM.
    Catches validation and not-found errors and returns them as strings.
    """
    try:
        if tool_name == "get_boards":
            return _get_boards(user_id)
        if tool_name == "get_folders":
            return _get_folders(user_id)
        if tool_name == "get_events":
            return _get_events(arguments["board_id"])
        if tool_name == "get_tasks":
            return _get_tasks(arguments["board_id"])
        if tool_name == "create_board":
            return _create_board(arguments, user_id)
        if tool_name == "create_folder":
            return _create_folder(arguments, user_id)
        if tool_name == "delete_board":
            return _delete_board(arguments["board_id"], user_id)
        if tool_name == "create_event":
            return _create_event(arguments)
        if tool_name == "update_event":
            return _update_event(arguments)
        if tool_name == "delete_event":
            return _delete_event(arguments["event_id"], arguments["board_id"])
        if tool_name == "create_task":
            return _create_task(arguments, user_id)
        if tool_name == "update_task":
            return _update_task(arguments)
        if tool_name == "delete_task":
            return _delete_task(arguments["task_id"], arguments["board_id"])
        if tool_name == "get_notes":
            return _get_notes(user_id)
        if tool_name == "get_note":
            return _get_note(arguments["note_id"], user_id)
        if tool_name == "create_note":
            return _create_note(arguments, user_id)
        if tool_name == "update_note":
            return _update_note(arguments, user_id)
        if tool_name == "delete_note":
            return _delete_note(arguments["note_id"], user_id)
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
    """Match planwise-ui boardService: lower case, non-alphanumeric -> hyphen, trim."""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    s = s.strip("-")
    return s or default


def _path_and_depth_under_parent(
    parent: Folder, child_name: str, slug_default: str = "board"
) -> tuple[str, int]:
    """
    Same path/depth rules as planwise-ui createBoard: extend parent.path with a slug + unique suffix;
    depth = parent.depth + 1.
    """
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


def _create_board(args: dict[str, Any], user_id: str, *, persist: bool = True) -> str:
    fs = FolderService()
    fs.ensure_root_folder(user_id)
    parent = fs.get_folder_by_id(str(args["parent_folder_id"]), user_id)
    if not parent:
        raise NotFoundError()
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


def _create_folder(args: dict[str, Any], user_id: str, *, persist: bool = True) -> str:
    fs = FolderService()
    fs.ensure_root_folder(user_id)
    parent = fs.get_folder_by_id(str(args["parent_folder_id"]), user_id)
    if not parent:
        raise NotFoundError()
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
    """Parse start_time/end_time from YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (with optional Z)."""
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
