import re


class InterpreterAgent:
    """
    Rule-based intent interpreter.

    Builds a structured intent dict from the user query using keyword matching
    and the semantic_map supplied at setup time.

    Confidence rules
    ----------------
    - 0.9  → matched a strong analytical keyword; skip LLM
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

    # Order matters: first match wins.
    QUERY_TYPE_MAP = [
        ("top", "top_n", "sum"),
        ("bottom", "top_n", "sum"),
        ("highest", "comparison", "sum"),
        ("lowest", "comparison", "sum"),
        ("most", "comparison", "sum"),
        ("least", "comparison", "sum"),
        ("average", "aggregation", "mean"),
        ("avg", "aggregation", "mean"),
        ("mean", "aggregation", "mean"),
        ("trend", "trend", "sum"),
        ("over time", "trend", "sum"),
        ("monthly", "trend", "sum"),
        ("daily", "trend", "sum"),
        ("total", "aggregation", "sum"),
        ("sum", "aggregation", "sum"),
        ("distribution", "aggregation", "sum"),
        ("breakdown", "aggregation", "sum"),
        ("compare", "comparison", "sum"),
    ]

    # Natural-language synonyms that mean "use the configured metric".
    # When a user says "top 5 items by SALES", "sales" isn't a column —
    # it's a synonym for whatever metric they configured.
    METRIC_SYNONYMS = {
        "sales",
        "revenue",
        "profit",
        "spend",
        "spending",
        "spent",
        "cost",
        "costs",
        "amount",
        "amounts",
        "value",
        "values",
        "earning",
        "earnings",
        "income",
        "price",
        "prices",
    }

    # Natural-language synonyms that map to known dimension keywords.
    DIMENSION_KEYWORDS = {
        "location": "location",
        "city": "location",
        "region": "location",
        "payment": "payment_method",
        "payment method": "payment_method",
        "item": "item",
        "items": "item",
        "product": "item",
        "products": "item",
        "category": "item",
    }

    def run(self, context):
        query = context["user_query"].lower().strip()
        schema = context["schema"]["columns"]
        semantic_map = context["semantic_map"]

        columns = [col["name"] for col in schema]

        # Validate semantic_map columns exist in the dataframe
        default_metric = semantic_map.get("metric")
        default_dimension = semantic_map.get("dimension")

        if default_metric not in columns:
            default_metric = None
        if default_dimension not in columns:
            default_dimension = None

        # Guard: empty / numeric-only
        if not query or query.isdigit():
            context["error"] = "Please enter a meaningful question."
            return context

        # ── Base intent ──────────────────────────────────────────────────
        intent = {
            "metric": default_metric,
            "dimension": default_dimension,
            "query_type": "aggregation",
            "operation": "sum",
            "limit": None,
        }

        # ── Metric resolution ────────────────────────────────────────────
        # 1. If an exact column name appears in the query → use it as metric
        metric_found = False
        for col in columns:
            readable = col.replace("_", " ")
            if col in query or readable in query:
                # Heuristic: if this column is numeric-ish name, treat as metric
                numeric_hints = {
                    "amount",
                    "price",
                    "spent",
                    "revenue",
                    "sales",
                    "cost",
                    "total",
                    "sum",
                    "qty",
                    "quantity",
                    "profit",
                }
                if any(h in col for h in numeric_hints):
                    intent["metric"] = col
                    metric_found = True
                    break

        # 2. If a metric synonym appears, keep the configured default metric
        #    (don't override — the synonym just confirms "use the metric column")
        if not metric_found:
            for syn in self.METRIC_SYNONYMS:
                if syn in query:
                    intent["metric"] = default_metric  # keep semantic default
                    break

        # ── Dimension resolution ─────────────────────────────────────────
        # 1. Keyword → dimension map (explicit, fast)
        dim_set = False
        for keyword, col_name in self.DIMENSION_KEYWORDS.items():
            if keyword in query and col_name in columns:
                intent["dimension"] = col_name
                dim_set = True
                break

        # 2. Exact column name match (catches user's own column names)
        if not dim_set:
            for col in columns:
                readable = col.replace("_", " ")
                if col in query or readable in query:
                    if col != intent.get("metric"):  # don't use metric as dimension
                        intent["dimension"] = col
                        break

        # 3. Time-column override for trend queries (handled below after query type)

        # ── Query-type detection ─────────────────────────────────────────
        matched_type = None
        matched_op = None

        for keyword, q_type, op in self.QUERY_TYPE_MAP:
            if keyword in query:
                matched_type = q_type
                matched_op = op
                break

        if matched_type:
            intent["query_type"] = matched_type
            intent["operation"] = matched_op

        # ── top-N: extract explicit number ───────────────────────────────
        if intent["query_type"] == "top_n":
            m = re.search(r"(?:top|bottom)\s+(\d+)", query)
            intent["limit"] = int(m.group(1)) if m else 5
            if "bottom" in query:
                intent["ascending"] = True

        # ── trend: force time column as dimension ────────────────────────
        if intent["query_type"] == "trend":
            time_col = semantic_map.get("time")
            if time_col and time_col in columns:
                intent["dimension"] = time_col

        # ── Sheet scope ──────────────────────────────────────────────────
        # Detect "in sheet Orders", "from Returns sheet", "across all sheets"
        available_sheets = context.get("excel_sheets", [])
        if available_sheets:
            intent["sheet"] = _detect_sheet_scope(query, available_sheets)

        # ── Confidence ───────────────────────────────────────────────────
        has_strong = any(kw in query for kw in self.STRONG_KEYWORDS)
        context["intent_confidence"] = 0.9 if has_strong else 0.2

        context["intent"] = intent
        return context


# ── Sheet-scope detection (appended at module level, called inside run) ──────
# This is a standalone helper imported by InterpreterAgent.run()
# It detects patterns like:
#   "top 5 sales in sheet Orders"
#   "average profit from the Returns sheet"
#   "across all sheets"

import re as _re


def _detect_sheet_scope(query: str, available_sheets: list) -> str | None:
    """
    Returns a sheet name if the query targets a specific sheet,
    or None if it targets all loaded sheets.
    """
    q = query.lower()

    # "across all sheets" / "all sheets" / "every sheet" → None (use combined df)
    if any(p in q for p in ["all sheets", "across sheets", "every sheet", "all data"]):
        return None

    # "in sheet <name>" / "from sheet <name>" / "sheet <name>"
    for sheet in available_sheets:
        if sheet.lower() in q:
            return sheet

    return None
