import pandas as pd


def get_period_row(weekly_df: pd.DataFrame, period: str) -> dict:
    row = weekly_df[weekly_df["date"] == period]
    if row.empty:
        raise ValueError(f"Period '{period}' not found in weekly_df.")
    return row.iloc[0].to_dict()


def extract_kpi_changes(period_row: dict) -> dict:
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
    delta_col = f"delta_{metric}"
    sorted_df = driver_df.sort_values(delta_col)

    top_negative = sorted_df.head(top_n)[[dimension, delta_col]].to_dict(orient="records")
    top_positive = sorted_df.tail(top_n)[[dimension, delta_col]].to_dict(orient="records")

    return top_negative, top_positive


def detect_threshold_anomalies(
    weekly_df: pd.DataFrame,
    threshold_pct: float = 15.0
) -> pd.DataFrame:
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


def detect_anomalies_by_segment(
    df: pd.DataFrame,
    dimension: str,
    metric: str,
    threshold_pct: float = 15.0
) -> pd.DataFrame:
    if dimension not in df.columns:
        raise ValueError(f"Dimension '{dimension}' not found in dataframe columns")

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in dataframe columns")

    weekly_segment = (
        df.groupby(["date", dimension])[metric]
        .sum()
        .reset_index()
        .sort_values(["date", dimension])
    )

    weekly_segment["prev_value"] = weekly_segment.groupby(dimension)[metric].shift(1)
    weekly_segment["wow_pct"] = (
        (weekly_segment[metric] - weekly_segment["prev_value"])
        / weekly_segment["prev_value"] * 100
    ).round(2)

    anomalies = weekly_segment[weekly_segment["wow_pct"].abs() >= threshold_pct].copy()
    anomalies["threshold_pct"] = threshold_pct
    anomalies["anomaly_type"] = "segment-level"
    anomalies["severity"] = anomalies["wow_pct"].abs().apply(
        lambda x: "high" if x >= 25 else "moderate"
    )

    return anomalies[[ "date", dimension, "wow_pct", "threshold_pct", "anomaly_type", "severity"]].reset_index(drop=True)


def driver_attribution_by_segment(
    df: pd.DataFrame,
    segment_dimension: str,
    segment_value,
    sub_dimension: str,
    current_period: str,
    baseline_period: str,
    metric: str = "revenue"
) -> pd.DataFrame:
    segment_df = df[df[segment_dimension] == segment_value]
    return driver_attribution_by_dimension(
        segment_df,
        current_period=current_period,
        baseline_period=baseline_period,
        dimension=sub_dimension,
        metric=metric
    )


def group_by_dimension_metric(
    df: pd.DataFrame,
    dimension: str,
    metric: str,
    periods: list[str] | None = None,
) -> pd.DataFrame:
    if dimension not in df.columns:
        raise ValueError(f"Dimension '{dimension}' not found in dataframe columns")

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in dataframe columns")

    work_df = df.copy()

    if periods is not None and "date" in work_df.columns:
        work_df = work_df[work_df["date"].isin(periods)]

    grouped = (
        work_df.groupby(["date", dimension])[metric]
        .sum()
        .reset_index()
        .sort_values(["date", metric], ascending=[True, False])
    )

    return grouped


def compare_two_dimensions(
    df: pd.DataFrame,
    dim1: str,
    dim2: str,
    metric: str,
    period: str,
) -> pd.DataFrame:
    if dim1 not in df.columns or dim2 not in df.columns:
        raise ValueError("Selected dimensions must be in DataFrame columns")

    if metric not in df.columns:
        raise ValueError("Selected metric must be in DataFrame columns")

    base = df[df["date"] == period]

    summary = (
        base.groupby([dim1, dim2])[metric]
        .sum()
        .reset_index()
        .sort_values(metric, ascending=False)
    )

    return summary


