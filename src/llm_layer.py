import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

from src.prompts import (
    CHART_RECOMMENDATION_TEMPLATE,
    INTERPRETATION_TEMPLATE,
    RECOMMENDATION_TEMPLATE,
)


def _load_model():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found.")

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL")
    if not model_name:
        raise ValueError("GEMINI_MODEL not configured.")

    return genai.GenerativeModel(model_name)


def _extract_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise
        return json.loads(text[start:end + 1])


def generate_chart_spec(insights: dict) -> dict:
    model = _load_model()
    prompt = CHART_RECOMMENDATION_TEMPLATE.format(
        insights_json=json.dumps(insights, indent=2)
    )
    response = model.generate_content(prompt)
    spec = _extract_json_object(response.text)

    if not isinstance(spec, dict):
        raise ValueError("Chart recommendation did not return a JSON object.")

    spec.setdefault("color", None)
    if "chart_type" not in spec or "x" not in spec or "y" not in spec or "title" not in spec or "question" not in spec:
        raise ValueError("Chart recommendation JSON is missing required keys.")

    return spec


def generate_exec_memo(insights: dict, chart_spec: dict | None = None) -> str:
    try:
        model = _load_model()
    except ValueError as e:
        return f"⚠️ {e}"

    chart_context = "No chart recommendation available."
    if chart_spec is not None:
        chart_context = (
            f"Recommended chart: {chart_spec.get('title')}"
            f" (type: {chart_spec.get('chart_type')}, x: {chart_spec.get('x')}, y: {chart_spec.get('y')}, "
            f"color: {chart_spec.get('color') or 'none'}). "
            f"This chart helps answer: {chart_spec.get('question')}"
        )

    interpretation_prompt = INTERPRETATION_TEMPLATE.format(
        insights_json=json.dumps(insights, indent=2),
        chart_context=chart_context,
    )
    interpretation_response = model.generate_content(interpretation_prompt)
    interpretation_text = interpretation_response.text

    recommendation_prompt = RECOMMENDATION_TEMPLATE.format(
        interpretation_text=interpretation_text
    )
    recommendation_response = model.generate_content(recommendation_prompt)
    recommendation_text = recommendation_response.text

    final_memo = f"""
EXECUTIVE PERFORMANCE MEMO

Chart recommendation:
{chart_context}

🔹 Performance Analysis:
{interpretation_text}

🔹 Recommended Actions:
{recommendation_text}
"""
    return final_memo
