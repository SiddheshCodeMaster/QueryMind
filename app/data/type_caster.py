"""
Shared column type-casting logic used by both CSVConnector and ExcelConnector.

_smart_cast_df(df) processes every column:
  - Already datetime  → leave alone
  - Already numeric   → run packed-date check, otherwise leave
  - Object/string     → try numeric → then packed-date check
"""

import pandas as pd


def _try_packed_date(int_series: pd.Series, original_series: pd.Series):
    """
    Given a Series of integers, try to parse as a packed date
    (DDMMYYYY, MMDDYYYY, YYYYMMDD) with zero-padding for 7-digit values.

    Returns a datetime Series if successful, None otherwise.
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

            # Re-apply to the full original column (preserving NaN positions)
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


def smart_cast_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intelligently cast each column to the most appropriate type.

    Processing order per column:
    1. Already datetime → skip
    2. Numeric dtype (int/float from Excel) → packed-date check first,
       then leave as-is if not a date
    3. Object/string → try numeric cast (>70% parseable),
       then packed-date check on the numeric result
    """
    for col in df.columns:
        dtype_str = str(df[col].dtype)

        # Already datetime — nothing to do
        if "datetime" in dtype_str:
            continue

        # ── Already numeric (common with Excel-loaded int columns) ────────
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

        # ── Object / string → try numeric cast first ─────────────────────
        if df[col].dtype == object or dtype_str == "string":
            converted = pd.to_numeric(df[col], errors="coerce")
            ratio = converted.notna().sum() / max(len(df), 1)

            if ratio <= 0.7:
                continue  # Not numeric enough — leave as object

            int_series = converted.dropna().astype("int64")
            if len(int_series) > 0:
                result = _try_packed_date(int_series, df[col])
                if result is not None:
                    dt_col, fmt = result
                    df[col] = dt_col
                    print(f"📅 '{col}' detected as packed date ({fmt})")
                    continue

            df[col] = converted  # plain numeric

    return df
