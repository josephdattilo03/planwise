"""
Canvas sync: fetch courses/assignments, compare fingerprint in DynamoDB, on change
run schedule-agent (plan_only) and return AI briefing for the client.
"""
import json
import logging
import os
from typing import Any, Optional

_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)
from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2

from shared.services.canvas_assignments_service import fetch_canvas_snapshot
from shared.services.integration_state_service import IntegrationStateService
from shared.services.schedule_agent_core import run_schedule_agent_llm
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler


def _norm_assignment(a: dict) -> dict[str, Any]:
    return {
        "name": a.get("name"),
        "due_at": a.get("due_at"),
        "updated_at": a.get("updated_at"),
        "points_possible": a.get("points_possible"),
        "url": a.get("html_url"),
    }


def _index_digest(digest: list[dict]) -> dict[tuple[int, int], dict[str, Any]]:
    out: dict[tuple[int, int], dict[str, Any]] = {}
    for c in digest:
        cid = int(c["course_id"])
        for a in c.get("assignments") or []:
            aid = a.get("id")
            if aid is None:
                continue
            out[(cid, int(aid))] = _norm_assignment(a)
    return out


def _diff_digest(
    prev_digest: Optional[list[dict]],
    curr_digest: list[dict],
    had_prev_fingerprint: bool,
) -> dict[str, Any]:
    if prev_digest is None:
        if had_prev_fingerprint:
            return {
                "comparison": "no_stored_digest",
                "note": (
                    "Canvas data changed since last sync, but no prior assignment snapshot "
                    "was stored for comparison. Summarize upcoming work and suggest tasks "
                    "or calendar events from the full assignment list."
                ),
            }
        return {
            "comparison": "first_sync",
            "note": "First Canvas sync for this account.",
        }

    prev_m = _index_digest(prev_digest)
    new_assignments: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []

    for c in curr_digest:
        cid = int(c["course_id"])
        cname = c.get("name") or f"Course {cid}"
        for a in c.get("assignments") or []:
            aid = a.get("id")
            if aid is None:
                continue
            key = (cid, int(aid))
            snap = _norm_assignment(a)
            if key not in prev_m:
                new_assignments.append(
                    {
                        "course_id": cid,
                        "course_name": cname,
                        "assignment": a,
                    }
                )
            elif prev_m[key] != snap:
                changed.append(
                    {
                        "course_id": cid,
                        "course_name": cname,
                        "before": prev_m[key],
                        "after": a,
                    }
                )

    return {
        "comparison": "diff",
        "new_assignments": new_assignments,
        "changed_assignments": changed,
    }


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    path_params = event.get("pathParameters") or {}
    user_id = path_params.get("user_id")
    if not user_id:
        raise BadRequestError()

    request_id = (event.get("requestContext") or {}).get("requestId") or ""
    aws_req = getattr(context, "aws_request_id", None) or "-"
    _log.info(
        "[canvas_sync] begin user_id=%s api_request_id=%s aws_request_id=%s",
        user_id,
        request_id or "-",
        aws_req,
    )

    base = (os.environ.get("CANVAS_API_BASE_URL") or "").strip()
    token = (os.environ.get("CANVAS_ACCESS_TOKEN") or "").strip()
    if not base or not token:
        _log.info("[canvas_sync] skip reason=canvas_not_configured user_id=%s", user_id)
        return {
            "statusCode": 200,
            "body": json.dumps({"skipped": True, "reason": "canvas_not_configured"}),
        }

    try:
        state = IntegrationStateService()
    except RuntimeError:
        _log.exception("[canvas_sync] INTEGRATION_STATE_TABLE not configured")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "INTEGRATION_STATE_TABLE not configured"}),
        }

    prev_fp: Optional[str]
    prev_digest: Optional[list[dict]]
    prev_fp, prev_digest = state.get_canvas_state(user_id)
    _log.debug(
        "[canvas_sync] loaded state prev_fp=%s had_prev_digest=%s",
        (prev_fp[:16] + "...") if prev_fp and len(prev_fp) > 16 else prev_fp,
        prev_digest is not None,
    )

    _log.debug("[canvas_sync] fetching Canvas courses")
    snap = fetch_canvas_snapshot()
    if not snap.get("ok"):
        reason = snap.get("reason", "error")
        if reason == "canvas_not_configured":
            _log.info("[canvas_sync] skip reason=canvas_not_configured user_id=%s", user_id)
            return {
                "statusCode": 200,
                "body": json.dumps({"skipped": True, "reason": "canvas_not_configured"}),
            }
        _log.warning(
            "[canvas_sync] canvas_error user_id=%s err=%s",
            user_id,
            snap.get("message"),
        )
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "skipped": True,
                    "reason": "canvas_error",
                    "detail": snap.get("message", "")[:500],
                }
            ),
        }

    digest = snap["digest"]
    fp = snap["fingerprint"]
    n_assignments = snap["assignment_count"]
    courses_count = snap["course_count"]
    _log.info(
        "[canvas_sync] canvas fetched courses=%s assignments=%s",
        courses_count,
        n_assignments,
    )
    _log.debug(
        "[canvas_sync] fingerprint new_fp=%s",
        (fp[:16] + "...") if len(fp) > 16 else fp,
    )

    if prev_fp is not None and prev_fp == fp:
        _log.info(
            "[canvas_sync] skip reason=canvas_unchanged user_id=%s fp=%s...",
            user_id,
            fp[:12],
        )
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"skipped": True, "reason": "canvas_unchanged", "fingerprint": fp}
            ),
        }

    diff = _diff_digest(prev_digest, digest, prev_fp is not None)
    cmp = diff.get("comparison")
    if cmp == "diff":
        _log.info(
            "[canvas_sync] diff new=%s changed=%s",
            len(diff.get("new_assignments") or []),
            len(diff.get("changed_assignments") or []),
        )
    else:
        _log.info("[canvas_sync] diff comparison=%s", cmp)
    state.put_canvas_state(user_id, fp, digest)
    _log.debug("[canvas_sync] persisted integration state")

    message = (
        "The user just opened Planwise and Canvas was synced. Their Canvas data "
        "changed since the last sync (new or updated assignments). "
        "Greet them briefly and call out what is new or changed using the diff below. "
        "Then suggest concrete next steps using plan_only tools they can confirm: "
        "e.g. create_task for work items, create_event for due dates or study blocks, "
        "aligned with their boards and workspace context. "
        "If the diff lists new assignments, treat those as the priority.\n\n"
        f"Canvas change summary (JSON):\n{json.dumps(diff, indent=2)}\n\n"
        f"Full Canvas snapshot (JSON):\n{json.dumps({'courses': digest}, indent=2)}"
    )

    _log.info("[canvas_sync] invoking schedule_agent plan_only user_id=%s", user_id)
    try:
        agent_body = run_schedule_agent_llm(
            user_id, message, plan_only=True, board_ids=None
        )
    except RuntimeError as e:
        _log.warning(
            "[canvas_sync] ai skipped RuntimeError user_id=%s err=%s",
            user_id,
            e,
        )
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
        _log.exception(
            "[canvas_sync] ai skipped unexpected user_id=%s",
            user_id,
        )
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

    n_actions = len(agent_body.get("proposed_actions") or [])
    reply_len = len((agent_body.get("reply") or ""))
    _log.info(
        "[canvas_sync] success user_id=%s reply_chars=%s proposed_actions=%s",
        user_id,
        reply_len,
        n_actions,
    )
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
