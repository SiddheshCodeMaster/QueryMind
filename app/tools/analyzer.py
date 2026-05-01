import pandas as pd


class Analyzer:
    """
    Executes the structured intent produced by the interpreter.

    Sheet-aware: if context["intent"]["sheet"] is set (e.g. the user said
    "in sheet Orders"), only that sheet's rows are used for analysis.
    Otherwise the full combined dataframe is used.

    Supported query types
    ---------------------
    comparison  – groupby dimension, sum metric, sort descending
    top_n       – like comparison, limited to N rows
    aggregation – groupby dimension, mean or sum
    trend       – groupby time dimension, sum, sort by index
    """

    def run(self, context: dict) -> dict:
        intent = context.get("intent", {})

        metric = intent.get("metric")
        dimension = intent.get("dimension")
        query_type = intent.get("query_type")
        target_sheet = intent.get("sheet")  # set by InterpreterAgent for sheet queries

        # ── Sheet-aware dataframe selection ──────────────────────────────
        if target_sheet and target_sheet in context.get("sheet_dataframes", {}):
            # Use only that sheet's dataframe
            df = context["sheet_dataframes"][target_sheet].copy()
        else:
            df = context["dataframe"].copy()

        # ── Guard: columns must exist ─────────────────────────────────────
        all_columns = df.columns.tolist()

        if not metric or metric not in all_columns:
            context["error"] = (
                f"Metric column '{metric}' not found.\n"
                f"Available: {[c for c in all_columns if c != '_sheet']}"
            )
            return context

        if not dimension or dimension not in all_columns:
            context["error"] = (
                f"Dimension column '{dimension}' not found.\n"
                f"Available: {[c for c in all_columns if c != '_sheet']}"
            )
            return context

        if not query_type:
            context["error"] = "No query type detected. Please rephrase your question."
            return context

        # ── Clean dimension ───────────────────────────────────────────────
        df[dimension] = (
            df[dimension]
            .astype(str)
            .str.strip()
            .replace(["ERROR", "UNKNOWN", "Unknown", "nan", ""], "Unknown")
        )

        # ── Coerce metric to numeric ──────────────────────────────────────
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        df = df.dropna(subset=[metric])

        if df.empty:
            context["error"] = f"No numeric data found in '{metric}' after cleaning."
            return context

        # ── Run analysis ──────────────────────────────────────────────────
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
                op = intent.get("operation", "sum")
                result = (
                    df.groupby(dimension)[metric].mean()
                    if op == "mean"
                    else df.groupby(dimension)[metric].sum()
                )

            elif query_type == "trend":
                result = df.groupby(dimension)[metric].sum().sort_index()

            else:
                context["error"] = f"Unsupported query type: '{query_type}'"
                return context

            context["analysis"] = result
            context["target_sheet"] = target_sheet  # for InsightGenerator label
            return context

        except Exception as e:
            context["error"] = f"Analysis failed: {e}"
            return context
