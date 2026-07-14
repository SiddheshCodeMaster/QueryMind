"""
Forecaster — linear trend extrapolation for time series data.

Uses numpy.polyfit (already a pandas dependency — no new packages
required). Discloses R² so users know how much to trust the forecast.

Designed for small tabular datasets (100-5000 rows), not deep learning.
"""

import numpy as np
import pandas as pd
from datetime import datetime


# ── R² fitness labels ────────────────────────────────────────────────────────

def _r2_label(r2: float) -> str:
    if r2 >= 0.85: return "strong fit — forecast is reasonably reliable"
    if r2 >= 0.60: return "moderate fit — treat as directional, not precise"
    if r2 >= 0.30: return "weak fit — high uncertainty, use with caution"
    return "poor fit — data is too noisy to forecast reliably"


def _trend_label(slope: float, mean: float, metric_label: str) -> str:
    if mean == 0:
        return "flat"
    pct = (slope / abs(mean)) * 100
    if abs(pct) < 0.5:
        return f"{metric_label} is flat (< 0.5% monthly change)"
    direction = "growing" if slope > 0 else "declining"
    return f"{metric_label} is {direction} ({pct:+.1f}% avg change per period)"


# ── Period label inference ───────────────────────────────────────────────────

def _infer_granularity(index: pd.Index) -> str:
    """Guess if the index represents months, quarters, years, or other."""
    if hasattr(index, 'freq') and index.freq:
        freq = str(index.freq).upper()
        if "MS" in freq or "M" in freq:  return "monthly"
        if "Q"  in freq:                 return "quarterly"
        if "Y"  in freq or "A" in freq:  return "yearly"
        if "W"  in freq:                 return "weekly"
        if "D"  in freq:                 return "daily"
    return "period"


def _next_period_labels(last_index_val, n: int, granularity: str) -> list:
    """Generate n future period labels from the last known index value."""
    try:
        if isinstance(last_index_val, (pd.Timestamp, datetime)):
            if granularity == "monthly":
                dates = pd.date_range(
                    last_index_val + pd.DateOffset(months=1),
                    periods=n, freq="MS"
                )
                return [d.strftime("%b %Y") for d in dates]
            elif granularity == "quarterly":
                dates = pd.date_range(
                    last_index_val + pd.DateOffset(months=3),
                    periods=n, freq="QS"
                )
                return [d.strftime("Q%q %Y") for d in dates]
            elif granularity == "yearly":
                return [str(last_index_val.year + i + 1) for i in range(n)]
            else:
                dates = pd.date_range(
                    last_index_val + pd.DateOffset(days=1),
                    periods=n, freq="D"
                )
                return [d.strftime("%Y-%m-%d") for d in dates]
    except Exception:
        pass
    # Fallback: integer or string index → just number the future periods
    try:
        base = int(last_index_val)
        return [str(base + i + 1) for i in range(n)]
    except Exception:
        return [f"Period +{i+1}" for i in range(n)]


# ── Main forecast function ───────────────────────────────────────────────────

def forecast(result: pd.Series, n_periods: int = 6) -> dict:
    """
    Fit a linear trend to a time series result and extrapolate n_periods ahead.

    Parameters
    ----------
    result    : pd.Series — the aggregated result from the Analyzer
                (index = time periods, values = metric values)
    n_periods : int — how many future periods to forecast (default 6)

    Returns
    -------
    dict with keys:
        forecast_vals   : list of float — predicted values
        forecast_labels : list of str   — period labels
        slope           : float
        r2              : float
        r2_label        : str
        trend_label     : str
        n_data_points   : int
        granularity     : str
        enough_data     : bool — False if < 4 data points (unreliable)
    """
    # Need at least 4 points for a meaningful trend
    if len(result) < 4:
        return {
            "enough_data": False,
            "reason": f"Only {len(result)} data point(s) — need at least 4 for a forecast.",
        }

    values = result.values.astype(float)
    x      = np.arange(len(values))

    # Fit linear regression
    coeffs           = np.polyfit(x, values, 1)
    slope, intercept = coeffs

    # R²
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((values - y_pred) ** 2)
    ss_tot = np.sum((values - np.mean(values)) ** 2)
    r2     = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    # Future values
    forecast_x    = np.arange(len(values), len(values) + n_periods)
    # No floor — negative values are valid for some metrics (profit/loss, temperature)
    forecast_vals = [float(v) for v in np.polyval(coeffs, forecast_x)]

    # Period labels
    granularity    = _infer_granularity(result.index)
    forecast_labels = _next_period_labels(result.index[-1], n_periods, granularity)

    metric_label = result.name or "value"

    return {
        "enough_data":    True,
        "forecast_vals":  forecast_vals,
        "forecast_labels": forecast_labels,
        "slope":          float(slope),
        "r2":             r2,
        "r2_label":       _r2_label(r2),
        "trend_label":    _trend_label(slope, float(np.mean(values)), str(metric_label)),
        "n_data_points":  len(values),
        "granularity":    granularity,
        "_raw_values":    values.tolist(),   # used by format_forecast for int detection
    }


def format_forecast(fc: dict, metric_label: str = "Value") -> str:
    """
    Format a forecast dict as a terminal-ready string.
    Returns an error string if enough_data is False.
    """
    if not fc.get("enough_data"):
        return f"🔮 Forecast unavailable: {fc.get('reason', 'not enough data.')}"

    vals   = fc["forecast_vals"]
    labels = fc["forecast_labels"]
    r2     = fc["r2"]
    abs_max = max(vals) if max(vals) > 0 else 1

    # Currency detection — only use $ if the metric name suggests money.
    # Same logic as InsightGenerator so formatting is consistent everywhere.
    CURRENCY_HINTS = {
        "sales", "revenue", "profit", "cost", "price", "spend",
        "spending", "spent", "amount", "earnings", "income",
        "fee", "charge", "payment", "salary", "wage", "budget",
    }
    is_currency = any(h in metric_label.lower() for h in CURRENCY_HINTS)

    # Check if historical values were all whole numbers — outside fmt() so
    # it's computed once and captured correctly by the closure
    _hist_vals = fc.get("_raw_values", [])
    _all_whole = (
        bool(_hist_vals)
        and all(float(x) == int(float(x)) for x in _hist_vals if not np.isnan(x))
    )

    def fmt(v):
        """Format a value appropriately for the metric type."""
        if is_currency:
            return f"${v:,.0f}"
        if _all_whole:
            return f"{round(v):,}"
        if abs(v) < 100:
            return f"{v:,.2f}"
        return f"{v:,.1f}"

    lines = [
        f"",
        f"🔮 Forecast — Next {len(vals)} periods (Linear Regression, R²={r2:.2f})",
        "━" * 62,
    ]
    for label, val in zip(labels, vals):
        bar_len = int((val / abs_max) * 20)
        bar     = "█" * bar_len
        lines.append(f"  {label:<16} {bar:<20} ~{fmt(val)}")

    lines += [
        "",
        f"  📊 {fc['trend_label'].capitalize()}",
        f"  🎯 R² = {r2:.2f} — {fc['r2_label']}",
        f"  📋 Based on {fc['n_data_points']} historical data points",
        f"  ⚠️  Linear extrapolation only — external factors not modelled",
        "",
    ]
    return "\n".join(lines)