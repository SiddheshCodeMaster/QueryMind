import re

BLOCKED_KEYWORDS = ["password", "ssn", "credit card", "api key", "private key"]

ANALYTICAL_KEYWORDS = {
    # intent words
    "highest",
    "lowest",
    "top",
    "bottom",
    "most",
    "least",
    "best",
    "worst",
    "average",
    "avg",
    "mean",
    "total",
    "sum",
    "count",
    "max",
    "min",
    "trend",
    "over time",
    "monthly",
    "daily",
    "weekly",
    "yearly",
    "compare",
    "comparison",
    "distribution",
    "breakdown",
    "ascending",
    "descending",
    "asc",
    "desc",
    "increasing",
    "decreasing",
    "lowest to highest",
    "highest to lowest",
    "sorted",
    "order",
    # question words
    "show",
    "give",
    "find",
    "list",
    "get",
    "what",
    "which",
    "how many",
    "how much",
    "where",
    "who",
    # common data domain words
    "sales",
    "revenue",
    "profit",
    "spend",
    "spending",
    "spent",
    "cost",
    "item",
    "items",
    "product",
    "products",
    "category",
    "location",
    "payment",
    "method",
    "customer",
    "customers",
    "order",
    "orders",
    "region",
    "city",
    "country",
    "store",
    "date",
    "month",
    "year",
    "by",
    "per",
    "across",
    "between",
    "vs",
    "versus",
}


# Slash commands handled entirely by the TUI — never reach InputGuard
TUI_COMMANDS = {"/history", "/h", "/profile", "/p", "history", "profile"}


class InputGuard:
    def __init__(self, extra_domain_words=None):
        """
        extra_domain_words: pass your semantic_map column names here so that
        queries referencing column names directly are always accepted.
        Example: InputGuard(extra_domain_words=["corrected_t_spent", "payment_method"])
        """
        self._extra = set(extra_domain_words or [])

    def run(self, context):
        query = context.get("user_query", "").strip()

        # --- Empty ---
        if not query:
            context["error"] = "Please enter a question."
            return context

        # --- TUI slash commands (should never reach here, but safety net) ---
        if query.strip().lower() in TUI_COMMANDS:
            return context

        query_lower = query.lower()

        # --- Sensitive content ---
        for word in BLOCKED_KEYWORDS:
            if word in query_lower:
                context["error"] = (
                    "⛔ Sensitive query detected. Please ask about your data."
                )
                return context

        # --- Gibberish / no intent ---
        domain_words = ANALYTICAL_KEYWORDS | self._extra
        has_intent = any(kw in query_lower for kw in domain_words)

        if not has_intent:
            context["error"] = (
                "❓ I couldn't understand that as a data question.\n\n"
                "Try something like:\n"
                "  • 'top 5 items by sales'\n"
                "  • 'highest revenue by location'\n"
                "  • 'average spend by payment method'\n"
                "  • 'total sales trend over time'"
            )
            return context

        return context
