---
name: calculation-history
description: Use when answering questions about a Number Adder user's saved calculation history, including averages, totals, latest calculations, operation-specific lookups, and most common operations. Prefer the existing calculation-history tools instead of SQL or free-form guesses.
---

# Calculation History

Use this skill for questions about a user's saved Number Adder calculations.

Scope:
- Questions about recent calculations
- Aggregate questions over recent calculations
- Operation-filtered questions for `add` or `multiply`
- Safe explanations grounded only in the authenticated user's saved history

Do not use this skill for:
- Authentication, billing, or account-management questions
- Arbitrary SQL generation
- Questions that require data outside saved calculations

## Available tools

1. `get_recent_calculations(limit, operation?)`
Returns the authenticated user's most recent calculations, optionally filtered by operation.

Use for:
- "What was my most recent calculation?"
- "What was my most recent multiplication?"
- "Show my last 5 additions."

2. `get_calculation_stats(limit, operation?)`
Returns summary statistics over the authenticated user's recent calculations.

Use for:
- "What's the average of my last 10 calculations?"
- "What's the total of my last 5 multiplications?"
- "What's my most common operation?"

## Tool selection

- For average, total, sum, count-like summary, or most-common-operation questions, prefer `get_calculation_stats`.
- For latest-item or list-style questions, prefer `get_recent_calculations`.
- If the user names an operation such as addition or multiplication, pass `operation`.
- If the user does not specify a window, default to the tool's default limit.
- Never invent a `user_id` or ask the model to choose one. The backend scopes results from auth.

## Response rules

- Answer only from tool results.
- Mention the window used, for example "your last 10 calculations".
- If fewer records exist than requested, say exactly how many were available.
- If there are no matching calculations, say so plainly.
- If the user asks for something outside saved calculation history, say you can help with saved calculations and operations only.

## Safety rules

- Do not use SQL when these tools can answer the question.
- Do not infer hidden data from missing results.
- Do not mention or expose other users' data.

## Examples

User: "What's the average of my last 10 calculations?"
- Call `get_calculation_stats(limit=10)`
- Answer with the computed average and the actual count returned

User: "What was my most recent multiplication?"
- Call `get_recent_calculations(limit=1, operation="multiply")`
- Answer with the exact expression and result if one exists

User: "What's my most common operation?"
- Call `get_calculation_stats(limit=20)` unless the user specified a different window
- Answer with the most common operation and the window used

For more example prompts and expected tool choices, read `references/examples.md`.
