import json

from app.llm.ollama_client import OllamaClient


class LLMInterpreter:
    """
    Uses LLM to convert natural language query → structured intent
    """

    def __init__(self):
        self.client = OllamaClient()

    def build_prompt(self, query, columns):
        return f"""
        You are a data analyst.

        Your task is to convert a user query into structured JSON.

        Available columns:
        {columns}

        User query:
        "{query}"

        Return ONLY valid JSON in this format:

        {{
        "metric": "<column_name>",
        "dimension": "<column_name>",
        "operation": "sum | mean | count",
        "query_type": "comparison | aggregation | trend | top_n",
        "limit": number or null
        }}

        Rules:
        - Use ONLY column names from the list
        - "revenue", "sales", "spending" → numeric columns
        - "highest", "most" → comparison
        - "top N" → top_n
        - "average" → mean
        - If unclear → choose best match
        - DO NOT explain anything
"""

    def safe_parse_json(self, text):
        try:
            # Extract JSON block if extra text exists
            start = text.find("{")
            end = text.rfind("}") + 1
            json_str = text[start:end]

            return json.loads(json_str)

        except Exception:
            return None

    def validate_intent(self, intent, columns):
        if not intent:
            return False

        if intent.get("metric") not in columns:
            return False

        if intent.get("dimension") not in columns:
            return False

        return True

    def run(self, context):
        query = context["user_query"]
        schema = context["schema"]["columns"]

        columns = [col["name"] for col in schema]

        prompt = self.build_prompt(query, columns)

        response = self.client.generate(prompt)

        intent = self.safe_parse_json(response)

        # VALIDATION:
        if not self.validate_intent(intent, columns):
            context["error"] = "LLM failed to generate valid intent"
            return context

        context["intent"] = intent
        context["llm_used"] = True

        return context
