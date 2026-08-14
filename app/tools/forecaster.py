"""
Forecaster — adaptive time series forecasting with auto model selection.

Three models, no external dependencies (numpy only):

1. Linear regression   — strong linear trend (R² typically ≥ 0.75)
2. Exponential smoothing (ETS) — flat/noisy data, weights recent values
3. Seasonal decomposition — data with repeating cycles (≥ 2 full periods)

The best model is chosen automatically by R². R² is always disclosed
so users know exactly how much to trust the projection.
"""

import numpy as np
import pandas as pd


# ── R² / fitness labels ───────────────────────────────────────────────────────


def _r2_label(r2: float) -> str:
    if r2 >= 0.85:
        return "the pattern in your data is clear — this projection is fairly reliable"
    if r2 >= 0.60:
        return "there's a general direction here, but don't treat the numbers as exact"
    if r2 >= 0.30:
        return "your data is quite variable — use this as a rough guide only"
    return "your data doesn't show a clear pattern — this projection is a guess"


def _trend_label(slope: float, mean: float, metric_label: str) -> str:
    if mean == 0:
        return f"{metric_label} is flat"
    pct = (slope / abs(mean)) * 100
    if abs(pct) < 0.5:
        return f"{metric_label} is flat (< 0.5% change per period)"
    direction = "growing" if slope > 0 else "declining"
    return f"{metric_label} is {direction} ({pct:+.1f}% avg change per period)"


# ── Period label inference ────────────────────────────────────────────────────


def _infer_granularity(index: pd.Index) -> str:
    if hasattr(index, "freq") and index.freq:
        freq = str(index.freq).upper()
        # pandas uses <MonthBegin>, <MonthEnd>, ME, MS etc.
        if any(k in freq for k in ("MONTH", "MS", "ME")):
            return "monthly"
        if any(k in freq for k in ("QUARTER", "QS", "QE", "QT")):
            return "quarterly"
        if any(k in freq for k in ("YEAR", "YS", "YE", "AS", "A-")):
            return "yearly"
        if any(k in freq for k in ("WEEK", "WS", "WE")):
            return "weekly"
        if "DAY" in freq or freq in ("D", "BD"):
            return "daily"
    return "monthly"  # sensible default for most business data


def _next_period_labels(last_val, n: int, granularity: str) -> list:
    try:
        if isinstance(last_val, (pd.Timestamp,)):
            if granularity == "monthly":
                dates = pd.date_range(
                    last_val + pd.DateOffset(months=1), periods=n, freq="MS"
                )
                return [d.strftime("%b %Y") for d in dates]
            elif granularity == "quarterly":
                dates = pd.date_range(
                    last_val + pd.DateOffset(months=3), periods=n, freq="QS"
                )
                return [f"Q{(d.month - 1) // 3 + 1} {d.year}" for d in dates]
            elif granularity == "yearly":
                return [str(last_val.year + i + 1) for i in range(n)]
            else:
                dates = pd.date_range(
                    last_val + pd.DateOffset(days=1), periods=n, freq="D"
                )
                return [d.strftime("%Y-%m-%d") for d in dates]
    except Exception:
        pass
    try:
        base = int(last_val)
        return [str(base + i + 1) for i in range(n)]
    except Exception:
        return [f"Period +{i + 1}" for i in range(n)]


# ── Model 1: Linear regression ────────────────────────────────────────────────


