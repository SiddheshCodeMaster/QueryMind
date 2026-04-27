import pandas as pd


class InsightGenerator:
    def run(self, context):
        result = context.get("analysis")
        intent = context.get("intent")

        if result is None or intent is None:
            return context

        try:
            metric = intent.get("metric")
            dimension = intent.get("dimension")
            query_type = intent.get("query_type")

            # Ensure Series
            if isinstance(result, pd.DataFrame):
                result = result.squeeze()

            if not isinstance(result, pd.Series) or result.empty:
                return context

            # CASE 1: TOP N
            if query_type == "top_n":
                n = intent.get("limit", 5)

                top_n = result.head(n)
                total = result.sum()

                top_value = top_n.iloc[0]
                top_category = top_n.index[0]
                percentage = (top_value / total) * 100 if total else 0

                # Format table
                table = top_n.to_string()

                context["answer"] = (
                    f"📊 Top {n} {dimension.replace('_', ' ')} by {metric.replace('_', ' ')}:\n\n"
                    f"{table}\n\n"
                    f"💡 Insight:\n"
                    f"{top_category} leads with ${top_value:,.2f} "
                    f"({percentage:.1f}% of total).\n\n"
                    f"📌 Takeaway:\n"
                    f"{top_category} is the highest contributor among top {n}."
                )

                return context

            # CASE 2: COMPARISON (top 1)
            elif query_type == "comparison":
                total = result.sum()
                top_value = result.iloc[0]
                top_category = result.index[0]
                percentage = (top_value / total) * 100 if total else 0

                context["answer"] = (
                    f"💡 Insight:\n"
                    f"{top_category} is the top-performing {dimension.replace('_', ' ')} "
                    f"with total {metric.replace('_', ' ')} of ${top_value:,.2f}.\n\n"
                    f"📊 Context:\n"
                    f"- Contribution: {percentage:.1f}% of total\n"
                    f"- Total: ${total:,.2f}\n\n"
                    f"📌 Takeaway:\n"
                    f"{top_category} dominates the {dimension.replace('_', ' ')} category."
                )

                return context

            # CASE 3: DEFAULT (aggregation/trend)
            else:
                context["answer"] = result.to_string()
                return context

        except Exception:
            return context
