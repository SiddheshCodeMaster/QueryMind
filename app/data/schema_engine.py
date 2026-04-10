class SchemaEngine:
    def run(self, context):
        schema = context["schema"]
        print("Schema: ", schema)
        
        if not schema:
            print("\n -------------- CONTEXT------------ \n", context)

            return context

        description = "Table: data\n\nColumns:\n"

        for col in schema["columns"]:
            description += f"- {col['name']} ({col['type']})\n"

        context["schema_description"] = description

        return context
