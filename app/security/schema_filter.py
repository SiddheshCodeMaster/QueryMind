SENSITIVE_COLUMNS = ["password", "ssn", "credit_card"]


class SchemaFilter:
    def run(self, context):
        schema = context["schema"]

        if not schema:
            return context

        filtered_columns = [
            col
            for col in schema["columns"]
            if col["name"].lower() not in SENSITIVE_COLUMNS
        ]

        schema["columns"] = filtered_columns
        context["schema"] = schema

        return context
