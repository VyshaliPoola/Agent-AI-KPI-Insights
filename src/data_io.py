from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

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

# --- 2) Column mapping for Marketing Campaign CSV ---
COLUMN_MAPPING = {
    "Date": "date",
    "Channel_Used": "channel",
    "Acquisition_Cost": "spend",
    "Impressions": "impressions",
    "Clicks": "clicks",
    "Conversion_Rate": "conversion_rate",
    "ROI": "roi",
}


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

    # Apply column mapping
    df = _apply_column_mapping(df)

    schema_ok, missing = validate_schema(df)
    return IngestionResult(df=df, used_dummy=False, schema_ok=schema_ok, missing_columns=missing)


def _apply_column_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """
    Maps incoming CSV columns to required schema and calculates missing metrics.
    """
    # Step 1: Rename columns based on mapping
    rename_map = {}
    for orig_col, new_col in COLUMN_MAPPING.items():
        if orig_col in df.columns:
            rename_map[orig_col] = new_col

    df = df.rename(columns=rename_map)

    # Step 2: Convert numeric columns to proper types
    numeric_cols = ["spend", "impressions", "clicks", "conversion_rate", "roi"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Step 3: Calculate missing required columns
    # Calculate conversions from clicks and conversion_rate
    if "clicks" in df.columns and "conversion_rate" in df.columns:
        max_conv = df["conversion_rate"].max()
        if max_conv <= 1:
            # Already in fraction form (e.g., 0.05)
            df["conversions"] = (df["clicks"] * df["conversion_rate"]).round().astype(int)
        else:
            # Percent form (e.g., 5 or 5.0)
            df["conversions"] = (df["clicks"] * df["conversion_rate"] / 100).round().astype(int)
    elif "clicks" in df.columns:
        # If conversion_rate is missing, assume 5% default
        df["conversions"] = (df["clicks"] * 0.05).round().astype(int)

    # Calculate revenue from spend and ROI
    if "spend" in df.columns and "roi" in df.columns:
        # ROI % → Revenue = Spend * (1 + ROI/100)
        df["revenue"] = (df["spend"] * (1 + df["roi"] / 100)).round(2)
    elif "spend" in df.columns:
        # If ROI is missing, assume 2x return (100% ROI)
        df["revenue"] = (df["spend"] * 2).round(2)

    # Step 4: Keep required columns but also preserve additional columns for analysis
    # Ensure required columns exist (add them if missing)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = 0  # Default value for missing required columns

    # Don't drop extra columns - keep them for analysis
    # df = df[REQUIRED_COLUMNS]  # Commented out to preserve extra columns

    return df