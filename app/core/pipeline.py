from app.agents.InterpreterAgent import InterpreterAgent
from app.agents.llm_intepreter import LLMInterpreter
from app.tools.analyzer import Analyzer
from app.security.input_guard import InputGuard
from app.data.connectors.csv_connector import CSVConnector
from app.data.connectors.excel_connector import ExcelConnector
from app.security.schema_filter import SchemaFilter
from app.data.schema_engine import SchemaEngine
from app.agents.insights_generator import InsightGenerator
# from app.tools.join_resolver import JoinResolver


class QueryMindPipeline:
    """
    Orchestrates the full query → insight pipeline.

    Accepts either a CSVConnector or ExcelConnector — the rest of the
    pipeline is connector-agnostic.

    Step sequence
    -------------
    1. InputGuard        – blocks junk / sensitive input
    2. InterpreterAgent  – fast rule-based intent extraction
    3. LLMInterpreter    – runs only when confidence < 0.8;
                           falls back to rule intent on failure
    4. Analyzer          – pandas operations; sheet-aware for Excel
    5. InsightGenerator  – formats raw Series → readable answer
    """

    def __init__(self, connector, semantic_map: dict):
        """
        connector    – a CSVConnector or ExcelConnector instance
        semantic_map – {"metric": col, "dimension": col, "time": col|None}
        """
        self.semantic_map = semantic_map

        # Infrastructure
        self.schema_filter = SchemaFilter()
        self.schema_engine = SchemaEngine()

        extra_words = [v for v in semantic_map.values() if v]
        self.input_guard = InputGuard(extra_domain_words=extra_words)

        # Agents
        self.interpreter = InterpreterAgent()
        self.llm_interpreter = LLMInterpreter()
        self.insight_generator = InsightGenerator()
        self.analyzer = Analyzer()
        # self.join_resolver = JoinResolver()

        # Load + cache base context once at startup
        self._base_context = {}
        self._base_context = connector.run(self._base_context)
        if self._base_context.get("error"):
            raise RuntimeError(f"Failed to load data: {self._base_context['error']}")
        self._base_context = self.schema_filter.run(self._base_context)
        self._base_context = self.schema_engine.run(self._base_context)

    # ------------------------------------------------------------------
    def _check_missing_column(self, context: dict) -> dict:
        """
        Detects when the user's query references a column that doesn't exist
        in any loaded sheet, and the interpreter silently fell back to the
        semantic default dimension.

        Sets context["error"] with a helpful message if detected.
        """
        import re

        query = context.get("user_query", "").lower()
        intent = context.get("intent", {})
        schema = context.get("schema", {})
        semantic = context.get("semantic_map", {})

        intent_dimension = intent.get("dimension", "")
        semantic_dimension = semantic.get("dimension", "")

        # Only check when interpreter fell back to semantic default
        # (means it couldn't find an explicit column match in the query)
        if intent_dimension != semantic_dimension:
            return context

        columns = [col["name"] for col in schema.get("columns", [])]
        col_set = set(columns)
        col_words = set()
        for col in columns:
            for part in col.split("_"):
                if len(part) > 2:
                    col_words.add(part)

        STOP_WORDS = {
            "which",
            "what",
            "who",
            "where",
            "when",
            "how",
            "the",
            "was",
            "were",
            "had",
            "has",
            "have",
            "did",
            "does",
            "most",
            "least",
            "max",
            "min",
            "top",
            "highest",
            "lowest",
            "total",
            "average",
            "used",
            "give",
            "show",
            "list",
            "find",
            "get",
            "and",
            "for",
            "with",
            "from",
            "that",
            "this",
            "are",
            "all",
            "per",
            "across",
            "gave",
            "its",
            "their",
            "use",
            "been",
            "much",
            "many",
            "more",
            "less",
            "than",
            "into",
            "over",
            "each",
            "some",
            "any",
            "our",
            "not",
            "but",
            "can",
            "could",
            "would",
            "using",
            "like",
            "sales",
            "revenue",
            "profit",
            "spend",
            "spending",
            "spent",
            "cost",
            "amount",
            "value",
            "number",
            "count",
            "sum",
            "avg",
            "mean",
            "sheet",
            "data",
            "file",
            "table",
            "column",
            "field",
        }

        # Add sheet names to stop words so they don't trigger false positives
        for s in context.get("excel_sheets", []):
            STOP_WORDS.add(s.lower())

        words = re.findall(r"[a-zA-Z]+", query)

        # Unigrams: words unknown to both stop list and schema
        unknowns = [
            w
            for w in words
            if w not in STOP_WORDS
            and w not in col_words
            and w not in col_set
            and len(w) > 3
        ]

        # Bigrams: adjacent unknown-word pairs as potential column names
        bigrams = []
        for i in range(len(words) - 1):
            a, b = words[i], words[i + 1]
            pair = f"{a}_{b}"
            if (
                pair not in col_set
                and a not in STOP_WORDS
                and b not in STOP_WORDS
                and a not in col_words
                and b not in col_words
                and len(a) > 2
                and len(b) > 2
            ):
                bigrams.append(pair)

        candidates = bigrams + unknowns
        if not candidates:
            return context

        # Most likely missing column = longest candidate
        most_likely = sorted(set(candidates), key=len, reverse=True)[0]

        # Suggest the closest real column name using character overlap
        def similarity(a, b):
            a_set = set(a.replace("_", ""))
            b_set = set(b.replace("_", ""))
            return len(a_set & b_set) / max(len(a_set | b_set), 1)

        ml_words = set(most_likely.replace("_", ""))
        suggestions = sorted(
            [c for c in columns if c != "_sheet"],
            key=lambda c: similarity(most_likely, c),
            reverse=True,
        )[:3]

        context["error"] = (
            f"❓ Column '{most_likely.replace('_', ' ')}' doesn't exist in your data.\n\n"
            f"  Available columns: {[c for c in columns if c != '_sheet']}\n\n"
            f"  Closest matches: {suggestions}\n"
            f"  Try rephrasing — e.g. 'which {suggestions[0]} had the most {semantic.get('metric', 'value')}?'"
        )
        return context

    # ------------------------------------------------------------------
    def run(self, context: dict) -> dict:
        # Inject shared state into every query context
        context["dataframe"] = self._base_context.get("dataframe")
        context["schema"] = self._base_context.get("schema")
        context["schema_description"] = self._base_context.get("schema_description")
        context["semantic_map"] = self.semantic_map

        # Carry Excel-specific metadata so Analyzer / InsightGenerator can use it
        context["sheet_dataframes"] = self._base_context.get("sheet_dataframes", {})
        context["excel_sheets"] = self._base_context.get("excel_sheets", [])
        context["excel_mode"] = self._base_context.get("excel_mode", None)

        # STEP 1 – Input guard
        context = self.input_guard.run(context)
        if context.get("error"):
            return context

        # STEP 2 – Rule-based interpreter
        context = self.interpreter.run(context)
        if context.get("error"):
            return context

        confidence = context.get("intent_confidence", 0)

        # STEP 3 – LLM fallback
        if confidence < 0.8:
            llm_context = self.llm_interpreter.run(dict(context))
            if llm_context.get("error"):
                # LLM failed → reject; don't silently fall back to defaults
                context["error"] = (
                    "❓ I couldn't understand that query.\n\n"
                    "Try something like:\n"
                    "  • 'top 5 items by sales'\n"
                    "  • 'highest revenue by location'\n"
                    "  • 'average spend by payment method'\n"
                    "  • 'total sales trend over time'"
                )
                return context
            context["intent"] = llm_context["intent"]
            context["llm_used"] = True

        # STEP 3.5a – Guard: user asked about a column that doesn't exist
        context = self._check_missing_column(context)
        if context.get("error"):
            return context

        # STEP 3.5b – Guard: trend query but no time column configured
        if context.get("intent", {}).get("no_time_column"):
            context["error"] = (
                "⏱️  This query needs a time column, but none was configured.\n\n"
                "Re-run QueryMind and set a time column at the setup prompt, "
                "or rephrase your question to use a different dimension."
            )
            return context

        # STEP 3.7 – Cross-sheet join resolution
        # Runs only when dimension column lives in a different sheet
        # than the metric column (e.g. "which manager had max sales?")
        context = self.join_resolver.run(context)
        if context.get("error"):
            return context

        # STEP 4 – Analyze
        context = self.analyzer.run(context)
        if context.get("error"):
            return context

        # STEP 5 – Generate insight
        context = self.insight_generator.run(context)

        if not context.get("answer"):
            raw = context.get("analysis")
            context["answer"] = (
                raw.to_string()
                if raw is not None
                else "⚠️  Could not generate an answer for that query."
            )

        return context
