import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

from src.prompts import (
    EXEC_MEMO_TEMPLATE,
    INTERPRETATION_TEMPLATE,
    RECOMMENDATION_TEMPLATE
)


def generate_exec_memo(insights: dict) -> str:

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        return "⚠️ GOOGLE_API_KEY not found."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL"))

    # STEP 1 — Interpretation Agent
    interpretation_prompt = INTERPRETATION_TEMPLATE.format(
        insights_json=json.dumps(insights, indent=2)
    )

    interpretation_response = model.generate_content(interpretation_prompt)
    interpretation_text = interpretation_response.text

    # STEP 2 — Recommendation Agent
    recommendation_prompt = RECOMMENDATION_TEMPLATE.format(
        interpretation_text=interpretation_text
    )

    recommendation_response = model.generate_content(recommendation_prompt)
    recommendation_text = recommendation_response.text

    # FINAL OUTPUT
    final_memo = f"""
EXECUTIVE PERFORMANCE MEMO

🔹 Performance Analysis:
{interpretation_text}

🔹 Recommended Actions:
{recommendation_text}
"""

    return final_memo