"""
Shared column type-casting logic used by CSVConnector, ExcelConnector,
and ParquetConnector.

smart_cast_df(df) processes every column:
  - Already datetime  → leave alone
  - Boolean           → leave alone
  - Already numeric   → packed-date check, then whole-number downcast
  - Object/string     → try currency/pct clean → numeric cast →
                        packed-date check → whole-number downcast
"""

import re
import pandas as pd


# ── Currency / percentage cleaning ──────────────────────────────────────────

_CURRENCY_RE = re.compile(r"[$€£¥₹,\s]")  # chars to strip from currency
_PCT_RE = re.compile(r"^\s*-?[\d.]+\s*%\s*$")  # e.g. "12%" or "-3.5%"
_CURRENCY_DETECT = re.compile(r"^\s*[$€£¥₹]")  # starts with currency symbol


def _try_clean_numeric(series: pd.Series) -> pd.Series | None:
    """
    Try to coerce a string column to numeric by:
    1. Stripping currency symbols and thousands commas  ($1,234.56 → 1234.56)
    2. Stripping percentage signs and dividing by 100   (12% → 0.12)

    Returns cleaned numeric Series if successful, None otherwise.
    Uses a 60% parseable threshold (lower than the raw threshold because
    we're pre-cleaning the values first).
    """
    sample = series.dropna().head(50).astype(str)
    if len(sample) == 0:
        return None

    # Detect if column looks like currency or percentage
    is_currency = sample.str.match(_CURRENCY_DETECT).sum() / len(sample) > 0.5
    is_pct = sample.str.match(_PCT_RE).sum() / len(sample) > 0.5

    if not is_currency and not is_pct:
        return None

    if is_pct:
        cleaned = series.astype(str).str.replace("%", "", regex=False).str.strip()
        converted = pd.to_numeric(cleaned, errors="coerce") / 100
    else:
        cleaned = (
            series.astype(str).str.strip().str.replace(_CURRENCY_RE, "", regex=True)
        )
        converted = pd.to_numeric(cleaned, errors="coerce")

    ratio = converted.notna().sum() / max(len(series), 1)
    return converted if ratio >= 0.60 else None


# ── Packed date detection ────────────────────────────────────────────────────


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


# ── Whole-number downcast ────────────────────────────────────────────────────


def _try_downcast_to_int(series: pd.Series) -> pd.Series:
    """
    If all non-null values in a float series are whole numbers
    (e.g. 553.0, 1733.0), convert to Int64 so they display as 553, 1733.
    Uses Int64 (nullable) rather than int64 to handle NaN rows.
    """
    if series.dtype not in ("float64", "float32"):
        return series
    non_null = series.dropna()
    if len(non_null) == 0:
        return series
    try:
        if (non_null == non_null.astype("int64")).all():
            return series.astype("Int64")
    except (OverflowError, ValueError):
        pass
    return series


# ── Main function ────────────────────────────────────────────────────────────


def smart_cast_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intelligently cast each column to the most appropriate type.

    Safety: deduplicates column names first — duplicate names cause
    df[col] to return a DataFrame instead of a Series, crashing .dtype.

    Processing order per column:
    1. Already datetime or boolean → skip
    2. Already numeric (int/float) → packed-date check, then int downcast
    3. Object/string:
       a. Try currency/pct cleaning first ($1,234.56 → 1234.56; 12% → 0.12)
       b. Try raw numeric cast (>60% parseable threshold)
       c. Packed-date check on result
       d. Whole-number downcast
    """
    # ── Dedup first — duplicate col names crash .dtype ────────────────────
    if df.columns.duplicated().any():
        dupes = df.columns[df.columns.duplicated()].unique().tolist()
        print(f"⚠️  Duplicate columns in smart_cast_df: {dupes} — keeping first")
        df = df.loc[:, ~df.columns.duplicated()].copy()

    for col in df.columns:
        col_data = df[col]

        # Extra safety: if somehow still a DataFrame, take first column
        if isinstance(col_data, pd.DataFrame):
            col_data = col_data.iloc[:, 0]
            df[col] = col_data

        dtype_str = str(col_data.dtype)

        # ── 1. Already datetime or boolean → skip ─────────────────────────
        if "datetime" in dtype_str or dtype_str == "bool":
            continue

        # ── 2. Already numeric ────────────────────────────────────────────
        if col_data.dtype in ("int64", "int32", "float64", "float32", "Int64", "Int32"):
            int_series = pd.to_numeric(col_data, errors="coerce").dropna()
            if len(int_series) > 0:
                try:
                    result = _try_packed_date(int_series.astype("int64"), col_data)
                    if result is not None:
                        df[col] = result[0]
                        print(f"📅 '{col}' detected as packed date ({result[1]})")
                        continue
                except Exception:
                    pass
            df[col] = _try_downcast_to_int(col_data)
            continue

        # ── 3. Object / string ────────────────────────────────────────────
        if col_data.dtype == object or dtype_str in ("string", "str"):
            # 3a. Currency / percentage cleaning
            cleaned = _try_clean_numeric(col_data)
            if cleaned is not None:
                df[col] = _try_downcast_to_int(cleaned)
                continue

            # 3b. Raw numeric cast (with slightly relaxed 60% threshold
            #     since N/A, "-", "n/a" are common non-numeric values)
            converted = pd.to_numeric(col_data, errors="coerce")
            ratio = converted.notna().sum() / max(len(col_data), 1)

            if ratio < 0.60:
                continue  # not numeric enough — leave as string

            # 3c. Packed date check
            int_series = converted.dropna()
            if len(int_series) > 0:
                try:
                    result = _try_packed_date(int_series.astype("int64"), col_data)
                    if result is not None:
                        df[col] = result[0]
                        print(f"📅 '{col}' detected as packed date ({result[1]})")
                        continue
                except Exception:
                    pass

            # 3d. Whole-number downcast
            df[col] = _try_downcast_to_int(converted)

    return df
