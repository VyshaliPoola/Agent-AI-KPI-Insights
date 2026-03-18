from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd


# --- 1) Define required columns for Marketing Performance ---
REQUIRED_COLUMNS = [
    "date",        # can be week string or actual date
    "channel",
    "spend",
    "impressions",
    "clicks",
    "conversions",
    "revenue",
]


@dataclass
class IngestionResult:
    df: pd.DataFrame
    used_dummy: bool
    schema_ok: bool
    missing_columns: List[str]


def load_dummy_marketing_data() -> pd.DataFrame:
    """
    Small dummy dataset so the pipeline runs even without a CSV.
    This will be replaced later by synthetic data generation.
    """
    data = [
        {"date": "2026-W01", "channel": "Google", "spend": 12000, "impressions": 320000, "clicks": 8000, "conversions": 420, "revenue": 28000},
        {"date": "2026-W01", "channel": "Meta",   "spend": 15000, "impressions": 410000, "clicks": 9500, "conversions": 380, "revenue": 25000},
        {"date": "2026-W02", "channel": "Google", "spend": 13000, "impressions": 330000, "clicks": 8200, "conversions": 410, "revenue": 27500},
        {"date": "2026-W02", "channel": "Meta",   "spend": 17000, "impressions": 420000, "clicks": 9000, "conversions": 320, "revenue": 21500},  # conversion drop
        {"date": "2026-W03", "channel": "Google", "spend": 12500, "impressions": 340000, "clicks": 8400, "conversions": 450, "revenue": 30000},
        {"date": "2026-W03", "channel": "Meta",   "spend": 16500, "impressions": 430000, "clicks": 9200, "conversions": 360, "revenue": 24000},
    ]
    return pd.DataFrame(data)


def validate_schema(df: pd.DataFrame, required_cols: List[str] = REQUIRED_COLUMNS) -> Tuple[bool, List[str]]:
    missing = [c for c in required_cols if c not in df.columns]
    return (len(missing) == 0), missing


def load_data(file) -> IngestionResult:
    """
    file: streamlit uploaded file object OR None
    Returns: IngestionResult with dataframe + schema validation info
    """
    if file is None:
        df = load_dummy_marketing_data()
        schema_ok, missing = validate_schema(df)
        return IngestionResult(df=df, used_dummy=True, schema_ok=schema_ok, missing_columns=missing)

    # If file uploaded
    df = pd.read_csv(file)

    # Basic cleanup: trim column names
    df.columns = [c.strip() for c in df.columns]

    schema_ok, missing = validate_schema(df)
    return IngestionResult(df=df, used_dummy=False, schema_ok=schema_ok, missing_columns=missing)