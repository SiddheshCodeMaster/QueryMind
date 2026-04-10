from app.agents.planner import PlannerAgent
from app.security.input_guard import InputGuard
from app.security.schema_filter import SchemaFilter
from app.data.connectors.csv_connector import CSVConnector
from app.data.schema_engine import SchemaEngine
from app.tools.analyzer import Analyzer


class QueryMindPipeline:
    def __init__(self, file_path, semantic_map):
        self.connector = CSVConnector(file_path)
        self.input_guard = InputGuard()
        self.semantic_map = semantic_map
        self.schema_filter = SchemaFilter()
        self.schema_engine = SchemaEngine()
        self.planner = PlannerAgent()
        self.analyzer = Analyzer()

        # Load data ONCE
        self.base_context = {}
        self.base_context = self.connector.run(self.base_context)
        self.base_context = self.schema_filter.run(self.base_context)
        self.base_context = self.schema_engine.run(self.base_context)

        # Inject semantic map
        self.base_context["semantic_mapping"] = semantic_map

    def run(self, context):

        # Inject base data every time
        context["dataframe"] = self.base_context.get("dataframe")
        context["schema"] = self.base_context.get("schema")
        context["schema_description"] = self.base_context.get("schema_description")

        # Inject semantic map EXPLICITLY
        context["semantic_map"] = self.semantic_map

        steps = [
            ("input_guard", self.input_guard),
            ("planner", self.planner),
            ("analyzer", self.analyzer),
        ]

        for name, step in steps:
            context = step.run(context)

            if context.get("error"):
                return context

        return context
