class InterpreterAgent:
    """
    Rule-based intent interpreter.

    Builds a structured intent dict from the user query using keyword matching
    and the semantic_map supplied at setup time.

    Confidence rules
    ----------------
    - 0.9  → matched a strong keyword; skip LLM
    - 0.5  → matched only a weak/generic keyword; LLM may refine
    - 0.2  → no recognisable keyword; defer to LLM
    """

    STRONG_KEYWORDS = {
        "highest",
        "lowest",
        "top",
        "bottom",
        "average",
        "avg",
        "mean",
        "trend",
        "over time",
        "monthly",
        "daily",
        "total",
        "sum",
        "most",
        "least",
        "distribution",
        "breakdown",
        "compare",
    }

    QUERY_TYPE_MAP = {
        "top": ("top_n", "sum"),
        "bottom": ("top_n", "sum"),
        "highest": ("comparison", "sum"),
        "lowest": ("comparison", "sum"),
        "most": ("comparison", "sum"),
        "least": ("comparison", "sum"),
        "average": ("aggregation", "mean"),
        "avg": ("aggregation", "mean"),
        "mean": ("aggregation", "mean"),
        "trend": ("trend", "sum"),
        "over time": ("trend", "sum"),
        "monthly": ("trend", "sum"),
        "daily": ("trend", "sum"),
        "total": ("aggregation", "sum"),
        "sum": ("aggregation", "sum"),
        "distribution": ("aggregation", "sum"),
        "breakdown": ("aggregation", "sum"),
        "compare": ("comparison", "sum"),
    }

    def run(self, context):
        query = context["user_query"].lower().strip()
        schema = context["schema"]["columns"]
        semantic_map = context["semantic_map"]

        columns = [col["name"] for col in schema]

        # Validate that semantic_map columns actually exist in the dataframe
        default_metric = semantic_map.get("metric")
        default_dimension = semantic_map.get("dimension")

        if default_metric not in columns:
            default_metric = None
        if default_dimension not in columns:
            default_dimension = None

        # --- Guard: empty / numeric-only query ---
        if not query or query.isdigit():
            context["error"] = "Please enter a meaningful question."
            return context

        # --- Build base intent from semantic defaults ---
        intent = {
            "metric": default_metric,
            "dimension": default_dimension,
            "query_type": "aggregation",
            "operation": "sum",
            "limit": None,
        }

        # --- Dynamic dimension detection (column name mentioned in query) ---
        for col in columns:
            readable = col.replace("_", " ")
            if readable in query or col in query:
                # Only override dimension if the column looks categorical
                intent["dimension"] = col
                break

        # --- Hardcoded keyword → dimension overrides (project-specific) ---
        # Keep these; they're faster and more reliable than fuzzy matching.
        if "location" in query:
            intent["dimension"] = "location"
        elif "payment" in query:
            intent["dimension"] = "payment_method"
        elif "item" in query or "product" in query:
            intent["dimension"] = "item"
        elif "month" in query:
            intent["dimension"] = semantic_map.get("time") or intent["dimension"]

        # --- Query-type detection (first match wins, ordered by priority) ---
        matched_query_type = None
        matched_operation = None

        for keyword, (q_type, op) in self.QUERY_TYPE_MAP.items():
            if keyword in query:
                matched_query_type = q_type
                matched_operation = op
                break

        if matched_query_type:
            intent["query_type"] = matched_query_type
            intent["operation"] = matched_operation

        # --- top-N: try to extract explicit number ("top 10 …") ---
        if intent["query_type"] == "top_n":
            import re

            m = re.search(r"top\s+(\d+)", query)
            intent["limit"] = int(m.group(1)) if m else 5

            # "bottom N" means ascending sort — handled in Analyzer
            if "bottom" in query:
                intent["ascending"] = True

        # --- trend: force dimension to time column if available ---
        if intent["query_type"] == "trend":
            time_col = semantic_map.get("time")
            if time_col and time_col in columns:
                intent["dimension"] = time_col

        # --- Confidence ---
        has_strong = any(kw in query for kw in self.STRONG_KEYWORDS)
        context["intent_confidence"] = 0.9 if has_strong else 0.2

        context["intent"] = intent
        return context
