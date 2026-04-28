from app.agents.InterpreterAgent import InterpreterAgent
from app.agents.llm_intepreter import LLMInterpreter
from app.tools.analyzer import Analyzer
from app.security.input_guard import InputGuard
from app.data.connectors.csv_connector import CSVConnector
from app.security.schema_filter import SchemaFilter
from app.data.schema_engine import SchemaEngine
from app.agents.insights_generator import InsightGenerator


class QueryMindPipeline:
    """
    Orchestrates the full query → insight pipeline.

    Step sequence
    -------------
    1. InputGuard        – blocks junk/unsafe input
    2. InterpreterAgent  – fast rule-based intent extraction (confidence 0–1)
    3. LLMInterpreter    – runs only when confidence < 0.8; its result
                           replaces the rule intent, but falls back to the
                           rule intent if the LLM produces invalid output
    4. Analyzer          – pandas operations against the dataframe
    5. InsightGenerator  – formats raw Series into human-readable answer
    """

    def __init__(self, file_path: str, semantic_map: dict):
        self.semantic_map = semantic_map

        # Infrastructure
        self.connector = CSVConnector(file_path)
        self.schema_filter = SchemaFilter()
        self.schema_engine = SchemaEngine()
        self.input_guard = InputGuard()

        # Agents
        self.interpreter = InterpreterAgent()
        self.llm_interpreter = LLMInterpreter()
        self.insight_generator = InsightGenerator()
        self.analyzer = Analyzer()

        # Load and cache base context (df + schema) once at startup
        self._base_context = {}
        self._base_context = self.connector.run(self._base_context)
        self._base_context = self.schema_filter.run(self._base_context)
        self._base_context = self.schema_engine.run(self._base_context)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, context: dict) -> dict:
        # --- Inject shared state ---
        context["dataframe"] = self._base_context.get("dataframe")
        context["schema"] = self._base_context.get("schema")
        context["schema_description"] = self._base_context.get("schema_description")
        context["semantic_map"] = self.semantic_map

        # STEP 1 – Input guard
        context = self.input_guard.run(context)
        if context.get("error"):
            return context

        # STEP 2 – Rule-based interpreter
        context = self.interpreter.run(context)
        if context.get("error"):
            return context

        rule_intent = context.get("intent")  # save for fallback
        confidence = context.get("intent_confidence", 0)

        # STEP 3 – LLM fallback (only when rule confidence is low)
        if confidence < 0.8:
            llm_context = self.llm_interpreter.run(dict(context))  # shallow copy

            if llm_context.get("error"):
                # LLM failed → keep the rule-based intent and carry on
                context["llm_used"] = False
                context["llm_error"] = llm_context["error"]
            else:
                # LLM succeeded → use its intent
                context["intent"] = llm_context["intent"]
                context["llm_used"] = True

        # STEP 4 – Analyze
        context = self.analyzer.run(context)
        if context.get("error"):
            return context

        # STEP 5 – Generate insight
        context = self.insight_generator.run(context)

        # Final safety net: if insight generator produced nothing, use raw
        if not context.get("answer"):
            raw = context.get("analysis")
            context["answer"] = (
                raw.to_string()
                if raw is not None
                else "⚠️  Could not generate an answer for that query."
            )

        return context
