import pandas as pd


def compute_kpis(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    required = ["impressions", "clicks", "spend", "conversions", "revenue"]
    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Cannot compute KPIs: missing columns {missing_cols}")

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["CTR"] = df["clicks"] / df["impressions"].replace({0: pd.NA})
    df["CPC"] = df["spend"] / df["clicks"].replace({0: pd.NA})
    df["CAC"] = df["spend"] / df["conversions"].replace({0: pd.NA})
    df["ROAS"] = df["revenue"] / df["spend"].replace({0: pd.NA})

    return df


def aggregate_by_week(df: pd.DataFrame) -> pd.DataFrame:
    weekly = df.groupby("date").agg({
        "spend": "sum",
        "impressions": "sum",
        "clicks": "sum",
        "conversions": "sum",
        "revenue": "sum"
    }).reset_index()

    weekly["CTR"] = weekly["clicks"] / weekly["impressions"]
    weekly["CPC"] = weekly["spend"] / weekly["clicks"]
    weekly["CAC"] = weekly["spend"] / weekly["conversions"]
    weekly["ROAS"] = weekly["revenue"] / weekly["spend"]

    return weekly


def compute_wow_change(weekly_df: pd.DataFrame) -> pd.DataFrame:
    weekly_df = weekly_df.copy()

    metrics = ["revenue", "spend", "conversions", "CTR", "CAC", "ROAS"]

    for m in metrics:
        weekly_df[f"{m}_WoW_%"] = weekly_df[m].pct_change() * 100

    return weekly_df