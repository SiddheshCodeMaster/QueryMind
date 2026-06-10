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
            count_mode = context.get("count_mode", False)
            metric_label = (
                "Count" if count_mode else (metric or "value").replace("_", " ").title()
            )
            dimension_label = dimension.replace("_", " ").title()
            op_label = (
                "Count"
                if count_mode
                else ("Average" if operation == "mean" else "Total")
            )

            # --- Currency detection ---
            # Only use $ formatting if metric name suggests monetary value.
            # Otherwise use plain number formatting.
            CURRENCY_HINTS = {
                "sales",
                "revenue",
                "profit",
                "cost",
                "price",
                "spend",
                "spending",
                "spent",
                "amount",
                "earnings",
                "income",
                "fee",
                "charge",
                "payment",
                "salary",
                "wage",
                "budget",
            }
            is_currency = (
                not count_mode
                and metric
                and any(h in (metric or "").lower() for h in CURRENCY_HINTS)
            )

            def fmt(val):
                """Format a value with or without $ based on metric type."""
                if count_mode:
                    return f"{int(val):,}"
                if is_currency:
                    return f"${val:,.2f}"
                # Check if whole number
                if val == int(val):
                    return f"{int(val):,}"
                return f"{val:,.2f}"

            total = result.sum()
            abs_max = result.abs().max() or 1

            # Display table: sort_ascending controls table order.
            # focus_min controls which item is featured in insight text.
            # These are now independent — "lowest in descending order"
            # shows table high→low but still highlights the minimum.
            focus_min = intent.get("focus_min", ascending)

            if query_type != "trend":
                display_result = result.sort_values(ascending=ascending)
                if focus_min:
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
                table_rows.append(f"  {str(cat):<25} {bar:<20} {fmt(val):>12}")
            table = "\n".join(table_rows)

            # --- Direction-aware language ---
            # verb uses focus_min (what user CARES about)
            # heading_pfx uses ascending (how table is SORTED)
            if focus_min:
                verb = "has the least"
            else:
                verb = "leads with"
            if ascending:
                heading_pfx = "Bottom"
            else:
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
                    f"  {featured_category} {verb} "
                    + (
                        f"{int(featured_value):,} {dimension_label.lower()}s "
                        f"({pct:.1f}% of {int(total):,} total)."
                        if count_mode
                        else f"{op_label.lower()} {metric_label} "
                        f"of {fmt(featured_value)} ({pct:.1f}% of total {fmt(total)})."
                    )
                )

            elif query_type == "aggregation":
                rank_word = "least" if ascending else "highest"
                answer = (
                    f"📊 {op_label} {metric_label} by {dimension_label}\n"
                    f"{'─' * 60}\n"
                    f"{table}\n\n"
                    f"💡 Insight\n"
                    f"  {featured_category} has the {rank_word} "
                    + (
                        f"count: {int(featured_value):,}."
                        if count_mode
                        else f"{op_label.lower()} {metric_label} at {fmt(featured_value)}."
                    )
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
                    f"({fmt(featured_val)}).  "
                    f"Latest: {last_category} ({fmt(last_value)})."
                )

            else:
                if count_mode:
                    heading = f"📊 Count of {dimension_label}s"
                else:
                    heading = "📊 Results"
                answer = f"{heading}\n{'─' * 60}\n{table}"
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
