from textual.app import App
from textual.widgets import Header, Footer, Input, Static
from app.core.pipeline import QueryMindPipeline
from app.core.context import Context
import time


class QueryMindApp(App):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self.chat_history = "🧠 QueryMind Ready\n"  # ✅ store manually

    def compose(self):
        yield Header()

        self.chat = Static(self.chat_history, id="chat")
        yield self.chat

        self.input = Input(placeholder="ask your question...")
        yield self.input

        yield Footer()

    async def on_input_submitted(self, event):
        query = event.value.strip()

        if not query:
            return

        if query.lower() in ["exit", "quit"]:
            # import os

            # os.system("cls" if os.name == "nt" else "clear")
            self.exit()
            print("🧠 QueryMind closed.\n")

            # await self.action_quit()
            return

        self.chat_history = "🧠 QueryMind Ready\nType 'exit' or press 'q' to quit\n"

        context = Context(query)
        result = self.pipeline.run(context)

        if result.get("error"):
            response = f"❌ {result['error']}"
        else:
            response = result.get("answer", "No answer")

        self.chat_history += f"\n💡 {response}\n"

        self.chat.update(self.chat_history)

        self.input.value = ""
