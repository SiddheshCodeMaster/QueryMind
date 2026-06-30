"""
ParquetConnector — loads a single .parquet file into a DataFrame.

Parquet is a columnar format that preserves dtypes natively (unlike CSV,
which loses everything to strings). We still run smart_cast_df() as a
safety net for edge cases — e.g. a column stored as string that contains
packed dates, or numeric columns that came through as object dtype from
an upstream ETL process.

Does NOT support partitioned Parquet datasets (folders of multiple
.parquet files split by partition key) — only single files. A clear
error is shown if a directory is passed instead of a file.
"""

import pandas as pd
from pathlib import Path

from app.data.type_caster import smart_cast_df


def _normalize_col(col: str) -> str:
    return col.lower().strip().replace(" ", "_")


class ParquetConnector:
    """Loads a single .parquet file into a DataFrame."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def run(self, context: dict) -> dict:
        path = Path(self.file_path)

        # ── Guard: partitioned datasets (directories) not supported ───────
        if path.is_dir():
            context["error"] = (
                "This looks like a partitioned Parquet dataset (a folder of "
                ".parquet files), which QueryMind doesn't support yet.\n\n"
                "Point QueryMind at a single .parquet file instead, or "
                "combine your partitions into one file first:\n"
                "  import pandas as pd\n"
                "  df = pd.read_parquet('your_folder/')\n"
                "  df.to_parquet('combined.parquet')"
            )
            return context

        if not path.exists():
            context["error"] = f"File not found: {self.file_path}"
            return context

        # ── Load ─────────────────────────────────────────────────────────
        try:
            df = pd.read_parquet(self.file_path, engine="pyarrow")
        except ImportError:
            context["error"] = (
                "Parquet support requires pyarrow, which isn't installed.\n"
                "Run: pip install pyarrow"
            )
            return context
        except Exception as e:
            context["error"] = f"Failed to load Parquet file: {e}"
            return context

        if df.empty:
            context["error"] = "Parquet file is empty (0 rows)."
            return context

        # ── Normalise + smart cast (safety net; Parquet is usually already typed) ──
        df.columns = [_normalize_col(c) for c in df.columns]

        # Deduplicate columns if normalization caused collisions
        if df.columns.duplicated().any():
            dupes = df.columns[df.columns.duplicated()].unique().tolist()
            print(
                f"⚠️  Duplicate columns after normalization: {dupes} — keeping first occurrence"
            )
            df = df.loc[:, ~df.columns.duplicated()].copy()

        df = smart_cast_df(df)

        if len(df.columns) < 2:
            context["error"] = (
                f"Only 1 column found ('{df.columns[0]}'). "
                f"QueryMind needs at least a metric and a dimension column."
            )
            return context

        print(f"✅ Parquet loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")
        print(f"   Columns: {df.columns.tolist()}")

        context["dataframe"] = df
        context["schema"] = {
            "columns": [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
        }
        return context
