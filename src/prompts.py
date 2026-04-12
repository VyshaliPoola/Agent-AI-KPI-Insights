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
You are a senior business analyst preparing a short executive performance memo.

Use the KEY FINDINGS first as the highest-priority signals.
Use the remaining structured insights only as supporting evidence.
Do not invent any facts not present in the JSON.

INSIGHTS JSON:
{insights_json}

CHART CONTEXT:
{chart_context}

Write the output in this exact structure:

Performance Summary
- Exactly 3 short bullet points
- Focus on the most important KPI movements only

Key Drivers
- 2 to 3 short bullet points
- Highlight the strongest negative and positive drivers

Risks / Anomalies
- 1 to 2 short bullet points
- Mention only the most important risk or anomaly

Chart Insight
- 1 short bullet point explaining why the chart is useful

Keep the tone executive, concise, and business-focused.
Avoid long paragraphs.
Avoid repeating the same KPI in multiple sections.
"""

RECOMMENDATION_TEMPLATE = """
You are a growth strategy expert.

Based on the analysis below:

{interpretation_text}

Write exactly 3 actionable recommendations.

Rules:
- Each recommendation must be short and specific
- Focus on actions a marketing manager can realistically take
- Do not repeat raw KPI numbers
- Do not restate the same recommendation in different words
- Keep each bullet to one sentence

Return only 3 bullet points.
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