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

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, pipeline: QueryMindPipeline):
        super().__init__()
        self.pipeline = pipeline
        self.chat_history = "🧠 QueryMind Ready\n"

        # Show active sheet in system info if available
        active = getattr(pipeline, "_base_context", {}).get("active_sheet", "")
        self._active_sheet = active

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="top"):
            yield Static(self._get_banner(), id="banner")
            yield Static(self._get_system_info(), id="system")

        self.chat = Static(self.chat_history, id="chat")
        yield self.chat

        self.input = Input(placeholder="Ask a question about your data...", id="input")
        yield self.input

        yield Footer()

    # ------------------------------------------------------------------ #

    def _get_banner(self) -> str:
        return "   🧠 QueryMind\n   AI Data Analyst\n"

    def _get_system_info(self) -> str:
        sheet_line = f"Sheet : {self._active_sheet}\n" if self._active_sheet else ""
        llm_status = (
            "LLM   : ✅ Ollama (phi)"
            if getattr(self.pipeline, "llm_available", False)
            else "LLM   : ⚠️  Offline (rule-based only)"
        )
        return f"Agent : QueryMind\nMode  : Local Analysis\n{llm_status}\n{sheet_line}"

    # ------------------------------------------------------------------ #

    async def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()

        if not query:
            return

        if query.lower() in ("exit", "quit", "/bye", "bye", "/c"):
            self.exit()
            return

        self.chat_history += f"\n>> {query}"

        context = Context(query)
        result = self.pipeline.run(context)

        if result.get("error"):
            response = f"❌ {result['error']}"
        else:
            response = result.get("answer", "No answer generated.")

        # Show which sheet the answer came from (useful in multi-sheet mode)
        active = result.get("active_sheet", "")
        if active and "+" in active:
            response = f"[{active}]\n{response}"

        self.chat_history += f"\n💡 {response}\n"
        self.chat.update(self.chat_history)
        self.input.value = ""
