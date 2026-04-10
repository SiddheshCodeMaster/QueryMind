import pandas as pd


class CSVConnector:
    def __init__(self, file_path):
        self.file_path = file_path

    def run(self, context):
        try:
            df = pd.read_csv(self.file_path)

            # Normalize column names
            df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]

            # 🔥 Auto-detect numeric columns (NO HARDCODING)
            for col in df.columns:
                converted = pd.to_numeric(df[col], errors="coerce")

                non_null_ratio = converted.notna().sum() / len(df)

                if non_null_ratio > 0.7:
                    df[col] = converted

            context["dataframe"] = df
            context["schema"] = {
                "columns": [
                    {"name": col, "type": str(df[col].dtype)} for col in df.columns
                ]
            }

            print("✅ Columns detected:", df.columns.tolist())
            print("📊 Data types:", df.dtypes)

            return context

        except Exception as e:
            context["error"] = str(e)
            return context
