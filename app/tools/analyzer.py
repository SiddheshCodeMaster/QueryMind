import pandas as pd


class Analyzer:
    """
    Executes the structured intent produced by the interpreter.

    Supported query types
    ---------------------
    comparison  – group by dimension, sum metric, sort descending
    top_n       – like comparison but limited to N rows
                  (ascending=True in intent → bottom N)
    aggregation – group by dimension, apply mean or sum
    trend       – group by time dimension, sum metric, sort by index
    """

    def run(self, context):
        df = context["dataframe"].copy()  # avoid mutating the shared base df
        intent = context.get("intent", {})

        metric = intent.get("metric")
        dimension = intent.get("dimension")
        query_type = intent.get("query_type")

        # ---------------------------------------------------------------
        # Guard: both metric and dimension must be present and valid
        # ---------------------------------------------------------------
        all_columns = df.columns.tolist()

        if not metric or metric not in all_columns:
            context["error"] = (
                f"Metric column '{metric}' not found in dataset. "
                f"Available columns: {all_columns}"
            )
            return context

        if not dimension or dimension not in all_columns:
            context["error"] = (
                f"Dimension column '{dimension}' not found in dataset. "
                f"Available columns: {all_columns}"
            )
            return context

        if not query_type:
            context["error"] = "No query type detected. Please rephrase your question."
            return context

        # ---------------------------------------------------------------
        # Clean dimension column
        # ---------------------------------------------------------------
        df[dimension] = (
            df[dimension]
            .astype(str)
            .str.strip()
            .replace(["ERROR", "UNKNOWN", "Unknown", "nan", ""], "Unknown")
        )

        # ---------------------------------------------------------------
        # Drop rows where metric is null (only drop on metric, not all cols)
        # ---------------------------------------------------------------
        df = df.dropna(subset=[metric])

        # ---------------------------------------------------------------
        # Coerce metric to numeric (safety net for mixed-type CSVs)
        # ---------------------------------------------------------------
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        df = df.dropna(subset=[metric])

        try:
            ascending = intent.get("ascending", False)

            if query_type == "comparison":
                result = (
                    df.groupby(dimension)[metric].sum().sort_values(ascending=ascending)
                )

            elif query_type == "top_n":
                n = intent.get("limit") or 5
                result = (
                    df.groupby(dimension)[metric]
                    .sum()
                    .sort_values(ascending=ascending)
                    .head(n)
                )

            elif query_type == "aggregation":
                operation = intent.get("operation", "sum")
                if operation == "mean":
                    result = df.groupby(dimension)[metric].mean()
                else:
                    result = df.groupby(dimension)[metric].sum()

            elif query_type == "trend":
                result = df.groupby(dimension)[metric].sum().sort_index()

            else:
                context["error"] = f"Unsupported query type: '{query_type}'"
                return context

            context["analysis"] = result
            return context

        except Exception as e:
            context["error"] = f"Analysis failed: {e}"
            return context
