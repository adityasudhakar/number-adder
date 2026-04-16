"""Chat agent orchestration for answering questions about user calculations."""

from __future__ import annotations

import json
import os
import re
from statistics import mean
from typing import Any

import httpx

from number_adder import database as db

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CHAT_AGENT_MODEL = os.environ.get("CHAT_AGENT_MODEL", "gpt-4.1-mini")
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = """
You answer questions about a user's Number Adder calculation history.

Rules:
- Only answer questions grounded in the user's own calculation data.
- Use tools when data is needed.
- Be concise and explicit about what window you used, for example "your last 10 calculations".
- If there are not enough calculations, say exactly how many exist.
- If the user asks for something outside calculation history, say you can help with their saved calculations and operations only.
""".strip()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_calculations",
            "description": "Fetch the user's most recent calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent calculations to fetch.",
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "operation": {
                        "type": "string",
                        "description": "Optional operation filter.",
                        "enum": ["add", "multiply"],
                    },
                },
                "required": ["limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_calculation_stats",
            "description": "Compute summary statistics over the user's recent calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent calculations to analyze.",
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "operation": {
                        "type": "string",
                        "description": "Optional operation filter.",
                        "enum": ["add", "multiply"],
                    },
                },
                "required": ["limit"],
                "additionalProperties": False,
            },
        },
    },
]


def answer_question(user_id: int, message: str) -> dict[str, Any]:
    """Answer a user's history question using OpenAI tool calling when configured."""
    normalized = message.strip()
    if not normalized:
        return {"answer": "Ask a question about your calculation history.", "source": "local"}

    if not OPENAI_API_KEY:
        return {"answer": _answer_with_rules(user_id, normalized), "source": "local"}

    try:
        answer = _answer_with_openai(user_id, normalized)
        return {"answer": answer, "source": "openai"}
    except Exception:
        # Keep the chat feature usable even if the upstream model call fails.
        return {"answer": _answer_with_rules(user_id, normalized), "source": "local"}


def _answer_with_openai(user_id: int, message: str) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        for _ in range(4):
            response = client.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers=headers,
                json={
                    "model": CHAT_AGENT_MODEL,
                    "messages": messages,
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            payload = response.json()
            assistant_message = payload["choices"][0]["message"]
            tool_calls = assistant_message.get("tool_calls") or []

            if not tool_calls:
                content = assistant_message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                return "I couldn't produce an answer from your calculation history."

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.get("content") or "",
                    "tool_calls": tool_calls,
                }
            )

            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                raw_arguments = tool_call["function"].get("arguments") or "{}"
                arguments = json.loads(raw_arguments)
                result = _run_tool(user_id, function_name, arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result),
                    }
                )

    return "I couldn't complete that request from your calculation history."


def _run_tool(user_id: int, function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if function_name == "get_recent_calculations":
        limit = _normalize_limit(arguments.get("limit", 10))
        operation = _normalize_operation(arguments.get("operation"))
        calculations = db.get_recent_calculations(user_id, limit=limit, operation=operation)
        return {
            "count": len(calculations),
            "limit_requested": limit,
            "operation": operation,
            "calculations": calculations,
        }

    if function_name == "get_calculation_stats":
        limit = _normalize_limit(arguments.get("limit", 10))
        operation = _normalize_operation(arguments.get("operation"))
        calculations = db.get_recent_calculations(user_id, limit=limit, operation=operation)
        return _build_stats_payload(calculations, limit, operation)

    raise ValueError(f"Unknown tool: {function_name}")


def _build_stats_payload(
    calculations: list[dict[str, Any]],
    limit: int,
    operation: str | None,
) -> dict[str, Any]:
    if not calculations:
        return {
            "count": 0,
            "limit_requested": limit,
            "operation": operation,
            "average_result": None,
            "sum_result": 0.0,
            "most_common_operation": None,
            "latest_calculation": None,
        }

    results = [float(item["result"]) for item in calculations]
    operation_counts: dict[str, int] = {}
    for item in calculations:
        operation_counts[item["operation"]] = operation_counts.get(item["operation"], 0) + 1

    most_common_operation = max(operation_counts.items(), key=lambda pair: pair[1])[0]
    return {
        "count": len(calculations),
        "limit_requested": limit,
        "operation": operation,
        "average_result": mean(results),
        "sum_result": sum(results),
        "most_common_operation": most_common_operation,
        "latest_calculation": calculations[0],
    }


def _normalize_limit(value: Any) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return 10
    return max(1, min(limit, 50))


def _normalize_operation(value: Any) -> str | None:
    if value in {"add", "multiply"}:
        return str(value)
    return None


def _answer_with_rules(user_id: int, message: str) -> str:
    lowered = message.lower()

    if any(token in lowered for token in ("average", "avg", "mean")):
        return _answer_average(user_id, lowered)

    if "most recent" in lowered or "latest" in lowered:
        return _answer_latest(user_id, lowered)

    if any(token in lowered for token in ("sum", "total")):
        return _answer_sum(user_id, lowered)

    if "most common operation" in lowered:
        stats = _build_stats_payload(db.get_recent_calculations(user_id, limit=20), 20, None)
        if not stats["count"]:
            return "You don't have any calculations yet."
        return (
            f"Your most common operation across your last {stats['count']} calculations "
            f"is {stats['most_common_operation']}."
        )

    return (
        "I can help with your calculation history. Try asking for your average, total, "
        "most recent calculation, or most common operation."
    )


def _answer_average(user_id: int, message: str) -> str:
    limit = _extract_limit(message)
    operation = _extract_operation(message)
    calculations = db.get_recent_calculations(user_id, limit=limit, operation=operation)
    if not calculations:
        return _no_results_message(operation)

    average_result = mean(float(item["result"]) for item in calculations)
    op_phrase = f" {operation}" if operation else ""
    return (
        f"The average result across your last {len(calculations)}{op_phrase} calculations "
        f"is {average_result:.2f}."
    )


def _answer_sum(user_id: int, message: str) -> str:
    limit = _extract_limit(message)
    operation = _extract_operation(message)
    calculations = db.get_recent_calculations(user_id, limit=limit, operation=operation)
    if not calculations:
        return _no_results_message(operation)

    total = sum(float(item["result"]) for item in calculations)
    op_phrase = f" {operation}" if operation else ""
    return (
        f"The total of your last {len(calculations)}{op_phrase} calculations is {total:.2f}."
    )


def _answer_latest(user_id: int, message: str) -> str:
    operation = _extract_operation(message)
    calculations = db.get_recent_calculations(user_id, limit=1, operation=operation)
    if not calculations:
        return _no_results_message(operation)

    item = calculations[0]
    symbol = "+" if item["operation"] == "add" else "x"
    return (
        f"Your most recent {item['operation']} calculation was "
        f"{item['num_a']} {symbol} {item['num_b']} = {item['result']}."
    )


def _extract_limit(message: str) -> int:
    match = re.search(r"last\s+(\d+)", message)
    if not match:
        return 10
    return _normalize_limit(match.group(1))


def _extract_operation(message: str) -> str | None:
    if "multiplication" in message or "multiply" in message:
        return "multiply"
    if "addition" in message or "add" in message:
        return "add"
    return None


def _no_results_message(operation: str | None) -> str:
    if operation:
        return f"You don't have any {operation} calculations yet."
    return "You don't have any calculations yet."
