import streamlit as st
import altair as alt
import pandas as pd

from src.data_io import load_data, REQUIRED_COLUMNS
from src.kpi_engine import compute_kpis, aggregate_by_week, compute_wow_change
from src.insight_builder import (
    driver_attribution_by_dimension,
    detect_threshold_anomalies,
    build_insights_json,
    group_by_dimension_metric,
    compare_two_dimensions,
)
from src.llm_layer import generate_chart_spec, generate_exec_memo
from src.chart_layer import create_chart_from_spec


st.set_page_config(page_title="Agentic KPI Insights", layout="wide")
st.title("Agentic KPI Insights — Marketing Performance Analytics")

st.write("Upload a CSV or run with dummy/synthetic data.")

uploaded = st.file_uploader("Upload marketing KPI CSV", type=["csv"])
result = load_data(uploaded)

if result.used_dummy:
    st.info("No CSV uploaded → using dummy dataset (pipeline testing mode).")
else:
    st.success("CSV uploaded successfully.")

if not result.schema_ok:
    st.error(f"Schema validation failed. Missing columns: {result.missing_columns}")
    st.write("Required columns are:", REQUIRED_COLUMNS)
    st.stop()
else:
    st.success("Schema validation passed ✅")

# ---------------------------
# DATA PREVIEW
# ---------------------------
st.subheader("Preview Data")
st.dataframe(result.df.head(20), use_container_width=True)

# ---------------------------
# KPI ANALYTICS ENGINE
# ---------------------------
st.subheader("KPI Analytics Engine")

kpi_df = compute_kpis(result.df)
weekly = aggregate_by_week(kpi_df)
weekly = compute_wow_change(weekly)

st.write("Weekly KPI Summary")
st.dataframe(weekly, use_container_width=True)

# ---------------------------
# INSIGHT BUILDER
# ---------------------------
st.subheader("Insight Builder")

periods = list(weekly["date"])
current_period = st.selectbox("Select Current Period", periods, index=len(periods) - 1)
baseline_period = st.selectbox("Select Baseline Period", periods, index=max(len(periods) - 2, 0))

# Select driver dimension from non-core columns
excluded_cols = ["date", "spend", "impressions", "clicks", "conversions", "revenue"]
dimension_options = [c for c in result.df.columns if c not in excluded_cols]

if "channel" in dimension_options:
    default_dimension = "channel"
elif len(dimension_options) > 0:
    default_dimension = dimension_options[0]
else:
    default_dimension = None

if default_dimension is not None:
    dimension = st.selectbox(
        "Driver dimension",
        dimension_options,
        index=dimension_options.index(default_dimension)
    )
else:
    st.warning("No valid dimensions available for driver analysis.")
    st.stop()

# ---------------------------
# GROUP-BY ANALYSIS
# ---------------------------
st.markdown("### Group-by Analysis")

metric_options = ["revenue", "spend", "conversions", "CTR", "CAC", "ROAS"]
metric = st.selectbox("Select Metric for Group-by", metric_options, index=0)

chart_type = st.selectbox(
    "Select Chart Type",
    ["bar", "line", "area", "stacked_altair", "faceted_altair", "annotated_trend"]
)

top_n = st.slider("Top N dimension values", 2, 20, 6)
fair_practice = st.checkbox("Include all dimension values (unchecked = top N)", value=True)

