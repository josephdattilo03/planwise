"""
Schedule agent Lambda: accepts a user message and optional board_ids,
uses OpenAI with tools to read/update events and tasks, returns natural language reply.
Supports plan_only (return proposed_actions for confirmation) and execute_plan (apply proposed_actions).
"""
import json
import os
from typing import Any

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
    """Apply a list of proposed actions; no LLM call."""
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

    if not event.get("body"):
        raise BadRequestError()

    body = json.loads(event.get("body") or "")
    plan_only = body.get("plan_only") is True
    execute_plan = body.get("execute_plan")

    # Execute-plan flow: apply a previously returned proposed_actions list (no LLM call).
    if execute_plan is not None and isinstance(execute_plan, list):
        return _handle_execute_plan(user_id, execute_plan)

    message = body.get("message")
    if not message or not isinstance(message, str):
        raise BadRequestError()

    board_ids = body.get("board_ids")  # optional list of board ids to scope context
    user_timezone = body.get("timezone")
    user_local_date = body.get("user_local_date")
    if user_timezone is not None and not isinstance(user_timezone, str):
        user_timezone = None
    if user_local_date is not None and not isinstance(user_local_date, str):
        user_local_date = None

    try:
        result = run_schedule_agent_llm(
            user_id,
            message,
            plan_only=plan_only,
            board_ids=board_ids,
            user_timezone=user_timezone,
            user_local_date=user_local_date,
        )
    except RuntimeError:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "OPENAI_API_KEY not configured"}),
        }

    return {
        "statusCode": 200,
        "body": json.dumps(result),
    }
