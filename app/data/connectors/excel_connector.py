import pandas as pd
from app.data.type_caster import smart_cast_df


def _normalize_col(col: str) -> str:
    return col.lower().strip().replace(" ", "_")


class ExcelConnector:
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
                df = smart_cast_df(df)  # ← shared smart caster
                sheet_dfs[sheet] = df
            except Exception as e:
                context["error"] = f"Failed to parse sheet '{sheet}': {e}"
                return context

        mode = "single" if len(self.selected_sheets) == 1 else "multi"

        if mode == "single":
            combined = sheet_dfs[self.selected_sheets[0]].copy()
            combined["_sheet"] = self.selected_sheets[0]
        else:
            frames = []
            for sheet, df in sheet_dfs.items():
                df = df.copy()
                df["_sheet"] = sheet
                frames.append(df)
            combined = pd.concat(frames, ignore_index=True, sort=False)

        print(f"✅ Excel loaded ({mode}): {self.selected_sheets}")
        print(f"   Shape: {combined.shape}  Cols: {combined.columns.tolist()}")
        print(f"   Dtypes: {combined.dtypes.to_dict()}")

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