if st.button("Run Group-by Analysis"):
    grouped_df = group_by_dimension_metric(
        result.df,
        dimension=dimension,
        metric=metric,
        periods=[current_period, baseline_period]
    )

    if not fair_practice and not grouped_df.empty:
        top_categories = (
            grouped_df.groupby(dimension)[metric]
            .sum()
            .nlargest(top_n)
            .index
            .tolist()
        )
        grouped_df = grouped_df[grouped_df[dimension].isin(top_categories)]

    st.write(
        f"Group-by: {metric} by {dimension} for {current_period} and {baseline_period} "
        f"(top_n={top_n if not fair_practice else 'all'})"
    )
    st.dataframe(grouped_df, use_container_width=True)

    if not grouped_df.empty:
        pivot_df = grouped_df.pivot(index="date", columns=dimension, values=metric).fillna(0)

        if chart_type == "bar":
            st.bar_chart(pivot_df)

        elif chart_type == "line":
            st.line_chart(pivot_df)

        elif chart_type == "area":
            st.area_chart(pivot_df)

        elif chart_type == "stacked_altair":
            alt_df = grouped_df.copy()
            alt_df["date"] = pd.to_datetime(alt_df["date"], errors="coerce")

            stacked = (
                alt.Chart(alt_df)
                .mark_bar()
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y(f"{metric}:Q", stack="normalize", title=f"Share of {metric}"),
                    color=alt.Color(f"{dimension}:N", title=dimension),
                    tooltip=["date", dimension, metric],
                )
                .properties(height=450, width=950)
            )
            st.altair_chart(stacked, use_container_width=True)

        elif chart_type == "faceted_altair":
            alt_df = grouped_df.copy()
            alt_df["date"] = pd.to_datetime(alt_df["date"], errors="coerce")

            facet = (
                alt.Chart(alt_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y(f"{metric}:Q", title=metric),
                    color=alt.Color(f"{dimension}:N", legend=None),
                    tooltip=["date", dimension, metric],
                )
                .facet(row=alt.Row(f"{dimension}:N", title=dimension))
                .properties(height=100, width=800)
            )
            st.altair_chart(facet, use_container_width=True)

        elif chart_type == "annotated_trend":
            alt_df = grouped_df.copy()
            alt_df["date"] = pd.to_datetime(alt_df["date"], errors="coerce")

            base = (
                alt.Chart(alt_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y(f"{metric}:Q", title=metric),
                    color=alt.Color(f"{dimension}:N", title=dimension),
                    tooltip=["date", dimension, metric],
                )
                .properties(height=420, width=950, title=f"{metric} trend by {dimension}")
            )
            st.altair_chart(base, use_container_width=True)

# ---------------------------
# 2D DIMENSION COMPARISON
# ---------------------------
st.markdown("### 2D Dimension Comparison")

dim_compare_options = [c for c in result.df.columns if c not in excluded_cols]
if len(dim_compare_options) >= 2:
    dim1 = st.selectbox("Select first dimension", dim_compare_options, index=0)
    dim2_candidates = [d for d in dim_compare_options if d != dim1]
    dim2 = st.selectbox("Select second dimension", dim2_candidates, index=0)

    compare_metric = st.selectbox("Select comparison metric", metric_options, index=0, key="compare_metric")
    compare_period = st.selectbox("Select period for comparison", periods, index=len(periods) - 1, key="compare_period")

    if st.button("Run 2D Comparison"):
        compare_df = compare_two_dimensions(
            result.df,
            dim1=dim1,
            dim2=dim2,
            metric=compare_metric,
            period=compare_period
        )
        st.dataframe(compare_df, use_container_width=True)

        if not compare_df.empty:
            compare_chart = (
                alt.Chart(compare_df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{dim1}:N", title=dim1),
                    y=alt.Y(f"{compare_metric}:Q", title=compare_metric),
                    color=alt.Color(f"{dim2}:N", title=dim2),
                    tooltip=[dim1, dim2, compare_metric]
                )
                .properties(width=900, height=450, title=f"{compare_metric} by {dim1} and {dim2}")
            )
            st.altair_chart(compare_chart, use_container_width=True)

# ---------------------------
# DRIVER + ANOMALY PIPELINE
# ---------------------------
threshold = st.slider("Anomaly Threshold (% WoW)", 5, 50, 15)

driver_df = driver_attribution_by_dimension(
    result.df,
    current_period,
    baseline_period,
    dimension=dimension,
    metric="revenue"
)

anomaly_df = detect_threshold_anomalies(
    weekly,
    threshold_pct=float(threshold)
)

insights = build_insights_json(
    weekly_df=weekly,
    driver_df=driver_df,
    current_period=current_period,
    baseline_period=baseline_period,
    anomaly_df=anomaly_df,
    raw_df=result.df,
    dimension=dimension,
    metric="revenue"
)

st.write(f"Driver Attribution (Revenue Δ by {dimension})")
st.dataframe(driver_df, use_container_width=True)

st.write("Anomalies Detected")
st.dataframe(anomaly_df, use_container_width=True)

st.write("Structured Insights JSON (LLM Input)")
st.json(insights)

if "key_findings" in insights:
    st.write("Key Findings Summary")
    st.json(insights["key_findings"])

# ---------------------------
# CHART RECOMMENDATION
# ---------------------------
st.subheader("Chart Recommendation")

if "chart_spec" not in st.session_state:
    st.session_state.chart_spec = None

