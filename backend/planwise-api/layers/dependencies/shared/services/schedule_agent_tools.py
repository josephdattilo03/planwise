"""OpenAI tool definitions and executor for the schedule agent."""
import json
import uuid
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from shared.models.board import Board
from shared.models.event import Event, Recurrence
from shared.models.task import Task
from shared.services.board_service import BoardService
from shared.services.event_service import EventService
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
            "description": "List all boards for the user. Returns board id, name, path, and color.",
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
            "name": "create_board",
            "description": "Create a new board for the user. You may omit id; one will be generated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Board display name"},
                    "path": {"type": "string", "description": "Path e.g. /work or /personal"},
                    "depth": {"type": "integer", "description": "Depth in folder tree (1 for top-level)"},
                    "color": {"type": "string", "description": "Hex color e.g. #3b82f6"},
                },
                "required": ["name", "path", "depth", "color"],
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
            "description": "Create a new task on a board. due_date and created_at in YYYY-MM-DD. You may omit id; one will be generated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "progress": {"type": "string", "enum": ["to-do", "in-progress", "done", "pending"]},
                    "priority_level": {"type": "integer"},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "created_at": {"type": "string", "description": "YYYY-MM-DD, optional; defaults to today"},
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
                    "created_at": {"type": "string"},
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
]

# Tool names that modify data; in plan_only mode these are recorded, not executed.
WRITE_TOOL_NAMES: frozenset[str] = frozenset({
    "create_board", "delete_board",
    "create_event", "update_event", "delete_event",
    "create_task", "update_task", "delete_task",
})


def execute_tool(tool_name: str, arguments: dict[str, Any], user_id: str) -> str:
    """
    Execute a single tool and return a short result string for the LLM.
    Catches validation and not-found errors and returns them as strings.
    """
    try:
        if tool_name == "get_boards":
            return _get_boards(user_id)
        if tool_name == "get_events":
            return _get_events(arguments["board_id"])
        if tool_name == "get_tasks":
            return _get_tasks(arguments["board_id"])
        if tool_name == "create_board":
            return _create_board(arguments, user_id)
        if tool_name == "delete_board":
            return _delete_board(arguments["board_id"], user_id)
        if tool_name == "create_event":
            return _create_event(arguments)
        if tool_name == "update_event":
            return _update_event(arguments)
        if tool_name == "delete_event":
            return _delete_event(arguments["event_id"], arguments["board_id"])
        if tool_name == "create_task":
            return _create_task(arguments)
        if tool_name == "update_task":
            return _update_task(arguments)
        if tool_name == "delete_task":
            return _delete_task(arguments["task_id"], arguments["board_id"])
        return f"Unknown tool: {tool_name}"
    except NotFoundError:
        return "Not found."
    except ValidationError as e:
        return f"Validation failed: {e.errors()}"
    except InvalidEventTimeError:
        return "Event start time must be before end time."
    except Exception as e:
        return f"Error: {e!s}"


def _get_boards(user_id: str) -> str:
    svc = BoardService()
    boards = svc.get_boards_by_user_id(user_id) or []
    return json.dumps([{"id": b.id, "name": b.name, "path": b.path, "color": b.color} for b in boards])


def _create_board(args: dict[str, Any], user_id: str) -> str:
    board_id = args.get("id") or f"bd_{uuid.uuid4().hex[:12]}"
    board = Board(
        id=board_id,
        user_id=user_id,
        name=args["name"],
        path=args["path"],
        depth=args["depth"],
        color=args["color"],
    )
    BoardService().create_board(board)
    return json.dumps({"message": "Board created successfully", "board_id": board_id})


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
            "created_at": t.created_at.isoformat(),
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


def _create_event(args: dict[str, Any]) -> str:
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
    EventService().create_event(event)
    return json.dumps({"message": "Event created successfully", "event_id": event_id})


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


def _create_task(args: dict[str, Any]) -> str:
    task_id = args.get("id") or f"tsk_{uuid.uuid4().hex[:12]}"
    today = date.today()
    created_at_str = args.get("created_at") or today.isoformat()
    task = Task(
        id=task_id,
        board_id=args["board_id"],
        name=args["name"],
        description=args["description"],
        progress=args["progress"],
        priority_level=args["priority_level"],
        due_date=date.fromisoformat(args["due_date"]),
        created_at=date.fromisoformat(created_at_str),
    )
    TaskService().create_task(task)
    return json.dumps({"message": "Task created successfully", "task_id": task_id})


def _update_task(args: dict[str, Any]) -> str:
    task_id = args["id"]
    board_id = args["board_id"]
    svc = TaskService()
    existing = svc.get_task(board_id, task_id)
    task = Task(
        id=existing.id,
        board_id=existing.board_id,
        name=args.get("name") or existing.name,
        description=args.get("description") or existing.description,
        progress=args.get("progress") or existing.progress,
        priority_level=args.get("priority_level") if "priority_level" in args else existing.priority_level,
        due_date=date.fromisoformat(args["due_date"]) if args.get("due_date") else existing.due_date,
        created_at=date.fromisoformat(args["created_at"]) if args.get("created_at") else existing.created_at,
    )
    svc.update_task(task)
    return json.dumps({"message": "Task updated successfully", "task_id": task_id})


def _delete_task(task_id: str, board_id: str) -> str:
    TaskService().delete_task(board_id, task_id)
    return json.dumps({"message": "Task deleted successfully"})
