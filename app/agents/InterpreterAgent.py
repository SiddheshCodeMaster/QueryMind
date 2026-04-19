class InterpreterAgent:
    def run(self, context):
        query = context["user_query"].lower()
        schema = context["schema"]["columns"]
        semantic_map = context["semantic_map"]

        columns = [col["name"] for col in schema]

        intent = {
            "metric": semantic_map.get("metric"),
            "dimension": semantic_map.get("dimension"),
            "query_type": "aggregation",
            "operation": "sum",
            "limit": None,
        }

        # DYNAMIC DIMENSION DETECTION
        for col in columns:
            if col.replace("_", " ") in query:
                intent["dimension"] = col

        # KEYWORD MAPPING
        if "location" in query:
            intent["dimension"] = "location"

        elif "payment" in query:
            intent["dimension"] = "payment_method"

        elif "item" in query or "product" in query:
            intent["dimension"] = "item"

        # QUERY TYPE
        if "top" in query:
            intent["query_type"] = "top_n"
            intent["limit"] = 5

        elif "average" in query:
            intent["operation"] = "mean"

        elif "highest" in query or "most" in query:
            intent["query_type"] = "comparison"

        context["intent"] = intent
        return context
