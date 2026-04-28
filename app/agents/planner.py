"""
PlannerAgent — lightweight pre-flight check.

NOTE: This agent is currently unused by the pipeline (InterpreterAgent
handles intent extraction). Keep it here for future multi-step query
planning (e.g. chaining two analyses together, or deciding whether a
query needs a trend + comparison combined answer).
"""


class PlannerAgent:
    """
    Validates that the semantic_map is properly configured and that the
    query contains at least one actionable keyword before the pipeline runs.

    Returns an error only for genuinely unactionable input (empty, numeric-only).
    For low-confidence / keyword-free natural-language queries the pipeline
    should route to the LLMInterpreter instead of hard-failing here.
    """

    VALID_KEYWORDS = {
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
        "how much",
        "how many",
        "which",
        "where",
        "what",
    }

    def run(self, context: dict) -> dict:
        query = context.get("user_query", "").lower().strip()
        semantic_map = context.get("semantic_map")

        # --- Validate semantic map ---
        if not semantic_map:
            context["error"] = (
                "Semantic map missing. Please restart and configure your dataset."
            )
            return context

        metric = semantic_map.get("metric")
        dimension = semantic_map.get("dimension")

        if not metric or not dimension:
            context["error"] = (
                "Metric or dimension not configured. "
                "Please restart and select valid columns."
            )
            return context

        # --- Guard obviously bad input ---
        if not query or query.isdigit():
            context["error"] = "Please enter a meaningful question."
            return context

        # --- Route decision (informational, does NOT block) ---
        has_keyword = any(kw in query for kw in self.VALID_KEYWORDS)
        context["planner_has_keyword"] = has_keyword

        return context