def segmentation_analysis(
    df: pd.DataFrame,
    dimensions: list[str],
    metric: str,
    current_period: str,
    baseline_period: str,
    period: str | None = None,
    top_n: int = 5,
    sub_dimension: str = "channel"
) -> dict:
    insights = {}

    for dimension in dimensions:
        if dimension not in df.columns:
            insights[dimension] = {"error": f"Dimension '{dimension}' not found in dataframe columns"}
            continue

        if metric not in df.columns:
            insights[dimension] = {"error": f"Metric '{metric}' not found in dataframe columns"}
            continue

        work_df = df.copy()
        if period is not None and "date" in work_df.columns:
            work_df = work_df[work_df["date"] == period]

        grouped = (
            work_df.groupby(dimension)[metric]
            .agg(["sum", "mean", "count"])
            .reset_index()
            .sort_values("mean", ascending=False)
        )

        if grouped.empty:
            insights[dimension] = {"error": f"No data available for dimension '{dimension}'"}
            continue

        total_metric = grouped["sum"].sum()
        grouped["percentage"] = (grouped["sum"] / total_metric * 100).round(2) if total_metric != 0 else 0

        top_segments = grouped.head(top_n).to_dict(orient="records")
        bottom_segments = grouped.tail(top_n).to_dict(orient="records")

        best_segment = grouped.iloc[0][dimension]
        worst_segment = grouped.iloc[-1][dimension]

        best_drivers = driver_attribution_by_segment(
            df, dimension, best_segment, sub_dimension, current_period, baseline_period, metric
        )
        worst_drivers = driver_attribution_by_segment(
            df, dimension, worst_segment, sub_dimension, current_period, baseline_period, metric
        )

        best_negative, best_positive = summarize_driver_impacts(best_drivers, sub_dimension, metric, top_n=2)
        worst_negative, worst_positive = summarize_driver_impacts(worst_drivers, sub_dimension, metric, top_n=2)

        insights[dimension] = {
            "metric": metric,
            "period": period,
            "total_segments": len(grouped),
            "best_performing_segment": {
                "name": best_segment,
                "mean_value": round(grouped.iloc[0]["mean"], 2),
                "total_value": round(grouped.iloc[0]["sum"], 2),
                "percentage": round(grouped.iloc[0]["percentage"], 2),
                "top_negative_drivers": best_negative,
                "top_positive_drivers": best_positive
            },
            "worst_performing_segment": {
                "name": worst_segment,
                "mean_value": round(grouped.iloc[-1]["mean"], 2),
                "total_value": round(grouped.iloc[-1]["sum"], 2),
                "percentage": round(grouped.iloc[-1]["percentage"], 2),
                "top_negative_drivers": worst_negative,
                "top_positive_drivers": worst_positive
            },
            "top_segments": top_segments,
            "bottom_segments": bottom_segments,
            "segment_distribution": grouped[[dimension, "mean", "sum", "percentage"]].to_dict(orient="records"),
            "anomalies_by_segment": detect_anomalies_by_segment(df, dimension, metric).to_dict(orient="records")
        }

    return insights


def build_key_findings(
    kpi_changes: dict,
    top_negative: list,
    top_positive: list,
    anomaly_df: pd.DataFrame,
    segmentation_results: dict | None = None
) -> dict:
    sorted_kpis = sorted(
        kpi_changes.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    top_kpi_movers = [
        {"metric": metric, "wow_pct": value}
        for metric, value in sorted_kpis[:3]
    ]

    strongest_negative_driver = top_negative[0] if len(top_negative) > 0 else None
    strongest_positive_driver = top_positive[-1] if len(top_positive) > 0 else None

    highest_priority_anomaly = None
    if not anomaly_df.empty:
        sorted_anomalies = anomaly_df.sort_values(
            by="wow_pct",
            key=lambda s: s.abs(),
            ascending=False
        )
        highest_priority_anomaly = sorted_anomalies.iloc[0].to_dict()

    best_segment = None
    worst_segment = None

    if segmentation_results:
        for dim, seg_data in segmentation_results.items():
            if isinstance(seg_data, dict):
                if seg_data.get("best_performing_segment") and best_segment is None:
                    best_segment = {
                        "dimension": dim,
                        **seg_data["best_performing_segment"]
                    }
                if seg_data.get("worst_performing_segment") and worst_segment is None:
                    worst_segment = {
                        "dimension": dim,
                        **seg_data["worst_performing_segment"]
                    }

    return {
        "top_kpi_movers": top_kpi_movers,
        "strongest_negative_driver": strongest_negative_driver,
        "strongest_positive_driver": strongest_positive_driver,
        "highest_priority_anomaly": highest_priority_anomaly,
        "best_segment": best_segment,
        "worst_segment": worst_segment,
    }


def build_insights_json(
    weekly_df: pd.DataFrame,
    driver_df: pd.DataFrame,
    current_period: str,
    baseline_period: str,
    anomaly_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    dimension: str = "channel",
    metric: str = "revenue"
) -> dict:
    current_row = get_period_row(weekly_df, current_period)
    baseline_row = get_period_row(weekly_df, baseline_period)

    kpi_changes = extract_kpi_changes(current_row)

    top_negative, top_positive = summarize_driver_impacts(
        driver_df,
        dimension=dimension,
        metric=metric,
        top_n=2
    )

    expected_dimensions = ["customer_segment", "location", "channel", "campaign_type"]
    available_dimensions = [d for d in expected_dimensions if d in raw_df.columns]

    segmentation_insights = segmentation_analysis(
        raw_df,
        dimensions=available_dimensions,
        metric=metric,
        current_period=current_period,
        baseline_period=baseline_period,
        period=current_period,
        top_n=5
    )

    numeric_columns = raw_df.select_dtypes(include=["number"]).columns.tolist()
    dims = [d for d in expected_dimensions if d in raw_df.columns]

    key_findings = build_key_findings(
        kpi_changes=kpi_changes,
        top_negative=top_negative,
        top_positive=top_positive,
        anomaly_df=anomaly_df,
        segmentation_results=segmentation_insights
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
        "segmentation_analysis": segmentation_insights,
        "key_findings": key_findings,
        "available_fields": {
            "numeric": sorted(numeric_columns),
            "categorical": sorted(dims),
            "date": ["date"] if "date" in raw_df.columns else [],
            "supported_charts": ["line", "bar", "scatter", "box", "histogram"],
        },
        "notes": f"Insights computed using rule-based logic with {dimension}-level driver attribution, threshold anomaly detection, and segmentation analysis."
    }

    return insights