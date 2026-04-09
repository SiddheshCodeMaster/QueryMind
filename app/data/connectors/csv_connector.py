import pandas as pd


class CSVConnector:
    def __init__(self, file_path):
        self.file_path = file_path

    def run(self, context):
        try:
            df = pd.read_csv(self.file_path)

            context["dataframe"] = df
            context["schema"] = {
                "columns": [
                    {"name": col, "type": str(df[col].dtype)} for col in df.columns
                ]
            }

            return context

        except Exception as e:
            context["error"] = str(e)
            return context