if st.button("Recommend a chart"):
    try:
        st.session_state.chart_spec = generate_chart_spec(insights)
        st.success("Chart recommendation generated.")
    except Exception as chart_error:
        st.error(f"Chart recommendation failed: {chart_error}")

if st.session_state.chart_spec is not None:
    st.write("Recommended chart specification")
    st.json(st.session_state.chart_spec)

    try:
        chart = create_chart_from_spec(
    result.df,
    st.session_state.chart_spec,
    current_period=current_period
)
        st.altair_chart(chart.properties(height=420), use_container_width=True)
    except Exception as render_error:
        st.error(f"Unable to render chart from spec: {render_error}")

# ---------------------------
# LLM EXECUTIVE MEMO
# ---------------------------
st.subheader("LLM-Based Executive Memo")

if st.button("Generate Executive Memo"):
    try:
        memo = generate_exec_memo(insights, st.session_state.chart_spec)
        st.text_area("Executive Memo Output", memo, height=380)
    except Exception as e:
        st.error(f"LLM call failed: {e}")

# ---------------------------
# SEGMENTATION ANALYSIS
# ---------------------------
st.subheader("Segmentation Analysis")

segm = insights.get("segmentation_analysis", {})

if not segm:
    st.info("No segmentation analysis data available. Check your input columns and rerun.")
else:
    for dim, dim_insight in segm.items():
        st.markdown(f"### {dim.capitalize()}")

        if isinstance(dim_insight, dict) and dim_insight.get("error"):
            st.warning(dim_insight.get("error"))
            continue

        st.write(
            "Best performing segment:",
            dim_insight.get("best_performing_segment", {}).get("name")
        )
        st.write(
            "Worst performing segment:",
            dim_insight.get("worst_performing_segment", {}).get("name")
        )

        segment_distribution = dim_insight.get("segment_distribution", [])
        if segment_distribution:
            seg_df = pd.DataFrame(segment_distribution)
            st.dataframe(seg_df, use_container_width=True)

        st.write("Anomalies by segment:")
        anomalies = dim_insight.get("anomalies_by_segment", [])
        if anomalies:
            st.dataframe(pd.DataFrame(anomalies), use_container_width=True)
        else:
            st.write("None detected")

# ---------------------------
# STATISTICAL ANALYSIS
# ---------------------------
st.subheader("Statistical Analysis")

# 1. Descriptive statistics
st.markdown("**1. Descriptive statistics (raw data)**")
try:
    desc_stats = kpi_df[
        ["spend", "impressions", "clicks", "conversions", "revenue", "CTR", "CAC", "ROAS"]
    ].describe().T
    st.dataframe(desc_stats, use_container_width=True)
except KeyError as e:
    st.warning(f"Missing column for descriptive statistics: {e}")

# 2. Grouped summary statistics
st.markdown("**2. Grouped summary statistics**")

summary_dimension_options = [c for c in result.df.columns if c not in excluded_cols]
if not summary_dimension_options:
    summary_dimension_options = [dimension]

summary_dimension = st.selectbox(
    "Select grouping dimension for summary",
    summary_dimension_options
)

if st.button("Compute grouped summary"):
    try:
        summary_df = result.df.copy()

        for col in ["CTR", "CAC", "ROAS"]:
            if col not in summary_df.columns:
                if col == "CTR":
                    summary_df["CTR"] = summary_df["clicks"] / summary_df["impressions"].replace({0: pd.NA})
                elif col == "CAC":
                    summary_df["CAC"] = summary_df["spend"] / summary_df["conversions"].replace({0: pd.NA})
                elif col == "ROAS":
                    summary_df["ROAS"] = summary_df["revenue"] / summary_df["spend"].replace({0: pd.NA})

        grouped = summary_df.groupby(summary_dimension).agg(
            avg_roas=("ROAS", "mean"),
            avg_cac=("CAC", "mean"),
            avg_ctr=("CTR", "mean"),
            total_spend=("spend", "sum"),
            total_revenue=("revenue", "sum"),
            total_conversions=("conversions", "sum"),
        ).reset_index().sort_values("avg_roas", ascending=False)

        st.dataframe(grouped, use_container_width=True)

        if "channel" in summary_df.columns:
            best_roas_channel = summary_df.groupby("channel")["ROAS"].mean().idxmax()
            st.markdown(f"- **Best ROAS channel:** {best_roas_channel}")

        if "campaign_type" in summary_df.columns:
            lowest_cac_campaign = summary_df.groupby("campaign_type")["CAC"].mean().idxmin()
            st.markdown(f"- **Lowest CAC campaign_type:** {lowest_cac_campaign}")

        if "customer_segment" in summary_df.columns and "engagement_score" in summary_df.columns:
            best_engagement_segment = summary_df.groupby("customer_segment")["engagement_score"].mean().idxmax()
            st.markdown(f"- **Best engagement customer_segment:** {best_engagement_segment}")

    except Exception as grouped_error:
        st.error(f"Grouped summary failed: {grouped_error}")

