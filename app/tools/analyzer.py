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
            df = context["sheet_dataframes"][target_sheet].copy()
        else:
            df = context["dataframe"].copy()

        # ── Guard: columns must exist ─────────────────────────────────────
        all_columns = df.columns.tolist()
        visible_cols = [c for c in all_columns if c != "_sheet"]

        if not metric or metric not in all_columns:
            numeric_in_sheet = df.select_dtypes(include="number").columns.tolist()
            id_hints = {"id", "_id", "key", "code", "num", "no", "number"}
            real_numeric = [
                c for c in numeric_in_sheet if not any(h in c.lower() for h in id_hints)
            ]

            if target_sheet and not real_numeric:
                context["error"] = (
                    f"The '{target_sheet}' sheet has no numeric columns to measure.\n"
                    f"  Columns in this sheet: {visible_cols}\n\n"
                    f"This sheet is likely a lookup/reference table.\n"
                    f"Try querying a sheet that has numeric data, like Orders."
                )
            elif target_sheet and real_numeric:
                context["error"] = (
                    f"'{metric}' is not available in the '{target_sheet}' sheet.\n"
                    f"  Available numeric columns here: {real_numeric}\n"
                    f"  Try: 'top 5 by {real_numeric[0]} in {target_sheet}'"
                )
            else:
                context["error"] = (
                    f"Metric column '{metric}' not found.\n"
                    f"  Available columns: {visible_cols}"
                )
            return context

        # Hard guard: internal/system columns must never be used as dimension
        INTERNAL_COLS = {"_sheet"}
        if dimension in INTERNAL_COLS:
            context["error"] = (
                f"'{dimension}' is an internal system column and cannot be "
                f"used as a dimension.\n\n"
                f"  Please rephrase and specify a real dimension column.\n"
                f"  Available columns: {visible_cols}"
            )
            return context

        if not dimension or dimension not in all_columns:
            context["error"] = (
                f"Dimension column '{dimension}' not found.\n"
                f"  Available columns: {visible_cols}"
            )
            return context
        if not query_type:
            context["error"] = "No query type detected. Please rephrase your question."
            return context

        # ── Date granularity: group datetime columns by month/year/week ──
        # If the dimension is a datetime column, extract the requested period
        # so "which month" groups by month label, not individual dates.
        if pd.api.types.is_datetime64_any_dtype(df[dimension]):
            granularity = intent.get("time_granularity", "day")
            if granularity == "year":
                df[dimension] = df[dimension].dt.to_period("Y").astype(str)
            elif granularity == "month":
                df[dimension] = df[dimension].dt.to_period("M").astype(str)
            elif granularity == "week":
                df[dimension] = df[dimension].dt.to_period("W").astype(str)
            else:
                df[dimension] = df[dimension].dt.date.astype(str)
        else:
            # ── Clean categorical dimension ───────────────────────────────
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
                # Always sort by value so display and insight are consistent
                result = result.sort_values(ascending=ascending)

            elif query_type == "count":
                # Count rows per group — works on any column, no numeric metric needed
                result = (
                    df.groupby(dimension)
                    .size()
                    .sort_values(ascending=ascending)
                    .rename("count")
                    .astype(int)  # ensure int not float
                )
                context["count_mode"] = True

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
