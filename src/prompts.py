EXEC_MEMO_TEMPLATE = """
You are a senior Business Analyst writing an executive performance memo.

Use ONLY the facts provided in the INSIGHTS JSON below.
Do not invent numbers, causes, or events.
Do not add anything not supported by the structured insights.

Write the memo in this exact structure:

1) Performance Summary (3 bullet points max)
2) What Changed (top 3 KPI WoW % changes)
3) Likely Drivers (explain the most important positive and negative drivers)
4) Chart Insight (if a chart recommendation is available, explain why it helps clarify the issue)
5) Risks / Anomalies (mention anomalies if any)
6) Actionable Recommendations (exactly 3 bullets, realistic and specific)

INSIGHTS JSON:
{insights_json}

CHART CONTEXT:
{chart_context}
"""


INTERPRETATION_TEMPLATE = """
You are a senior business analyst.

Use the KEY FINDINGS first as the highest-priority signals.
Then use the remaining structured insights only as supporting evidence.

INSIGHTS JSON:
{insights_json}

CHART CONTEXT:
{chart_context}

Explain:
1. What changed in performance
2. Why it likely changed
3. Key risks observed
4. What the chart helps clarify

Write clearly and concisely for executives.
Use short bullet points.
Do not invent any facts not present in the JSON.
"""

RECOMMENDATION_TEMPLATE = """
You are a growth strategy expert.

Based on this analysis:

{interpretation_text}

Provide:
1. Exactly three actionable recommendations
2. Keep them practical, business-focused, and easy to implement
3. Avoid repeating raw numbers from the analysis

Write in bullet points only.
"""


CHART_RECOMMENDATION_TEMPLATE = """
You are a marketing analytics expert.

Based ONLY on the insights below, recommend the most useful visualization to explain the business issue.
Return ONLY a valid JSON object with these keys:
- chart_type: one of ["line", "bar", "scatter", "box", "histogram"]
- x: field name
- y: field name
- color: optional grouping field or null
- title: short chart title
- question: the business question this chart answers

Do not invent fields that are not present in the available fields list.
Do not include any markdown, explanation, or text outside the JSON object.

Available fields are provided in the insights JSON.

INSIGHTS JSON:
{insights_json}
"""