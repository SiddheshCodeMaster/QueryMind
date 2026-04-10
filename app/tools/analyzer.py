class Analyzer:
    def run(self, context):
        df = context["dataframe"]
        intent = context["intent"]

        metric = intent["metric"]
        dimension = intent["dimension"]
        query_type = intent["query_type"]

        if not metric or not dimension:
            context["error"] = "Invalid intent"
            return context

        df[dimension] = df[dimension].fillna("Unknown")

        if query_type == "comparison":
            result = df.groupby(dimension)[metric].sum().sort_values(ascending=False)
            top = result.iloc[0]
            label = result.index[0]

            context["answer"] = (
                f"{label} has the highest {metric} with value {top:,.2f}"
            )

        elif query_type == "top_n":
            n = intent.get("limit", 5)
            result = (
                df.groupby(dimension)[metric].sum().sort_values(ascending=False).head(n)
            )

            context["answer"] = result.to_string()

        elif query_type == "aggregation":
            result = df.groupby(dimension)[metric].mean()

            context["answer"] = result.to_string()

        elif query_type == "trend":
            result = df.groupby(dimension)[metric].sum().sort_index()

            context["answer"] = result.to_string()

        return context
