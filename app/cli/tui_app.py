from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from app.core.pipeline import QueryMindPipeline
from app.core.context import Context


class QueryMindApp(App):
    CSS = """
    #top {
        height: 10;
    }

    #chat {
        border: round green;
        padding: 1;
    }

    #input {
        dock: bottom;
    }
    """

    BINDINGS = [("q", "quit", "Quit"), ("ctrl+c", "quit", "Quit"), ("/bye", "bye")]

    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self.chat_history = "🧠 QueryMind Ready\n"

    def compose(self) -> ComposeResult:
        yield Header()

        # TOP PANEL (split)
        with Horizontal(id="top"):
            yield Static(self.get_ascii_banner(), id="banner")
            yield Static(self.get_system_info(), id="system")

        # CHAT AREA
        self.chat = Static(self.chat_history, id="chat")
        yield self.chat

        # INPUT
        self.input = Input(placeholder="Type your message...", id="input")
        yield self.input

        yield Footer()

    # ----------------------------
    # UI CONTENT
    # ----------------------------
    def get_ascii_banner(self):
        return "   🐧 QueryMind\n   AI Data Analyst\n"

    def get_system_info(self):
        return "Agent: QueryMind\nMode: Local Analysis\nModel: Rule-based (for now)\n"

    # ----------------------------
    # INPUT HANDLER
    # ----------------------------
    async def on_input_submitted(self, event):
        query = event.value.strip()

        if not query:
            return

        if query.lower() in ["exit", "quit", "bye", "/bye"]:
            self.exit()
            return

        # Add user message
        self.chat_history += f"\n>> {query}"

        context = Context(query)
        result = self.pipeline.run(context)

        if result.get("error"):
            response = f"❌ {result['error']}"
        else:
            response = result.get("answer", "No answer")

        self.chat_history += f"\n💡 {response}\n"

        self.chat.update(self.chat_history)

        self.input.value = ""
