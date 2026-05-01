import pandas as pd


def _normalize_col(col: str) -> str:
    return col.lower().strip().replace(" ", "_")


def _auto_cast(df: pd.DataFrame) -> pd.DataFrame:
    """Mirror CSVConnector: if >70% of a column parses as numeric, cast it."""
    for col in df.columns:
        if df[col].dtype == object or str(df[col].dtype) == "string":
            converted = pd.to_numeric(df[col], errors="coerce")
            ratio = converted.notna().sum() / max(len(df), 1)
            if ratio > 0.7:
                df[col] = converted
    return df


class ExcelConnector:
    """
    Loads one or more sheets from an .xlsx / .xls file.

    Context keys written
    --------------------
    dataframe        - combined (or single-sheet) DataFrame
    schema           - {"columns": [{"name": ..., "type": ...}]}
    excel_sheets     - list of sheet names actually loaded
    excel_mode       - "single" | "multi"
    sheet_dataframes - dict[sheet_name -> DataFrame]
    """

    def __init__(self, file_path: str, selected_sheets: list):
        self.file_path = file_path
        self.selected_sheets = selected_sheets

    def run(self, context: dict) -> dict:
        try:
            xl = pd.ExcelFile(self.file_path)
        except Exception as e:
            context["error"] = f"Cannot open Excel file: {e}"
            return context

        available = xl.sheet_names
        invalid = [s for s in self.selected_sheets if s not in available]
        if invalid:
            context["error"] = f"Sheet(s) not found: {invalid}. Available: {available}"
            return context

        sheet_dfs = {}
        for sheet in self.selected_sheets:
            try:
                df = xl.parse(sheet)
                df.columns = [_normalize_col(c) for c in df.columns]
                df = _auto_cast(df)
                sheet_dfs[sheet] = df
            except Exception as e:
                context["error"] = f"Failed to parse sheet '{sheet}': {e}"
                return context

        mode = "single" if len(self.selected_sheets) == 1 else "multi"

        if mode == "single":
            sheet_name = self.selected_sheets[0]
            combined = sheet_dfs[sheet_name].copy()
            combined["_sheet"] = sheet_name
        else:
            frames = []
            for sheet, df in sheet_dfs.items():
                df = df.copy()
                df["_sheet"] = sheet
                frames.append(df)
            # outer-union all sheets; NaN fills columns missing in some sheets
            combined = pd.concat(frames, ignore_index=True, sort=False)

        print(f"✅ Excel loaded ({mode}): {self.selected_sheets}")
        print(f"   Shape: {combined.shape}  Cols: {combined.columns.tolist()}")

        context["dataframe"] = combined
        context["sheet_dataframes"] = sheet_dfs
        context["excel_sheets"] = self.selected_sheets
        context["excel_mode"] = mode
        context["schema"] = {
            "columns": [
                {"name": col, "type": str(combined[col].dtype)}
                for col in combined.columns
            ]
        }
        return context
