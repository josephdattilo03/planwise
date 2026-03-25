"""Shared LLM loop for the schedule agent (used by API Lambda and Canvas sync Lambda)."""
import json
import os
from typing import Any

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

MAX_TOOL_ROUNDS = 24


def run_schedule_agent_llm(
    user_id: str,
    message: str,
    *,
    plan_only: bool,
    board_ids: list[Any] | None = None,
    user_timezone: str | None = None,
    user_local_date: str | None = None,
) -> dict[str, Any]:
    """
    Run one schedule-agent conversation turn. Returns a dict suitable for JSON response body:
    plan_only True -> { "reply": str, "proposed_actions": list }
    plan_only False -> { "reply": str }
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    normalized_board_ids: list[str] | None = None
    if board_ids is not None:
        if not isinstance(board_ids, list):
            normalized_board_ids = None
        else:
            normalized_board_ids = [str(b) for b in board_ids]

    context_data = build_schedule_context(
        user_id,
        normalized_board_ids,
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
            "reply": final_content,
            "proposed_actions": proposed_actions,
        }
    return {"reply": final_content}
