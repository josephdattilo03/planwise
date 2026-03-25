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
from openai import OpenAI

from shared.prompts.schedule_agent_prompt import build_schedule_agent_system_prompt
from shared.services.schedule_agent_context import build_schedule_context
from shared.services.schedule_agent_tools import (
    SCHEDULE_AGENT_TOOLS,
    WRITE_TOOL_NAMES,
    enrich_write_arguments,
    execute_tool,
    preview_write_tool,
)
from shared.utils.errors import BadRequestError
from shared.utils.lambda_error_wrapper import lambda_http_handler

MAX_TOOL_ROUNDS = 24


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

    context_data = build_schedule_context(
        user_id,
        board_ids,
        user_timezone=user_timezone,
        user_local_date=user_local_date,
    )
    context_json = json.dumps(context_data, indent=2)
    cal = context_data.get("calendar") or {}
    tz_for_prompt = str(cal.get("timezone") or "UTC")
    system_prompt = build_schedule_agent_system_prompt(
        context_json, timezone=tz_for_prompt, plan_only=plan_only
    )

    client = OpenAI(api_key=api_key)
    messages: list[dict[str, str | list[dict]]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    proposed_actions: list[dict[str, Any]] = []
    final_content = ""

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=SCHEDULE_AGENT_TOOLS,
            tool_choice="auto",
            parallel_tool_calls=True,
        )
        choice = response.choices[0]
        msg = choice.message
        if not msg.content and not (getattr(msg, "tool_calls") and msg.tool_calls):
            break

        if msg.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                if plan_only and name in WRITE_TOOL_NAMES:
                    args = enrich_write_arguments(name, args)
                    proposed_actions.append({"tool": name, "arguments": args})
                    result = preview_write_tool(name, args, user_id)
                else:
                    result = execute_tool(name, args, user_id)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
            continue

        final_content = (msg.content or "").strip()
        break

    if plan_only:
        return {
            "statusCode": 200,
            "body": json.dumps({
                "reply": final_content,
                "proposed_actions": proposed_actions,
            }),
        }
    return {
        "statusCode": 200,
        "body": json.dumps({"reply": final_content}),
    }
