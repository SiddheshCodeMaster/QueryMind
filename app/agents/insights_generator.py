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

            # Ensure it's a Series
            if isinstance(result, pd.DataFrame):
                result = result.squeeze()

            if not isinstance(result, pd.Series) or result.empty:
                return context

            total = result.sum()
            top_value = result.iloc[0]
            top_category = result.index[0]

            percentage = (top_value / total) * 100 if total else 0

            context["answer"] = (
                f"💡 Insight:\n"
                f"{top_category} is the top-performing {dimension.replace('_', ' ')} "
                f"with total {metric.replace('_', ' ')} of ₹{top_value:,.2f}.\n\n"
                f"📊 Context:\n"
                f"- Contribution: {percentage:.1f}% of total\n"
                f"- Total: ₹{total:,.2f}\n\n"
                f"📌 Takeaway:\n"
                f"{top_category} dominates the {dimension.replace('_', ' ')} category."
            )

            return context

        except Exception:
            return context
