import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
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

def _load_lc_model():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found.")

    model_name = os.getenv("GEMINI_MODEL")
    if not model_name:
        raise ValueError("GEMINI_MODEL not configured.")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0
    )
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

    lc_model = _load_lc_model()

    interpretation_prompt = PromptTemplate(
        template=INTERPRETATION_TEMPLATE,
        input_variables=["insights_json", "chart_context"]
    )

    interpretation_chain = interpretation_prompt | lc_model | StrOutputParser()

    interpretation_text = interpretation_chain.invoke({
        "insights_json": json.dumps(insights, indent=2),
        "chart_context": chart_context,
    })

    recommendation_prompt = PromptTemplate(
        template=RECOMMENDATION_TEMPLATE,
        input_variables=["interpretation_text"]
    )

    recommendation_chain = recommendation_prompt | lc_model | StrOutputParser()

    recommendation_text = recommendation_chain.invoke({
        "interpretation_text": interpretation_text
    })

    final_memo = f"""
EXECUTIVE PERFORMANCE MEMO

{interpretation_text}

Recommended Actions
{recommendation_text}
"""
    return final_memo