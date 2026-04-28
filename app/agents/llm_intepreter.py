import json

from app.llm.ollama_client import OllamaClient


class LLMInterpreter:
    """
    Falls back to an LLM when the rule-based interpreter has low confidence.

    Converts a natural-language query into the same structured intent dict
    that InterpreterAgent produces, so the rest of the pipeline is unaware
    of which interpreter was used.
    """

    def __init__(self):
        self.client = OllamaClient()

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def build_prompt(self, query: str, columns: list, semantic_map: dict) -> str:
        metric = semantic_map.get("metric", "")
        dimension = semantic_map.get("dimension", "")
        time_col = semantic_map.get("time", "")

        numeric_cols = [
            c
            for c in columns
            if any(
                hint in c
                for hint in (
                    "amount",
                    "price",
                    "spent",
                    "revenue",
                    "sales",
                    "total",
                    "count",
                    "qty",
                    "quantity",
                )
            )
        ]
        categorical_cols = [c for c in columns if c not in numeric_cols]

        return f"""You are a data analyst assistant.

Convert the user query into a JSON intent object. Use ONLY column names from the list below.

Dataset columns  : {columns}
Numeric columns  : {numeric_cols or "unknown — pick best match"}
Categorical cols : {categorical_cols or "unknown — pick best match"}
Default metric   : {metric}
Default dimension: {dimension}
Time column      : {time_col or "none"}

User query: "{query}"

Return ONLY valid JSON — no explanation, no markdown fences.

{{
  "metric":     "<column_name>",
  "dimension":  "<column_name>",
  "operation":  "sum | mean | count",
  "query_type": "comparison | aggregation | trend | top_n",
  "limit":      <number or null>
}}

Rules
- metric    must be a numeric column
- dimension must be a categorical or time column
- "highest" / "most" / "compare"    → query_type = "comparison"
- "top N" / "bottom N"              → query_type = "top_n", limit = N (default 5)
- "average" / "avg" / "mean"        → query_type = "aggregation", operation = "mean"
- "trend" / "over time" / "monthly" → query_type = "trend", dimension = time column
- anything else                     → query_type = "aggregation", operation = "sum"
"""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse(self, text: str) -> dict | None:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            return json.loads(text[start:end])
        except Exception:
            return None

    def _valid(self, intent: dict, columns: list) -> bool:
        if not intent:
            return False
        if intent.get("metric") not in columns:
            return False
        if intent.get("dimension") not in columns:
            return False
        if intent.get("query_type") not in (
            "comparison",
            "aggregation",
            "trend",
            "top_n",
        ):
            return False
        return True

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    def run(self, context: dict) -> dict:
        query = context["user_query"]
        schema = context["schema"]["columns"]
        semantic_map = context.get("semantic_map", {})
        columns = [col["name"] for col in schema]

        prompt = self.build_prompt(query, columns, semantic_map)
        response = self.client.generate(prompt)
        intent = self._parse(response)

        if not self._valid(intent, columns):
            context["error"] = (
                f"LLM returned an invalid intent. Raw response: {response[:200]}"
            )
            return context

        context["intent"] = intent
        context["llm_used"] = True
        return context
