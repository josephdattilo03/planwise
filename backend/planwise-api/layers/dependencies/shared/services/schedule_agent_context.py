"""Builds schedule context (boards, events, tasks) for the schedule agent."""
from datetime import date
from typing import Any, Optional

from shared.models.board import Board
from shared.models.event import Event
from shared.models.task import Task
from shared.services.board_service import BoardService
from shared.services.event_service import EventService
from shared.services.task_service import TaskService


def build_schedule_context(
    user_id: str,
    board_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Build a JSON-serializable schedule context for the given user.
    If board_ids is provided, only include those boards; otherwise all boards for the user.
    """
    board_svc = BoardService()
    event_svc = EventService()
    task_svc = TaskService()

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
            "color": board.color,
            "events": [_event_to_context(e) for e in events],
            "tasks": [_task_to_context(t) for t in tasks],
        }
        result.append(board_data)

    return {
        "today": date.today().isoformat(),
        "boards": result,
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


def _task_to_context(t: Task) -> dict[str, Any]:
    return {
        "id": t.id,
        "board_id": t.board_id,
        "name": t.name,
        "description": t.description,
        "progress": t.progress,
        "priority_level": t.priority_level,
        "due_date": t.due_date.isoformat() if hasattr(t.due_date, "isoformat") else str(t.due_date),
        "created_at": t.created_at.isoformat() if hasattr(t.created_at, "isoformat") else str(t.created_at),
    }
