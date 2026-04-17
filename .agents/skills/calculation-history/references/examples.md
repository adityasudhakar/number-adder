# Calculation History Examples

Use these examples only when you need clarification on tool choice or phrasing.

## Aggregate questions

Question: "What's the average of my last 10 calculations?"
- Tool: `get_calculation_stats(limit=10)`
- Good answer shape: "The average result across your last N calculations is X."

Question: "What's the total of my last 5 multiplications?"
- Tool: `get_calculation_stats(limit=5, operation="multiply")`
- Good answer shape: "The total of your last N multiplication calculations is X."

Question: "What's my most common operation?"
- Tool: `get_calculation_stats(limit=20)` if no explicit window is given
- Good answer shape: "Across your last N calculations, your most common operation is add/multiply."

## Lookup questions

Question: "What was my most recent calculation?"
- Tool: `get_recent_calculations(limit=1)`
- Good answer shape: "Your most recent calculation was A + B = C."

Question: "What was my most recent multiplication?"
- Tool: `get_recent_calculations(limit=1, operation="multiply")`
- Good answer shape: "Your most recent multiplication was A x B = C."

Question: "Show my last 3 additions."
- Tool: `get_recent_calculations(limit=3, operation="add")`
- Good answer shape: concise list or summary grounded only in returned records

## Empty-history handling

Question: "What's the average of my last 10 calculations?"
- If zero records: "You don't have any calculations yet."

Question: "What was my most recent multiplication?"
- If zero matching records: "You don't have any multiply calculations yet."

## Out-of-scope handling

Question: "Why is my bill higher this month?"
- Do not use this skill's tools.
- Answer that you can help with saved calculations and operations only.
