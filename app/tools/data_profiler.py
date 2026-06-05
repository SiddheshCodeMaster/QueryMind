"""
DataProfiler — generates a human-readable profile of a DataFrame.

Used by the /profile TUI command.

Output sections
---------------
1. Overall summary (rows, cols, memory, null overview)
2. Per-column table (type, null%, unique count, stats/samples)

For Excel multi-sheet files:
- Overall summary covers the combined df
- Per-sheet tables shown individually below
"""

import pandas as pd
from datetime import datetime


# Column type classification
def _classify(series: pd.Series) -> str:
    dtype = str(series.dtype)
    if "datetime" in dtype:
        return "datetime"
    if dtype in ("int64", "Int64", "int32", "Int32"):
        return "integer"
    if dtype in ("float64", "float32"):
        return "numeric"
    if series.nunique() / max(len(series), 1) > 0.5:
        return "text"  # high cardinality strings → probably free text
    return "categorical"


def _null_pct(series: pd.Series) -> str:
    pct = series.isna().sum() / max(len(series), 1) * 100
    if pct == 0:
        return "0%"
    if pct < 1:
        return f"<1%"
    return f"{pct:.1f}%"


def _stats(series: pd.Series, col_type: str) -> str:
    """Return a compact stats string appropriate for the column type."""
    try:
        if col_type == "datetime":
            mn = series.dropna().min()
            mx = series.dropna().max()
            return f"{mn.date()} → {mx.date()}"

        elif col_type in ("numeric", "integer"):
            mn = series.min()
            mx = series.max()
            avg = series.mean()
            if col_type == "integer":
                return f"min {mn:,}  ·  avg {avg:,.0f}  ·  max {mx:,}"
            return f"min {mn:,.2f}  ·  avg {avg:,.2f}  ·  max {mx:,.2f}"

        elif col_type == "categorical":
            top = series.value_counts().head(3).index.tolist()
            return ", ".join(str(v) for v in top)

        else:  # text
            sample = series.dropna().head(2).tolist()
            return "  |  ".join(str(v)[:30] for v in sample)

    except Exception:
        return "—"


def _profile_df(df: pd.DataFrame, title: str) -> str:
    """Generate a profile string for a single DataFrame."""
    rows, cols = df.shape

    # Skip _sheet discriminator column
    visible = [c for c in df.columns if c != "_sheet"]

    null_cols = sum(1 for c in visible if df[c].isna().any())
    total_nulls = sum(df[c].isna().sum() for c in visible)

    # Memory estimate
    try:
        mem_kb = df.memory_usage(deep=True).sum() / 1024
        if mem_kb > 1024:
            mem_str = f"{mem_kb / 1024:.1f} MB"
        else:
            mem_str = f"{mem_kb:.0f} KB"
    except Exception:
        mem_str = "—"

    lines = [
        f"",
        f"📊 {title}",
        "━" * 62,
        f"  Rows    : {rows:,}",
        f"  Columns : {len(visible)}",
        f"  Memory  : {mem_str}",
        f"  Nulls   : {total_nulls:,} values across {null_cols} column(s)",
        "",
        f"  {'Column':<28} {'Type':<12} {'Nulls':<7} {'Unique':<8} {'Stats / Sample'}",
        "  " + "─" * 60,
    ]

    for col in visible:
        col_type = _classify(df[col])
        null_p = _null_pct(df[col])
        unique = f"{df[col].nunique():,}"
        stats = _stats(df[col], col_type)

        # Truncate long column names
        col_label = col[:26] + ".." if len(col) > 28 else col
        type_label = col_type[:10]

        lines.append(
            f"  {col_label:<28} {type_label:<12} {null_p:<7} {unique:<8} {stats}"
        )

    lines.append("")
    return "\n".join(lines)


class DataProfiler:
    """
    Profiles the loaded dataset and returns a formatted string
    ready to display in the TUI.
    """

    def run(self, context: dict) -> str:
        df = context.get("dataframe")
        sheet_dfs = context.get("sheet_dataframes", {})
        excel_sheets = context.get("excel_sheets", [])
        file_path = context.get("file_path", "dataset")

        if df is None:
            return "❌ No dataset loaded."

        import os

        fname = os.path.basename(file_path) if file_path else "dataset"

        sections = []

        if sheet_dfs and len(sheet_dfs) > 1:
            # Multi-sheet: overall summary (no per-column table — misleading due to outer join)
            total_rows = sum(len(s) for s in sheet_dfs.values())
            try:
                mem_kb = df.memory_usage(deep=True).sum() / 1024
                mem_str = (
                    f"{mem_kb / 1024:.1f} MB" if mem_kb > 1024 else f"{mem_kb:.0f} KB"
                )
            except Exception:
                mem_str = "—"

            summary = [
                "",
                f"📊 Overall Profile — {fname}",
                "━" * 62,
                f"  Sheets  : {len(excel_sheets)}  ({', '.join(excel_sheets)})",
                f"  Total rows (across all sheets): {total_rows:,}",
                f"  Memory  : {mem_str}",
                "",
                f"  Sheet breakdown:",
            ]
            for sheet, sdf in sheet_dfs.items():
                visible = [c for c in sdf.columns if c != "_sheet"]
                summary.append(
                    f"    • {sheet:<20} {len(sdf):>6,} rows  ·  {len(visible)} columns"
                )
            summary.append("")
            sections.append("\n".join(summary))

            # Then full per-sheet profiles
            for sheet, sdf in sheet_dfs.items():
                sections.append(_profile_df(sdf, f"Sheet: {sheet}"))
        else:
            # Single sheet or CSV
            sheet_label = excel_sheets[0] if excel_sheets else ""
            title = f"{fname}" + (f" — {sheet_label}" if sheet_label else "")
            sections.append(_profile_df(df, title))

        return "\n".join(sections)