# 3. Time-based trend analysis
st.markdown("**3. Time-based trend analysis**")

try:
    weekly_trends = weekly.copy()
    weekly_trends["date"] = pd.to_datetime(weekly_trends["date"], errors="coerce")

    if weekly_trends["date"].isna().all():
        st.warning("Date parsing failed for time-based trend analysis.")
    else:
        trend_metric = st.selectbox("Select KPI for weekly trend", ["ROAS", "CAC", "clicks"], index=0)

        trend_chart = (
            alt.Chart(weekly_trends)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Week"),
                y=alt.Y(f"{trend_metric}:Q", title=trend_metric),
                tooltip=["date", trend_metric]
            )
            .properties(width=950, height=400, title="Weekly KPI trends")
        )
        st.altair_chart(trend_chart, use_container_width=True)

        roas_drift = (
            weekly_trends["ROAS"].pct_change().iloc[-1] * 100
            if len(weekly_trends) > 1 and pd.notna(weekly_trends["ROAS"].pct_change().iloc[-1])
            else 0.0
        )

        anomaly_periods = weekly_trends[
            (weekly_trends["revenue_WoW_%"].abs() >= 15)
            | (weekly_trends["spend_WoW_%"].abs() >= 15)
            | (weekly_trends["ROAS_WoW_%"].abs() >= 15)
        ]

        last_anomaly = None
        if not anomaly_periods.empty:
            last_anomaly = anomaly_periods["date"].max().strftime("%Y-%m-%d")

        st.markdown("### Trend summary")
        st.markdown(f"- **Recent ROAS drift:** {roas_drift:+.2f}%")
        st.markdown(f"- **Last anomaly week:** {last_anomaly if last_anomaly is not None else 'None detected'}")

        st.write("Weekly anomaly periods (>= 15% WoW change)")
        st.dataframe(anomaly_periods.sort_values("date"), use_container_width=True)

        insights["agent_prompt_insights"] = {
            "recent_roas_drift_pct": round(roas_drift, 2),
            "last_anomaly_week": last_anomaly or "none",
            "top_channel_by_roas": None,
        }

        if "channel" in result.df.columns and "ROAS" in result.df.columns:
            channel_roas = result.df.groupby("channel")["ROAS"].mean().idxmax()
            insights["agent_prompt_insights"]["top_channel_by_roas"] = str(channel_roas)

        # 4. Optional STL decomposition
        try:
            from statsmodels.tsa.seasonal import STL

            st.write("**Seasonal decomposition (STL)**")
            decompose_metric = st.selectbox("Choose metric for decomposition", ["ROAS", "CAC", "clicks"], index=0)
            st.write(f"Decomposing {decompose_metric}")

            decomposition_input = weekly_trends.set_index("date")[decompose_metric].dropna()
            decomposition_input = decomposition_input.sort_index().asfreq("W", method="pad")

            st.write("Decomposition frequency: weekly")

            stl = STL(decomposition_input, period=52, robust=True)
            res = stl.fit()

            decomposed = pd.DataFrame({
                "trend": res.trend,
                "seasonal": res.seasonal,
                "resid": res.resid,
            })

            melt_dec = decomposed.reset_index().melt(
                id_vars=["date"],
                var_name="component",
                value_name="value"
            )

            dec_chart = (
                alt.Chart(melt_dec)
                .mark_line()
                .encode(
                    x="date:T",
                    y=alt.Y("value:Q", title="Value"),
                    color=alt.Color("component:N", scale=alt.Scale(scheme="dark2"))
                )
                .properties(width=900, height=400, title=f"STL Decomposition of {decompose_metric}")
            )
            st.altair_chart(dec_chart, use_container_width=True)

        except Exception as stl_error:
            st.info(f"STL decomposition not available or failed: {stl_error}")

except Exception as trend_error:
    st.error(f"Time-based trend analysis failed: {trend_error}")