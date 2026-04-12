import altair as alt
import pandas as pd
from typing import Optional

VALID_CHART_TYPES = {"line", "bar", "scatter", "box", "histogram"}


def _get_axis_type(df: pd.DataFrame, field: str) -> str:
    if field not in df.columns:
        raise ValueError(f"Field '{field}' not found in DataFrame columns")
    if field == "date":
        return "T"
    if pd.api.types.is_numeric_dtype(df[field]):
        return "Q"
    return "N"


def generate_line_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
) -> alt.Chart:
    x_type = _get_axis_type(df, x)
    if _get_axis_type(df, y) != "Q":
        raise ValueError(f"Line plot y-axis must be numeric. '{y}' is not numeric.")

    encoding = {
        "x": alt.X(f"{x}:{x_type}", title=x.replace("_", " ").title()),
        "y": alt.Y(f"{y}:Q", title=y.replace("_", " ").title()),
    }
    if color:
        encoding["color"] = alt.Color(f"{color}:N", title=color.replace("_", " ").title())

    return (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=2)
        .encode(**encoding)
        .properties(title=title or f"{y.replace('_', ' ').title()} over {x.replace('_', ' ').title()}")
    )


def generate_bar_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str | None = None
) -> alt.Chart:
    chart_df = df.copy()

    # sort descending by y for cleaner ranking
    chart_df = chart_df.sort_values(by=y, ascending=False)

    # base bar chart
    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{x}:N",
                sort="-y",
                title=x.replace("_", " ").title(),
                axis=alt.Axis(labelAngle=-45)
            ),
            y=alt.Y(
                f"{y}:Q",
                title=f"{y.replace('_', ' ').title()} (Current Period)"
            ),
            color=alt.Color(f"{color}:N", title=color.replace("_", " ").title()) if color else alt.value("#1f77b4"),
            tooltip=[x, y] + ([color] if color else [])
        )
        .properties(
            title=title,
            width=850,
            height=420
        )
    )

    # value labels on top of bars
    labels = (
        alt.Chart(chart_df)
        .mark_text(
            align="center",
            baseline="bottom",
            dy=-4,
            fontSize=11
        )
        .encode(
            x=alt.X(f"{x}:N", sort="-y"),
            y=alt.Y(f"{y}:Q"),
            text=alt.Text(f"{y}:Q", format=",.0f")
        )
    )

    return bars + labels

def generate_scatter_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
) -> alt.Chart:
    if _get_axis_type(df, x) not in {"Q", "T"}:
        raise ValueError(f"Scatter plot x-axis must be numeric or date. '{x}' is not valid.")
    if _get_axis_type(df, y) != "Q":
        raise ValueError(f"Scatter plot y-axis must be numeric. '{y}' is not numeric.")

    encoding = {
        "x": alt.X(f"{x}:{_get_axis_type(df, x)}", title=x.replace("_", " ").title()),
        "y": alt.Y(f"{y}:Q", title=y.replace("_", " ").title()),
        "tooltip": [x, y],
    }
    if color:
        encoding["color"] = alt.Color(f"{color}:N", title=color.replace("_", " ").title())
        encoding["tooltip"].append(color)

    return (
        alt.Chart(df)
        .mark_circle(size=80, opacity=0.8)
        .encode(**encoding)
        .properties(title=title or f"{y.replace('_', ' ').title()} vs {x.replace('_', ' ').title()}")
    )


def generate_box_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
) -> alt.Chart:
    if _get_axis_type(df, y) != "Q":
        raise ValueError(f"Box plot y-axis must be numeric. '{y}' is not numeric.")

    encoding = {
        "x": alt.X(f"{x}:N", title=x.replace("_", " ").title()),
        "y": alt.Y(f"{y}:Q", title=y.replace("_", " ").title()),
    }
    if color:
        encoding["color"] = alt.Color(f"{color}:N", title=color.replace("_", " ").title())

    return (
        alt.Chart(df)
        .mark_boxplot()
        .encode(**encoding)
        .properties(title=title or f"{y.replace('_', ' ').title()} distribution by {x.replace('_', ' ').title()}")
    )


def generate_histogram(
    df: pd.DataFrame,
    x: str,
    title: Optional[str] = None,
    nbins: int = 20,
) -> alt.Chart:
    if _get_axis_type(df, x) != "Q":
        raise ValueError(f"Histogram x-axis must be numeric. '{x}' is not numeric.")

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x}:Q", bin=alt.Bin(maxbins=nbins), title=x.replace("_", " ").title()),
            y=alt.Y("count():Q", title="Count"),
            tooltip=[x],
        )
        .properties(title=title or f"Distribution of {x.replace('_', ' ').title()}")
    )


def create_chart_from_spec(
    df: pd.DataFrame,
    chart_spec: dict,
    current_period: str | None = None
) -> alt.Chart:
    if not isinstance(chart_spec, dict):
        raise ValueError("Chart specification must be a dictionary.")

    chart_type = chart_spec.get("chart_type")
    x = chart_spec.get("x")
    y = chart_spec.get("y")
    color = chart_spec.get("color")
    title = chart_spec.get("title")
    question = str(chart_spec.get("question", "")).lower()

    if chart_type not in VALID_CHART_TYPES:
        raise ValueError(f"Unsupported chart_type '{chart_type}'. Supported: {sorted(VALID_CHART_TYPES)}")

    plot_df = df.copy()

    # Apply current-period filter if the question refers to the current period
    if current_period is not None and "current period" in question and "date" in plot_df.columns:
        plot_df = plot_df[plot_df["date"] == current_period]

    if chart_type == "histogram":
        return generate_histogram(plot_df, x, title=title)

    if x is None or y is None:
        raise ValueError("Chart specification must include both 'x' and 'y' for this chart type.")

    # For bar charts with categorical x and numeric y, aggregate before plotting
    if chart_type == "bar":
        if _get_axis_type(plot_df, x) == "N" and _get_axis_type(plot_df, y) == "Q":
            agg_cols = [x]
            if color:
                agg_cols.append(color)

            chart_df = (
                plot_df.groupby(agg_cols, dropna=False)[y]
                .sum()
                .reset_index()
            )
            return generate_bar_plot(chart_df, x, y, color=color, title=title)

        return generate_bar_plot(plot_df, x, y, color=color, title=title)

    if chart_type == "line":
        return generate_line_plot(plot_df, x, y, color=color, title=title)

    if chart_type == "scatter":
        return generate_scatter_plot(plot_df, x, y, color=color, title=title)

    if chart_type == "box":
        return generate_box_plot(plot_df, x, y, color=color, title=title)

    raise ValueError(f"Chart type '{chart_type}' is not implemented.")