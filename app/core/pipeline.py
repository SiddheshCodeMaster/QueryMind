from app.agents.InterpreterAgent import InterpreterAgent
from app.agents.llm_intepreter import LLMInterpreter
from app.tools.analyzer import Analyzer
from app.security.input_guard import InputGuard
from app.data.connectors.csv_connector import CSVConnector
from app.data.connectors.excel_connector import ExcelConnector
from app.security.schema_filter import SchemaFilter
from app.data.schema_engine import SchemaEngine
from app.agents.insights_generator import InsightGenerator


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

        # Load + cache base context once at startup
        self._base_context = {}
        self._base_context = connector.run(self._base_context)
        if self._base_context.get("error"):
            raise RuntimeError(f"Failed to load data: {self._base_context['error']}")
        self._base_context = self.schema_filter.run(self._base_context)
        self._base_context = self.schema_engine.run(self._base_context)

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

        # STEP 3.5 – Guard: trend query but no time column configured
        if context.get("intent", {}).get("no_time_column"):
            context["error"] = (
                "⏱️  This query needs a time column, but none was configured.\n\n"
                "Re-run QueryMind and set a time column at the setup prompt, "
                "or rephrase your question to use a different dimension."
            )
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