def _fit_linear(values: np.ndarray, n_future: int):
    x = np.arange(len(values))
    coeffs = np.polyfit(x, values, 1)
    y_pred = np.polyval(coeffs, x)
    ss_res = float(np.sum((values - y_pred) ** 2))
    ss_tot = float(np.sum((values - np.mean(values)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    fc = np.polyval(coeffs, np.arange(len(values), len(values) + n_future))
    slope = float(coeffs[0])
    return fc.tolist(), r2, "Linear regression", slope


# ── Model 2: Exponential smoothing ───────────────────────────────────────────


def _fit_ets(values: np.ndarray, n_future: int, alpha: float = 0.3):
    """
    Simple exponential smoothing.
    alpha controls how quickly old data is forgotten (0.3 = moderate memory).
    Good for noisy/flat data where the recent level matters most.
    """
    smoothed = np.zeros(len(values))
    smoothed[0] = values[0]
    for i in range(1, len(values)):
        smoothed[i] = alpha * values[i] + (1 - alpha) * smoothed[i - 1]

    ss_res = float(np.sum((values - smoothed) ** 2))
    ss_tot = float(np.sum((values - np.mean(values)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    last = float(smoothed[-1])
    trend = float((smoothed[-1] - smoothed[-3]) / 2) if len(smoothed) >= 3 else 0.0
    fc = [last + trend * (i + 1) for i in range(n_future)]
    slope = trend  # approximate slope per period
    return fc, r2, "Exponential smoothing", slope


# ── Model 3: Seasonal decomposition ──────────────────────────────────────────


def _fit_seasonal(values: np.ndarray, n_future: int, period: int = 12):
    """
    Decompose series into trend + seasonality, forecast each separately.
    Requires at least 2 full cycles (2 * period data points).
    Works for monthly, quarterly, or any fixed-period data.
    """
    n = len(values)
    if n < 2 * period:
        return None, 0.0, None, 0.0

    # Centred moving average for trend
    trend = np.convolve(values, np.ones(period) / period, mode="same")
    half = period // 2
    trend[:half] = trend[half]
    trend[-half:] = trend[-(half + 1)]

    # Seasonal indices
    detrended = values - trend
    s_idx = np.zeros(period)
    counts = np.zeros(period)
    for i in range(n):
        s_idx[i % period] += detrended[i]
        counts[i % period] += 1
    s_idx /= np.maximum(counts, 1)
    s_idx -= s_idx.mean()  # normalise

    # Linear trend on de-seasonalised series
    deseasonal = values - np.array([s_idx[i % period] for i in range(n)])
    x = np.arange(n)
    coeffs = np.polyfit(x, deseasonal, 1)
    slope = float(coeffs[0])

    # R² of full model
    recon = np.polyval(coeffs, x) + np.array([s_idx[i % period] for i in range(n)])
    ss_res = float(np.sum((values - recon) ** 2))
    ss_tot = float(np.sum((values - np.mean(values)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Forecast
    future_x = np.arange(n, n + n_future)
    fc = (
        np.polyval(coeffs, future_x) + np.array([s_idx[i % period] for i in future_x])
    ).tolist()

    return fc, r2, f"Seasonal decomposition (period={period})", slope


# ── Auto model selection ──────────────────────────────────────────────────────


def _select_best_model(values: np.ndarray, n_future: int, period: int = 12):
    """
    Try all applicable models and return the one with the highest R².
    Returns (forecast_vals, r2, model_name, slope).
    """
    candidates = []

    candidates.append(_fit_linear(values, n_future))
    candidates.append(_fit_ets(values, n_future))

    if len(values) >= 2 * period:
        fc, r2, name, slope = _fit_seasonal(values, n_future, period)
        if fc is not None:
            candidates.append((fc, r2, name, slope))

    # Pick highest R²
    return max(candidates, key=lambda c: c[1])


# ── Public API ────────────────────────────────────────────────────────────────


def forecast(result: pd.Series, n_periods: int = 6) -> dict:
    """
    Forecast n_periods ahead using the best-fitting model.

    Parameters
    ----------
    result    : pd.Series — analyzer result (index=time, values=metric)
    n_periods : int — how many future periods to project

    Returns
    -------
    dict with keys: enough_data, forecast_vals, forecast_labels, r2,
                    r2_label, trend_label, model_name, n_data_points,
                    granularity, _raw_values
    """
    if len(result) < 4:
        return {
            "enough_data": False,
            "reason": f"Only {len(result)} data point(s) — need at least 4 for a forecast.",
        }

    values = result.values.astype(float)

    # Infer seasonality period from granularity
    granularity = _infer_granularity(result.index)
    period_map = {"monthly": 12, "quarterly": 4, "weekly": 52, "daily": 7}
    period = period_map.get(granularity, 12)

    fc_vals, r2, model_name, slope = _select_best_model(values, n_periods, period)

    forecast_labels = _next_period_labels(result.index[-1], n_periods, granularity)
    metric_label = str(result.name or "value")

    return {
        "enough_data": True,
        "forecast_vals": fc_vals,
        "forecast_labels": forecast_labels,
        "r2": r2,
        "r2_label": _r2_label(r2),
        "trend_label": _trend_label(slope, float(np.mean(values)), metric_label),
        "model_name": model_name,
        "n_data_points": len(values),
        "granularity": granularity,
        "_raw_values": values.tolist(),
    }


def format_forecast(fc: dict, metric_label: str = "Value") -> str:
    """Format a forecast dict as a terminal-ready string."""
    if not fc.get("enough_data"):
        return f"🔮 Forecast unavailable: {fc.get('reason', 'not enough data.')}"

    vals = fc["forecast_vals"]
    labels = fc["forecast_labels"]
    r2 = fc["r2"]
    model = fc.get("model_name", "")
    granularity = fc.get("granularity", "period")
    abs_max = max(abs(v) for v in vals) if vals else 1

    CURRENCY_HINTS = {
        "sales",
        "revenue",
        "profit",
        "cost",
        "price",
        "spend",
        "spending",
        "spent",
        "amount",
        "earnings",
        "income",
        "fee",
        "charge",
        "payment",
        "salary",
        "wage",
        "budget",
    }
    is_currency = any(h in metric_label.lower() for h in CURRENCY_HINTS)

    _hist = fc.get("_raw_values", [])
    _all_whole = bool(_hist) and all(float(x) == int(float(x)) for x in _hist)

    def fmt(v):
        if is_currency:
            return f"${v:,.0f}"
        if _all_whole:
            return f"{round(v):,}"
        if abs(v) < 100:
            return f"{v:,.2f}"
        return f"{v:,.1f}"

    # Plain confidence word for the heading
    if r2 >= 0.85:
        conf_word = "high confidence"
    elif r2 >= 0.60:
        conf_word = "moderate confidence"
    elif r2 >= 0.30:
        conf_word = "low confidence"
    else:
        conf_word = "very uncertain"

    lines = [
        "",
        f"🔮 Forecast — Next {len(vals)} {granularity} periods ({conf_word})",
        "━" * 62,
    ]
    for label, val in zip(labels, vals):
        bar_len = int((abs(val) / max(abs_max, 1)) * 20)
        bar = "█" * max(bar_len, 1)
        lines.append(f"  {label:<16} {bar:<20} ~{fmt(val)}")

    model_plain = {
        "Linear regression": "straight-line trend",
        "Exponential smoothing": "recent-data weighted average",
    }
    # Seasonal decomp has dynamic name
    if "Seasonal" in model:
        model_plain_str = "seasonal pattern detection"
    else:
        model_plain_str = model_plain.get(model, model)

    lines += [
        "",
        f"  📈 {fc['trend_label'].capitalize()}",
        f"  💬 Confidence: {fc['r2_label']}",
        f"  🔍 How it was calculated: {model_plain_str}",
        f"  📋 Based on {fc['n_data_points']} past data points",
        f"  ⚠️  This is a projection — unexpected events won't be reflected",
        "",
    ]
    return "\n".join(lines)
