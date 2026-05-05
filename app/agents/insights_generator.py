import pandas as pd


class InsightGenerator:
    """
    Converts a raw analysis Series into a human-readable insight string.
    Respects intent["ascending"] for direction-aware language.
    """

    def run(self, context):
        result = context.get("analysis")
        intent = context.get("intent")

        if result is None or intent is None:
            return context

        try:
            metric = intent.get("metric", "value")
            dimension = intent.get("dimension", "category")
            query_type = intent.get("query_type", "aggregation")
            operation = intent.get("operation", "sum")
            ascending = intent.get("ascending", False)

            # Normalise to Series
            if isinstance(result, pd.DataFrame):
                result = result.squeeze()

            if not isinstance(result, pd.Series) or result.empty:
                return context

            # --- Human-readable labels ---
            metric_label = metric.replace("_", " ").title()
            dimension_label = dimension.replace("_", " ").title()
            op_label = "Average" if operation == "mean" else "Total"

            total = result.sum()
            abs_max = result.abs().max() or 1

            # Always display table high→low for non-trend queries.
            # Always derive featured item from idxmax/idxmin — never rely
            # on sort order — so the insight is correct regardless of how
            # the analyzer returned the result.
            if query_type != "trend":
                display_result = result.sort_values(ascending=False)
                if ascending:
                    featured_value = result.min()
                    featured_category = result.idxmin()
                else:
                    featured_value = result.max()
                    featured_category = result.idxmax()
            else:
                display_result = result  # trend keeps chronological order
                featured_value = result.iloc[0]
                featured_category = result.index[0]

            pct = (featured_value / total * 100) if total else 0

            # --- Build result table (up to 8 rows) ---
            table_rows = []
            for cat, val in display_result.head(8).items():
                bar_len = int((abs(val) / abs_max) * 20)
                bar = "█" * bar_len
                table_rows.append(f"  {str(cat):<25} {bar:<20} {val:>12,.2f}")
            table = "\n".join(table_rows)

            # --- Direction-aware language ---
            if ascending:
                verb = "has the least"
                heading_pfx = "Bottom"
            else:
                verb = "leads with"
                heading_pfx = "Top"

            # --- Compose answer ---
            if query_type in ("comparison", "top_n"):
                limit = intent.get("limit")
                if limit:
                    heading = f"{heading_pfx} {limit}"
                else:
                    heading = "Comparison"
                answer = (
                    f"📊 {heading} by {dimension_label}\n"
                    f"{'─' * 60}\n"
                    f"{table}\n\n"
                    f"💡 Insight\n"
                    f"  {featured_category} {verb} {op_label.lower()} {metric_label} "
                    f"of ${featured_value:,.2f} ({pct:.1f}% of total ${total:,.2f})."
                )

            elif query_type == "aggregation":
                rank_word = "least" if ascending else "highest"
                answer = (
                    f"📊 {op_label} {metric_label} by {dimension_label}\n"
                    f"{'─' * 60}\n"
                    f"{table}\n\n"
                    f"💡 Insight\n"
                    f"  {featured_category} has the {rank_word} {op_label.lower()} "
                    f"{metric_label} at ${featured_value:,.2f}."
                )

            elif query_type == "trend":
                granularity = intent.get("time_granularity", "day")
                gran_label = {
                    "year": "Year",
                    "month": "Month",
                    "week": "Week",
                    "day": "Date",
                }.get(granularity, "Date")

                if ascending:
                    featured_val = result.min()
                    featured_per = result.idxmin()
                    superlative = "Lowest"
                else:
                    featured_val = result.max()
                    featured_per = result.idxmax()
                    superlative = "Peak"

                last_category = result.index[-1]
                last_value = result.iloc[-1]
                answer = (
                    f"📈 {metric_label} by {gran_label}\n"
                    f"{'─' * 60}\n"
                    f"{table}\n\n"
                    f"💡 Insight\n"
                    f"  {superlative} {gran_label.lower()}: {featured_per} "
                    f"(${featured_val:,.2f}).  "
                    f"Latest: {last_category} (${last_value:,.2f})."
                )

            else:
                answer = f"📊 Results\n{'─' * 60}\n{table}"

            context["answer"] = answer
            return context

        except Exception as e:
            import traceback

            print(f"[InsightGenerator ERROR] {e}")
            traceback.print_exc()
            context["_insight_error"] = str(e)
            # Always set a fallback answer so the user sees something
            if not context.get("answer"):
                raw = context.get("analysis")
                context["answer"] = (
                    raw.to_string()
                    if raw is not None
                    else "⚠️  Could not format results."
                )
            return context
