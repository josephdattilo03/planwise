"""Read-only Canvas LMS: courses and assignments (shared by canvas_sync and schedule agent tools)."""
from __future__ import annotations

import hashlib
import os
from typing import Any, Optional

import requests

CANVAS_TIMEOUT = (5, 25)


def _canvas_get(base: str, token: str, path: str) -> Any:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=CANVAS_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _fingerprint(courses: list[dict], by_course: dict[int, list[dict]]) -> str:
    rows: list[str] = []
    for c in courses:
        cid = int(c["id"])
        for a in by_course.get(cid, []):
            rows.append(
                f"{cid}:{a.get('id')}:{a.get('updated_at') or ''}:"
                f"{a.get('due_at') or ''}:{a.get('name') or ''}"
            )
    rows.sort()
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def _digest(courses: list[dict], by_course: dict[int, list[dict]]) -> list[dict]:
    out: list[dict] = []
    for c in courses:
        cid = int(c["id"])
        name = c.get("name") or c.get("course_code") or f"Course {cid}"
        assigns = by_course.get(cid, [])
        out.append(
            {
                "course_id": cid,
                "name": name,
                "assignments": [
                    {
                        "id": x.get("id"),
                        "name": x.get("name"),
                        "due_at": x.get("due_at"),
                        "updated_at": x.get("updated_at"),
                        "points_possible": x.get("points_possible"),
                        "url": x.get("html_url"),
                    }
                    for x in assigns
                ],
            }
        )
    return out


def fetch_canvas_snapshot() -> dict[str, Any]:
    """
    Load active courses and assignments from Canvas.

    Returns:
        {"ok": True, "digest": [...], "fingerprint": str, "course_count": int, "assignment_count": int}
        {"ok": False, "reason": str, "message": str}
    """
    base = (os.environ.get("CANVAS_API_BASE_URL") or "").strip()
    token = (os.environ.get("CANVAS_ACCESS_TOKEN") or "").strip()
    if not base or not token:
        return {
            "ok": False,
            "reason": "canvas_not_configured",
            "message": "Canvas API is not configured (CANVAS_API_BASE_URL / CANVAS_ACCESS_TOKEN).",
        }
    try:
        raw_courses = _canvas_get(
            base, token, "/api/v1/courses?enrollment_state=active&per_page=100"
        )
        courses = raw_courses if isinstance(raw_courses, list) else []
        by_course: dict[int, list[dict]] = {}
        for course in courses:
            cid = int(course["id"])
            try:
                raw_a = _canvas_get(
                    base, token, f"/api/v1/courses/{cid}/assignments?per_page=100"
                )
                by_course[cid] = raw_a if isinstance(raw_a, list) else []
            except requests.RequestException:
                by_course[cid] = []

        digest = _digest(courses, by_course)
        fp = _fingerprint(courses, by_course)
        n_assignments = sum(len(v) for v in by_course.values())
        return {
            "ok": True,
            "digest": digest,
            "fingerprint": fp,
            "course_count": len(courses),
            "assignment_count": n_assignments,
        }
    except requests.RequestException as e:
        return {
            "ok": False,
            "reason": "canvas_error",
            "message": str(e)[:500],
        }
