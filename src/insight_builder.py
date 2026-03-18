import pandas as pd


def get_period_row(weekly_df: pd.DataFrame, period: str) -> dict:
    """
    Returns one row of weekly KPI summary as a dictionary.
    """
    row = weekly_df[weekly_df["date"] == period]
    if row.empty:
        raise ValueError(f"Period '{period}' not found in weekly_df.")
    return row.iloc[0].to_dict()


def extract_kpi_changes(period_row: dict) -> dict:
    """
    Extracts WoW KPI changes from a weekly KPI row.
    """
    kpi_changes = {}
    for key, value in period_row.items():
        if str(key).endswith("_WoW_%") and pd.notna(value):
            metric_name = key.replace("_WoW_%", "")
            kpi_changes[metric_name] = round(float(value), 2)
    return kpi_changes


def driver_attribution_by_dimension(
    df: pd.DataFrame,
    current_period: str,
    baseline_period: str,
    dimension: str = "channel",
    metric: str = "revenue"
) -> pd.DataFrame:
    """
    Generic driver attribution by any dimension (channel, region, device, etc.).
    Compares current vs baseline period and computes delta for the selected metric.
    """
    cur = (
        df[df["date"] == current_period]
        .groupby(dimension)[metric]
        .sum()
        .reset_index()
    )

    base = (
        df[df["date"] == baseline_period]
        .groupby(dimension)[metric]
        .sum()
        .reset_index()
    )

    merged = cur.merge(
        base,
        on=dimension,
        how="outer",
        suffixes=("_current", "_baseline")
    ).fillna(0)

    merged[f"delta_{metric}"] = merged[f"{metric}_current"] - merged[f"{metric}_baseline"]
    merged = merged.sort_values(f"delta_{metric}")

    return merged


def summarize_driver_impacts(
    driver_df: pd.DataFrame,
    dimension: str = "channel",
    metric: str = "revenue",
    top_n: int = 2
) -> tuple[list, list]:
    """
    Returns top negative and positive drivers as JSON-friendly lists.
    """
    delta_col = f"delta_{metric}"
    sorted_df = driver_df.sort_values(delta_col)

    top_negative = sorted_df.head(top_n)[[dimension, delta_col]].to_dict(orient="records")
    top_positive = sorted_df.tail(top_n)[[dimension, delta_col]].to_dict(orient="records")

    return top_negative, top_positive


def detect_threshold_anomalies(weekly_df: pd.DataFrame, threshold_pct: float = 15.0) -> pd.DataFrame:
    """
    Flags KPIs where absolute WoW % change exceeds threshold.
    Adds anomaly severity and detection type.
    """
    wow_cols = [c for c in weekly_df.columns if c.endswith("_WoW_%")]
    anomalies = []

    for _, row in weekly_df.iterrows():
        for col in wow_cols:
            val = row[col]
            if pd.notna(val) and abs(val) >= threshold_pct:
                severity = "high" if abs(val) >= 25 else "moderate"
                anomalies.append({
                    "date": row["date"],
                    "metric": col.replace("_WoW_%", ""),
                    "wow_pct": round(float(val), 2),
                    "threshold_pct": threshold_pct,
                    "anomaly_type": "threshold-based",
                    "severity": severity
                })

    return pd.DataFrame(anomalies)


def build_insights_json(
    weekly_df: pd.DataFrame,
    driver_df: pd.DataFrame,
    current_period: str,
    baseline_period: str,
    anomaly_df: pd.DataFrame,
    dimension: str = "channel",
    metric: str = "revenue"
) -> dict:
    """
    Builds structured insights dictionary for LLM input.
    """
    current_row = get_period_row(weekly_df, current_period)
    baseline_row = get_period_row(weekly_df, baseline_period)

    kpi_changes = extract_kpi_changes(current_row)

    top_negative, top_positive = summarize_driver_impacts(
        driver_df, dimension=dimension, metric=metric, top_n=2
    )

    insights = {
        "period_comparison": f"{current_period} vs {baseline_period}",
        "current_period_summary": {
            "revenue": current_row.get("revenue"),
            "spend": current_row.get("spend"),
            "conversions": current_row.get("conversions"),
            "CTR": round(current_row.get("CTR", 0), 4) if pd.notna(current_row.get("CTR")) else None,
            "CAC": round(current_row.get("CAC", 0), 4) if pd.notna(current_row.get("CAC")) else None,
            "ROAS": round(current_row.get("ROAS", 0), 4) if pd.notna(current_row.get("ROAS")) else None,
        },
        "baseline_period_summary": {
            "revenue": baseline_row.get("revenue"),
            "spend": baseline_row.get("spend"),
            "conversions": baseline_row.get("conversions"),
            "CTR": round(baseline_row.get("CTR", 0), 4) if pd.notna(baseline_row.get("CTR")) else None,
            "CAC": round(baseline_row.get("CAC", 0), 4) if pd.notna(baseline_row.get("CAC")) else None,
            "ROAS": round(baseline_row.get("ROAS", 0), 4) if pd.notna(baseline_row.get("ROAS")) else None,
        },
        "kpi_wow_changes_pct": kpi_changes,
        "top_negative_drivers": top_negative,
        "top_positive_drivers": top_positive,
        "anomalies": anomaly_df.to_dict(orient="records"),
        "anomaly_count": len(anomaly_df),
        "notes": f"Insights computed using rule-based logic with {dimension}-level driver attribution and threshold anomaly detection."
    }

    return insights