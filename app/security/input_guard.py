BLOCKED_KEYWORDS = ["password", "ssn", "credit card", "api key", " private key"]


class InputGuard:
    def run(self, context):
        query = context["user_query"].lower()

        for word in BLOCKED_KEYWORDS:
            if word in query:
                context["error"] = "Sensitive Query detected"
                return context

        return context
