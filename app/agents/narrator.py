class Narrator:
    """
    Final layer: formats and cleans the output before sending to UI
    """

    def run(self, context):
        answer = context.get("answer")

        if not answer:
            return context

        try:
            # Clean duplicate emojis
            answer = answer.replace("💡 💡", "💡")

            # Ensure spacing
            answer = answer.strip()

            # Add fallback formatting if plain text
            if not any(x in answer for x in ["💡", "📊", "📌"]):
                answer = f"💡 {answer}"

            context["answer"] = answer
            return context

        except Exception:
            return context
