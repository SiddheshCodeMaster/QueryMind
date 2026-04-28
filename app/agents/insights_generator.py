import pandas as pd


class InsightGenerator:
    """
    Converts a raw analysis Series into a human-readable insight string.

    Works for all four query types: comparison, top_n, aggregation, trend.
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

            # Normalise to Series
            if isinstance(result, pd.DataFrame):
                result = result.squeeze()

            if not isinstance(result, pd.Series) or result.empty:
                return context

            # --- Human-readable labels ---
            metric_label = metric.replace("_", " ").title()
            dimension_label = dimension.replace("_", " ").title()
            op_label = "Average" if operation == "mean" else "Total"

            top_value = result.iloc[0]
            top_category = result.index[0]
            total = result.sum()
            pct = (top_value / total * 100) if total else 0

            # --- Build result table (up to 8 rows) ---
            table_rows = []
            for cat, val in result.head(8).items():
                bar_len = int((val / result.max()) * 20) if result.max() else 0
                bar = "█" * bar_len
                table_rows.append(f"  {str(cat):<25} {bar:<20} {val:>12,.2f}")

            table = "\n".join(table_rows)

            # --- Compose answer ---
            if query_type in ("comparison", "top_n"):
                limit = intent.get("limit")
                heading = f"Top {limit}" if limit else "Comparison"
                answer = (
                    f"📊 {heading} by {dimension_label}\n"
                    f"{'─' * 60}\n"
                    f"{table}\n\n"
                    f"💡 Insight\n"
                    f"  {top_category} leads with {op_label.lower()} {metric_label} "
                    f"of ${top_value:,.2f} ({pct:.1f}% of total ${total:,.2f})."
                )

            elif query_type == "aggregation":
                answer = (
                    f"📊 {op_label} {metric_label} by {dimension_label}\n"
                    f"{'─' * 60}\n"
                    f"{table}\n\n"
                    f"💡 Insight\n"
                    f"  {top_category} has the highest {op_label.lower()} "
                    f"{metric_label} at ${top_value:,.2f}."
                )

            elif query_type == "trend":
                last_category = result.index[-1]
                last_value = result.iloc[-1]
                answer = (
                    f"📈 Trend — {metric_label} over {dimension_label}\n"
                    f"{'─' * 60}\n"
                    f"{table}\n\n"
                    f"💡 Insight\n"
                    f"  Peak at {top_category} (${top_value:,.2f}). "
                    f"  Latest period ({last_category}): ${last_value:,.2f}."
                )

            else:
                answer = f"📊 Results\n{'─' * 60}\n{table}"

            context["answer"] = answer
            return context

        except Exception:
            # Fail gracefully — pipeline will fall back to raw .to_string()
            return context
