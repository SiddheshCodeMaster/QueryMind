from app.agents.InterpreterAgent import InterpreterAgent
from app.agents.llm_intepreter import LLMInterpreter

from app.tools.analyzer import Analyzer
from app.security.input_guard import InputGuard

from app.data.connectors.csv_connector import CSVConnector
from app.security.schema_filter import SchemaFilter
from app.data.schema_engine import SchemaEngine
from app.agents.insights_generator import InsightGenerator


class QueryMindPipeline:
    def __init__(self, file_path, semantic_map):
        self.semantic_map = semantic_map

        # Core components:
        self.connector = CSVConnector(file_path)
        self.schema_filter = SchemaFilter()
        self.schema_engine = SchemaEngine()

        self.input_guard = InputGuard()

        # Agents:
        self.interpreter = InterpreterAgent()
        self.llm_interpreter = LLMInterpreter()
        self.insight_generator = InsightGenerator()

        self.analyzer = Analyzer()

        # Load base context once
        self.base_context = {}
        self.base_context = self.connector.run(self.base_context)
        self.base_context = self.schema_filter.run(self.base_context)
        self.base_context = self.schema_engine.run(self.base_context)

    def run(self, context):

        # Inject base context:
        context["dataframe"] = self.base_context.get("dataframe")
        context["schema"] = self.base_context.get("schema")
        context["schema_description"] = self.base_context.get("schema_description")

        context["semantic_map"] = self.semantic_map

        # ----------------------------
        # STEP 1: Input Guard:
        # ----------------------------
        context = self.input_guard.run(context)
        if context.get("error"):
            return context

        # ----------------------------
        # STEP 2: Rule-Based Interpreter:
        # ----------------------------
        context = self.interpreter.run(context)

        confidence = context.get("intent_confidence", 0)

        # ----------------------------
        # STEP 3: LLM Fallback:
        # ----------------------------
        if confidence < 0.8:
            context = self.llm_interpreter.run(context)

            # If LLM fails → fallback to rule-based safely:
            if context.get("error"):
                # Remove error, continue with rule-based intent:
                context.pop("error", None)

        # ----------------------------
        # STEP 4: Analyzer:
        # ----------------------------
        context = self.analyzer.run(context)

        if context.get("error"):
            return context

        context = self.insight_generator.run(context)

        if not context.get("answer"):  # SAFETY
            context["answer"] = "Could not generate insights"

        return context
