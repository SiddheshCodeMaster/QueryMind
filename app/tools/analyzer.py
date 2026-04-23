class Analyzer:
    def run(self, context):
        df = context["dataframe"]
        intent = context["intent"]

        metric = intent.get("metric")
        dimension = intent.get("dimension")
        query_type = intent.get("query_type")

        if not metric or not dimension:
            context["error"] = "Invalid intent"
            return context

        df[dimension] = df[dimension].astype(str).str.strip()

        df[dimension] = df[dimension].replace(
            ["ERROR", "UNKNOWN", "Unknown", ""], "Unknown"
        )

        try:
            if query_type == "comparison":
                result = (
                    df.groupby(dimension)[metric].sum().sort_values(ascending=False)
                )

            elif query_type == "top_n":
                n = intent.get("limit", 5)
                result = (
                    df.groupby(dimension)[metric]
                    .sum()
                    .sort_values(ascending=False)
                    .head(n)
                )

            elif query_type == "aggregation":
                result = df.groupby(dimension)[metric].mean()

            elif query_type == "trend":
                result = df.groupby(dimension)[metric].sum().sort_index()

            else:
                context["error"] = "Unsupported query type"
                return context

            # ALWAYS store RAW result (Series)
            context["analysis"] = result

            return context

        except Exception as e:
            context["error"] = str(e)
            return context
