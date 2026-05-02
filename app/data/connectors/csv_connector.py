import pandas as pd
import chardet
from app.data.type_caster import smart_cast_df


def _detect_encoding(file_path: str) -> str:
    """
    Detect file encoding.
    Checks for BOM first (catches Excel-exported UTF-8 files),
    then falls back to chardet for other encodings (latin-1, cp1252, etc.)
    """
    with open(file_path, "rb") as f:
        raw = f.read(4096)

    # UTF-8 BOM — most common cause of \ufeff in column names
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    # UTF-16 BOMs
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"

    detected = chardet.detect(raw)
    return detected.get("encoding") or "utf-8"


def _detect_delimiter(file_path: str, encoding: str) -> str:
    """
    Detect delimiter by counting occurrences in the first line.
    Handles comma, semicolon, tab, pipe — in that priority order on ties.
    """
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            first_line = f.readline()
    except Exception:
        return ","

    candidates = {",": 0, ";": 0, "\t": 0, "|": 0}
    for delim in candidates:
        candidates[delim] = first_line.count(delim)

    best = max(candidates, key=candidates.get)
    return best if candidates[best] > 0 else ","


class CSVConnector:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def run(self, context: dict) -> dict:
        try:
            encoding = _detect_encoding(self.file_path)
            delimiter = _detect_delimiter(self.file_path, encoding)

            print(f"📄 CSV encoding={encoding}  delimiter={repr(delimiter)}")

            try:
                df = pd.read_csv(
                    self.file_path,
                    encoding=encoding,
                    sep=delimiter,
                    on_bad_lines="warn",  # skip malformed rows, don't crash
                )
            except pd.errors.EmptyDataError:
                context["error"] = (
                    f"'{self.file_path}' is completely empty. "
                    f"Please provide a file with headers and at least one row of data."
                )
                return context

            # Guard: headers-only (parsed fine but zero rows)
            if df.empty:
                context["error"] = (
                    f"'{self.file_path}' contains only headers and no data rows. "
                    f"Please provide a file with at least one row of data."
                )
                return context

            # Normalize column names
            df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]

            # Smart cast: numeric + packed-date detection (shared logic)
            df = smart_cast_df(df)

            context["dataframe"] = df
            context["schema"] = {
                "columns": [
                    {"name": col, "type": str(df[col].dtype)} for col in df.columns
                ]
            }

            print("✅ Columns detected:", df.columns.tolist())
            print("📊 Data types:\n", df.dtypes.to_string())

            return context

        except Exception as e:
            context["error"] = f"Failed to load CSV: {e}"
            return context
