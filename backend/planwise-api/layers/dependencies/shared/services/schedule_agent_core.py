"""LLM tool loop for the schedule agent (API Lambda + Canvas sync)."""
import json
import logging
import os
import time
from typing import Any, Optional

from openai import OpenAI

from shared.prompts.schedule_agent_prompt import build_schedule_agent_system_prompt
from shared.services.schedule_agent_context import build_schedule_context
from shared.services.schedule_agent_tools import (
    SCHEDULE_AGENT_TOOLS,
    WRITE_TOOL_NAMES,
    PlanPreviewRegistry,
    execute_tool,
    normalize_tool_arguments,
    preview_write_tool,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_TOOL_ROUNDS = 64
MAX_TOOL_RESULT_CHARS = 32000


def _min_remaining_ms() -> int:
    raw = os.environ.get("SCHEDULE_AGENT_MIN_REMAINING_MS", "25000")
    try:
        return max(5_000, int(raw))
    except ValueError:
        return 25_000


def _truncate_tool_content(text: str) -> str:
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    return text[: MAX_TOOL_RESULT_CHARS - 24] + "\n… [truncated]"


def _remaining_ms(lambda_context: Any) -> Optional[int]:
    if lambda_context is None:
        return None
    try:
        return int(lambda_context.get_remaining_time_in_millis())
    except Exception:
        return None


def run_schedule_agent_llm(
    user_id: str,
    message: str,
    *,
    plan_only: bool,
    board_ids: list[Any] | None = None,
    user_timezone: str | None = None,
    user_local_date: str | None = None,
    lambda_context: Any = None,
) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    t_start = time.perf_counter()
    normalized_board_ids: list[str] | None = (
        [str(b) for b in board_ids] if isinstance(board_ids, list) else None
    )
    context_data = build_schedule_context(
        user_id,
        normalized_board_ids,
        user_timezone=user_timezone,
        user_local_date=user_local_date,
    )
    context_json = json.dumps(context_data, indent=2)
    logger.info(
        "schedule_agent start user_id=%s plan_only=%s msg_chars=%s ctx_chars=%s remaining_ms=%s",
        user_id,
        plan_only,
        len(message),
        len(context_json),
        _remaining_ms(lambda_context),
    )
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
    preview_registry: Optional[PlanPreviewRegistry] = (
        PlanPreviewRegistry() if plan_only else None
    )

    for round_idx in range(MAX_TOOL_ROUNDS):
        rem = _remaining_ms(lambda_context)
        budget = _min_remaining_ms()
        if rem is not None and rem < budget:
            note = (
                " Stopped early: not enough execution time left to safely continue tool rounds. "
                "Try a shorter request or split it into multiple steps."
            )
            logger.warning(
                "schedule_agent deadline stop round=%s remaining_ms=%s budget_ms=%s elapsed_s=%.1f",
                round_idx,
                rem,
                budget,
                time.perf_counter() - t_start,
            )
            if plan_only:
                return {
                    "reply": (final_content or "") + note,
                    "proposed_actions": proposed_actions,
                    "stopped_early": True,
                    "reason": "lambda_time_budget",
                }
            return {
                "reply": (final_content or "") + note,
                "stopped_early": True,
                "reason": "lambda_time_budget",
            }

        t_llm = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=SCHEDULE_AGENT_TOOLS,
                tool_choice="auto",
                parallel_tool_calls=True,
            )
        except Exception as e:
            logger.exception("schedule_agent OpenAI error at round=%s", round_idx)
            err = f"OpenAI request failed: {e!s}"
            if plan_only:
                return {"reply": err, "proposed_actions": proposed_actions}
            return {"reply": err}

        llm_s = time.perf_counter() - t_llm
        if not response.choices:
            logger.warning("schedule_agent empty choices round=%s", round_idx)
            break
        choice = response.choices[0]
        msg = choice.message
        tc_list = getattr(msg, "tool_calls", None) or []
        logger.info(
            "schedule_agent round=%s/%s openai_s=%.2f tools=%s rem_ms=%s",
            round_idx + 1,
            MAX_TOOL_ROUNDS,
            llm_s,
            len(tc_list),
            rem if rem is not None else "n/a",
        )

        if not msg.content and not tc_list:
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
                try:
                    args = normalize_tool_arguments(
                        name, args, user_id, preview_registry
                    )
                    if plan_only and name in WRITE_TOOL_NAMES:
                        result = preview_write_tool(
                            name, args, user_id, preview_registry
                        )
                        proposed_actions.append({"tool": name, "arguments": args})
                    else:
                        result = execute_tool(name, args, user_id)
                except Exception as e:
                    err_msg = str(e).strip() or type(e).__name__
                    logger.warning("schedule_agent tool error tool=%s err=%s", name, err_msg)
                    result = json.dumps(
                        {"error": err_msg, "hint": "Check required fields for this tool."}
                    )
                result = _truncate_tool_content(
                    result if isinstance(result, str) else str(result)
                )
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

    logger.info(
        "schedule_agent finished elapsed_s=%.2f proposed_actions=%s reply_chars=%s",
        time.perf_counter() - t_start,
        len(proposed_actions),
        len(final_content),
    )

    if plan_only:
        return {
            "reply": final_content,
            "proposed_actions": proposed_actions,
        }
    return {"reply": final_content}
