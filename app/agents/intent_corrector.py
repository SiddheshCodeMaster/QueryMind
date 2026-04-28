class IntentCorrector:
    """
    Post-processes the intent after the interpreter runs.

    Responsibilities
    ----------------
    1. If the resolved metric is not a numeric column → replace with the
       first detected numeric column.
    2. If the resolved dimension is an ID column (high-cardinality, unique)
       → replace with the first proper categorical column.
    3. Ensures the intent has a valid query_type (defaults to "aggregation").

    This runs AFTER the interpreter (rule or LLM) and BEFORE the Analyzer,
    acting as a safety layer so the Analyzer never receives bad column names.

    Depends on context["semantic_columns"] being populated by SchemaEngine.
    """

    def run(self, context: dict) -> dict:
        intent = context.get("intent")
        semantic = context.get("semantic_columns")  # set by SchemaEngine

        if not intent:
            return context  # nothing to correct

        if not semantic:
            # SchemaEngine didn't run or produced nothing; can't correct
            return context

        metrics = semantic.get("metrics", [])
        dimensions = semantic.get("dimensions", [])
        ids = semantic.get("ids", [])

        # --- Fix metric ---
        if intent.get("metric") not in metrics and metrics:
            intent["metric"] = metrics[0]

        # --- Fix dimension ---
        current_dim = intent.get("dimension")
        if current_dim in ids and dimensions:
            intent["dimension"] = dimensions[0]
        elif current_dim not in dimensions and dimensions:
            # Only override if the current value isn't in any known column list
            all_known = metrics + dimensions + ids
            if current_dim not in all_known and dimensions:
                intent["dimension"] = dimensions[0]

        # --- Ensure query_type is set ---
        if not intent.get("query_type"):
            intent["query_type"] = "aggregation"

        # --- Ensure operation is set ---
        if not intent.get("operation"):
            intent["operation"] = "sum"

        context["intent"] = intent
        context["intent_corrected"] = True

        return context
