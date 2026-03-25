"""Schedule agent API: OpenAI tools + optional plan_only / execute_plan."""
import json
import logging
import os
from typing import Any

_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)

from aws_lambda_typing import context as lambda_context
from aws_lambda_typing import events as lambda_events
from aws_lambda_typing.responses import APIGatewayProxyResponseV2

from shared.services.schedule_agent_core import run_schedule_agent_llm
from shared.services.schedule_agent_tools import WRITE_TOOL_NAMES, execute_tool
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler


def _require_ascii_api_key(api_key: str) -> None:
    """OpenAI keys are ASCII; stray Unicode in env (e.g. copy-paste) breaks HTTP headers."""
    try:
        api_key.encode("ascii")
    except UnicodeEncodeError as e:
        raise ValueError(
            "OPENAI_API_KEY must be ASCII-only. Replace the key in env.json — "
            "corrupted or non-English characters (often at the spot mentioned in the error) "
            "cause 'ascii' codec errors when calling OpenAI."
        ) from e


def _handle_execute_plan(
    user_id: str,
    execute_plan: list[dict[str, Any]],
) -> APIGatewayProxyResponseV2:
    results: list[dict[str, Any]] = []
    for i, item in enumerate(execute_plan):
        if not isinstance(item, dict):
            results.append({"index": i, "error": "Invalid action: not an object"})
            continue
        tool_name = item.get("tool")
        arguments = item.get("arguments")
        if not tool_name or not isinstance(arguments, dict):
            results.append({"index": i, "error": "Missing tool or arguments"})
            continue
        if tool_name not in WRITE_TOOL_NAMES:
            results.append({"index": i, "error": f"Not allowed in execute_plan: {tool_name}"})
            continue
        try:
            result_str = execute_tool(tool_name, arguments, user_id)
            results.append({"index": i, "tool": tool_name, "result": result_str})
        except Exception as e:
            results.append({"index": i, "tool": tool_name, "error": str(e)})
    applied = sum(1 for r in results if "result" in r)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "reply": f"Applied {applied} of {len(execute_plan)} actions.",
            "results": results,
        }),
    }


@lambda_http_handler
def lambda_handler(
    event: lambda_events.APIGatewayProxyEventV2,
    context: lambda_context.Context,
) -> APIGatewayProxyResponseV2:
    api_key = os.environ.get("OPENAI_API_KEY") or ""
    if not api_key.strip():
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "OPENAI_API_KEY not configured"}),
        }
    try:
        _require_ascii_api_key(api_key)
    except ValueError as ve:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(ve)}),
        }

    path_params = event.get("pathParameters") or {}
    user_id = path_params.get("user_id")
    if not user_id:
        raise BadRequestError()

    req_id = getattr(context, "aws_request_id", "?")
    try:
        rem = int(context.get_remaining_time_in_millis())
    except Exception:
        rem = -1
    _log.info(
        "schedule_agent lambda request_id=%s user_id=%s remaining_ms=%s",
        req_id,
        user_id,
        rem,
    )

    raw_body = event.get("body")
    if not raw_body:
        raise BadRequestError()

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise BadRequestError()
    plan_only = body.get("plan_only") is True
    execute_plan = body.get("execute_plan")

    if execute_plan is not None and isinstance(execute_plan, list):
        _log.info(
            "schedule_agent execute_plan actions=%s request_id=%s",
            len(execute_plan),
            req_id,
        )
        return _handle_execute_plan(user_id, execute_plan)

    message = body.get("message")
    if not message or not isinstance(message, str):
        raise BadRequestError()

    board_ids = body.get("board_ids")
    user_timezone = body.get("timezone")
    user_local_date = body.get("user_local_date")
    if user_timezone is not None and not isinstance(user_timezone, str):
        user_timezone = None
    if user_local_date is not None and not isinstance(user_local_date, str):
        user_local_date = None

    try:
        _log.info(
            "schedule_agent llm path plan_only=%s board_ids=%s request_id=%s",
            plan_only,
            board_ids is not None,
            req_id,
        )
        result = run_schedule_agent_llm(
            user_id,
            message,
            plan_only=plan_only,
            board_ids=board_ids,
            user_timezone=user_timezone,
            user_local_date=user_local_date,
            lambda_context=context,
        )
    except RuntimeError as e:
        if "OPENAI_API_KEY not configured" in str(e):
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "OPENAI_API_KEY not configured"}),
            }
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }

    try:
        body_json = json.dumps(result)
    except (TypeError, ValueError) as e:
        _log.exception("schedule_agent json serialize failed request_id=%s", req_id)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Response not serializable: {e}"}),
        }

    _log.info(
        "schedule_agent ok request_id=%s reply_chars=%s",
        req_id,
        len(result.get("reply") or "") if isinstance(result, dict) else 0,
    )
    return {
        "statusCode": 200,
        "body": body_json,
    }
