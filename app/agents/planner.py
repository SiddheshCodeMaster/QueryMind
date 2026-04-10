class PlannerAgent:
    def run(self, context):
        query = context["user_query"].lower()
        semantic_map = context.get("semantic_map")

        if not semantic_map:
            context["error"] = "Semantic map missing"
            return context

        metric = semantic_map.get("metric")
        dimension = semantic_map.get("dimension")

        if not metric or not dimension:
            context["error"] = "Invalid semantic mapping"
            return context

        intent = {
            "metric": metric,
            "dimension": dimension,
            "query_type": None,
            "operation": "sum",
            "limit": None,
        }

        # Detect query type
        if "top" in query:
            intent["query_type"] = "top_n"
            intent["limit"] = 5

        elif "average" in query or "avg" in query:
            intent["query_type"] = "aggregation"
            intent["operation"] = "mean"

        elif "trend" in query:
            intent["query_type"] = "trend"
            intent["dimension"] = semantic_map.get("time")

        elif "highest" in query or "lowest" in query:
            intent["query_type"] = "comparison"

        else:
            intent["query_type"] = "aggregation"

        context["intent"] = intent
        return context
