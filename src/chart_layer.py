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
    color: Optional[str] = None,
    title: Optional[str] = None,
) -> alt.Chart:
    x_type = _get_axis_type(df, x)
    if _get_axis_type(df, y) != "Q":
        raise ValueError(f"Bar plot y-axis must be numeric. '{y}' is not numeric.")

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X(f"{x}:{x_type}", title=x.replace("_", " ").title()),
        y=alt.Y(f"{y}:Q", title=y.replace("_", " ").title()),
    )
    if color:
        chart = chart.encode(color=alt.Color(f"{color}:N", title=color.replace("_", " ").title()))

    return chart.properties(title=title or f"{y.replace('_', ' ').title()} by {x.replace('_', ' ').title()}")


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


def create_chart_from_spec(df: pd.DataFrame, chart_spec: dict) -> alt.Chart:
    if not isinstance(chart_spec, dict):
        raise ValueError("Chart specification must be a dictionary.")

    chart_type = chart_spec.get("chart_type")
    x = chart_spec.get("x")
    y = chart_spec.get("y")
    color = chart_spec.get("color")
    title = chart_spec.get("title")

    if chart_type not in VALID_CHART_TYPES:
        raise ValueError(f"Unsupported chart_type '{chart_type}'. Supported: {sorted(VALID_CHART_TYPES)}")

    if chart_type == "histogram":
        return generate_histogram(df, x, title=title)

    if x is None or y is None:
        raise ValueError("Chart specification must include both 'x' and 'y' for this chart type.")

    if chart_type == "line":
        return generate_line_plot(df, x, y, color=color, title=title)
    if chart_type == "bar":
        return generate_bar_plot(df, x, y, color=color, title=title)
    if chart_type == "scatter":
        return generate_scatter_plot(df, x, y, color=color, title=title)
    if chart_type == "box":
        return generate_box_plot(df, x, y, color=color, title=title)

    raise ValueError(f"Chart type '{chart_type}' is not implemented.")
