import streamlit as st
from src.data_io import load_data, REQUIRED_COLUMNS
from src.kpi_engine import compute_kpis, aggregate_by_week, compute_wow_change
from src.insight_builder import (
    driver_attribution_by_dimension,
    detect_threshold_anomalies,
    build_insights_json,
)
from src.llm_layer import generate_exec_memo

st.set_page_config(page_title="Agentic KPI Insights", layout="wide")
st.title("Agentic KPI Insights — Step 3: Data Ingestion ✅")

st.write("Upload a CSV or run with dummy data.")

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

st.subheader("Preview Data")
st.dataframe(result.df.head(20), use_container_width=True)

st.subheader("KPI Analytics Engine")

kpi_df = compute_kpis(result.df)

weekly = aggregate_by_week(kpi_df)

weekly = compute_wow_change(weekly)

st.write("Weekly KPI Summary")
st.dataframe(weekly)

st.subheader("Insight Builder")

# Choose periods (current vs baseline)
periods = list(weekly["date"])
current_period = st.selectbox("Select Current Period", periods, index=len(periods)-1)
baseline_period = st.selectbox("Select Baseline Period", periods, index=max(len(periods)-2, 0))

threshold = st.slider("Anomaly Threshold (% WoW)", 5, 50, 15)

driver_df = driver_attribution_by_dimension(
    result.df,
    current_period,
    baseline_period,
    dimension="channel",
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
    dimension="channel",
    metric="revenue"
)

st.write("Driver Attribution (Revenue Δ by Channel)")
st.dataframe(driver_df, use_container_width=True)

st.write("Anomalies Detected")
st.dataframe(anomaly_df, use_container_width=True)

st.write("Structured Insights JSON (LLM Input)")
st.json(insights)


st.subheader("LLM-Based Executive Memo")

if st.button("Generate Executive Memo"):
    try:
        memo = generate_exec_memo(insights)
        st.text_area("Executive Memo Output", memo, height=350)
    except Exception as e:
        st.error(f"LLM call failed: {e}")
        