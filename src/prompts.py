EXEC_MEMO_TEMPLATE = """
You are a senior Business Analyst writing a weekly executive performance memo.

You must ONLY use the facts provided in the INSIGHTS JSON below.
Do not invent numbers, causes, or events.

Write the memo in this exact structure:

1) Performance Summary (3 bullet points max)
2) What Changed (top 3 KPI WoW % changes)
3) Key Drivers (top negative and positive revenue drivers)
4) Risks / Anomalies (mention anomalies if any)
5) Actionable Recommendations (exactly 3 bullets, realistic and specific)

INSIGHTS JSON:
{insights_json}
"""


INTERPRETATION_TEMPLATE = """
You are a senior business analyst.

Based ONLY on the insights below:

{insights_json}

Explain:

1. What changed in performance
2. Why it likely changed (based on drivers)
3. Key risks observed

Write clearly and concisely for executives.
"""

RECOMMENDATION_TEMPLATE = """
You are a growth strategy expert.

Based on this analysis:

{interpretation_text}

Provide:

1. Three actionable recommendations
2. Keep them practical and business-focused
3. Avoid repeating numbers

Write in bullet points.
"""