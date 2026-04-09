from app.security.input_guard import InputGuard
from app.security.schema_filter import SchemaFilter
from app.data.connectors.csv_connector import CSVConnector
from app.data.schema_engine import SchemaEngine

# (we’ll add other modules later)


class QueryMindPipeline:
    def __init__(self, file_path):
        self.connector = CSVConnector(file_path)
        self.input_guard = InputGuard()
        self.schema_filter = SchemaFilter()
        self.schema_engine = SchemaEngine()

    def run(self, context):
        steps = [
            ("input_guard", self.input_guard),
            ("connector", self.connector),
            ("schema_filter", self.schema_filter),
            ("schema_engine", self.schema_engine),
        ]

        for name, step in steps:
            context = step.run(context)

            if context.get("error"):
                return context

        return context
