class SQLWriter:
    def run(self, context):
        intent = context.get("intent")
        schema = context.get("schema")

        if not intent or not schema:
            context["error"] = "Missing intent or schema"
            return context

        columns = [col["name"] for col in schema["columns"]]

        metric = intent.get("metric")
        dimension = intent.get("dimension")
        analysis_type = intent.get("analysis_type")

        # Safety check: ensure columns exist
        if metric not in columns or dimension not in columns:
            context["error"] = "Invalid columns in intent"
            return context

        try:
            # Build SQL
            sql = f"SELECT {dimension}, SUM({metric}) AS total_{metric} FROM data"

            # GROUP BY
            sql += f" GROUP BY {dimension}"

            # ORDER BY (for comparison queries)
            if analysis_type == "comparison":
                sql += f" ORDER BY total_{metric} DESC"

            context["sql_query"] = sql
            return context

        except Exception as e:
            context["error"] = f"SQL generation failed: {str(e)}"
            return context
