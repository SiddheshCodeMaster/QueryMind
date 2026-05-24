"""
Shared column type-casting logic used by both CSVConnector and ExcelConnector.

smart_cast_df(df) processes every column:
  - Already datetime  → leave alone
  - Already numeric   → packed-date check, then whole-number downcast
  - Object/string     → try numeric → packed-date check → whole-number downcast
"""

import pandas as pd


def _try_packed_date(int_series: pd.Series, original_series: pd.Series):
    """
    Try to parse an integer series as a packed date
    (DDMMYYYY, MMDDYYYY, YYYYMMDD) with zero-padding for 7-digit values.

    Returns (datetime_series, fmt) if successful, None otherwise.
    """
    digits = int_series.astype(str).str.len()
    mostly_7_8 = ((digits >= 7) & (digits <= 8)).sum() / len(digits)

    if mostly_7_8 <= 0.8:
        return None

    padded = int_series.astype(str).str.zfill(8)

    for fmt in ("%d%m%Y", "%m%d%Y", "%Y%m%d"):
        try:
            candidate = pd.to_datetime(padded, format=fmt, errors="raise")
            if not (
                (candidate.dt.year >= 1900).all() and (candidate.dt.year <= 2100).all()
            ):
                continue

            full_padded = (
                pd.to_numeric(original_series, errors="coerce")
                .astype("Int64")
                .astype(str)
                .str.zfill(8)
                .replace("<NA>", pd.NaT)
            )
            result = pd.to_datetime(full_padded, format=fmt, errors="coerce")
            return result, fmt

        except Exception:
            continue

    return None


def _try_downcast_to_int(series: pd.Series) -> pd.Series:
    """
    If all non-null values in a float series are whole numbers
    (e.g. 553.0, 1733.0), convert to nullable Int64 so they
    display as 553, 1733 instead of 553.0, 1733.0.

    Uses Int64 (nullable) rather than int64 so NaN rows are preserved.
    """
    if series.dtype not in ("float64", "float32"):
        return series

    non_null = series.dropna()
    if len(non_null) == 0:
        return series

    if (non_null == non_null.astype("int64")).all():
        return series.astype("Int64")

    return series


def smart_cast_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intelligently cast each column to the most appropriate type.

    Processing order per column:
    1. Already datetime → skip
    2. Numeric dtype (int/float from Excel) → packed-date check,
       then whole-number float → Int64 downcast
    3. Object/string → try numeric cast (>70% parseable),
       then packed-date check, then whole-number downcast
    """
    for col in df.columns:
        dtype_str = str(df[col].dtype)

        # Already datetime — nothing to do
        if "datetime" in dtype_str:
            continue

        # ── Already numeric (common with Excel-loaded columns) ────────────
        if df[col].dtype in ("int64", "int32", "float64", "float32", "Int64", "Int32"):
            int_series = (
                pd.to_numeric(df[col], errors="coerce").dropna().astype("int64")
            )
            if len(int_series) > 0:
                result = _try_packed_date(int_series, df[col])
                if result is not None:
                    dt_col, fmt = result
                    df[col] = dt_col
                    print(f"📅 '{col}' detected as packed date ({fmt})")
                    continue

            # Downcast whole-number floats to Int64
            df[col] = _try_downcast_to_int(df[col])
            continue

        # ── Object / string → try numeric cast first ──────────────────────
        if df[col].dtype == object or dtype_str in ("string", "str"):
            converted = pd.to_numeric(df[col], errors="coerce")
            ratio = converted.notna().sum() / max(len(df), 1)

            if ratio <= 0.7:
                continue  # Not numeric enough — leave as object/string

            int_series = converted.dropna().astype("int64")
            if len(int_series) > 0:
                result = _try_packed_date(int_series, df[col])
                if result is not None:
                    dt_col, fmt = result
                    df[col] = dt_col
                    print(f"📅 '{col}' detected as packed date ({fmt})")
                    continue

            # Downcast whole-number floats before storing
            df[col] = _try_downcast_to_int(converted)

    return df
