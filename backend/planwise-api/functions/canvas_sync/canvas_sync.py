"""
Canvas sync: fetch courses/assignments, compare fingerprint in DynamoDB, on change
run schedule-agent (plan_only) and return AI briefing for the client.
"""
import hashlib
import json
import os
from typing import Any, Optional

import requests
from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2

from shared.services.integration_state_service import IntegrationStateService
from shared.services.schedule_agent_core import run_schedule_agent_llm
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler

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


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    path_params = event.get("pathParameters") or {}
    user_id = path_params.get("user_id")
    if not user_id:
        raise BadRequestError()

    base = (os.environ.get("CANVAS_API_BASE_URL") or "").strip()
    token = (os.environ.get("CANVAS_ACCESS_TOKEN") or "").strip()
    if not base or not token:
        return {
            "statusCode": 200,
            "body": json.dumps({"skipped": True, "reason": "canvas_not_configured"}),
        }

    try:
        state = IntegrationStateService()
    except RuntimeError:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "INTEGRATION_STATE_TABLE not configured"}),
        }

    prev_fp: Optional[str] = state.get_canvas_fingerprint(user_id)

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

        fp = _fingerprint(courses, by_course)
        if prev_fp is not None and prev_fp == fp:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"skipped": True, "reason": "canvas_unchanged", "fingerprint": fp}
                ),
            }

        digest = _digest(courses, by_course)
        state.put_canvas_fingerprint(user_id, fp)

        message = (
            "The student's Canvas LMS has been refreshed. Here is the current snapshot "
            "of active courses and assignments (JSON). Compare with their existing "
            "Planwise boards, events, and tasks in your context. Recommend a concrete plan: "
            "which tasks or events to add or update, suggested due dates, and how to organize "
            "by course. Prefer plan_only tool proposals the user can confirm.\n\n"
            f"Canvas snapshot:\n{json.dumps({'courses': digest}, indent=2)}"
        )

        try:
            agent_body = run_schedule_agent_llm(
                user_id, message, plan_only=True, board_ids=None
            )
        except RuntimeError as e:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "synced": True,
                        "fingerprint": fp,
                        "digest": digest,
                        "ai_skipped": True,
                        "ai_reason": str(e),
                    }
                ),
            }
        except Exception as e:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "synced": True,
                        "fingerprint": fp,
                        "digest": digest,
                        "ai_skipped": True,
                        "ai_reason": str(e)[:500],
                    }
                ),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "synced": True,
                    "fingerprint": fp,
                    "digest": digest,
                    "ai": {
                        "text": agent_body.get("reply", ""),
                        "proposed_actions": agent_body.get("proposed_actions") or [],
                    },
                }
            ),
        }
    except requests.RequestException as e:
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "skipped": True,
                    "reason": "canvas_error",
                    "detail": str(e)[:500],
                }
            ),
        }
