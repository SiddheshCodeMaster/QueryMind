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

        self.input = Input(
            placeholder="Ask a question  ·  /profile  ·  /history", id="input"
        )
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
        try:
            history_path = self.pipeline.logger.path
        except Exception:
            history_path = ""
        history_line = (
            f"Log   : ~/querymind_sessions/querymind_history.md\n"
            if history_path
            else ""
        )
        return (
            f"Agent : QueryMind\n"
            f"Mode  : Local Analysis\n"
            f"{llm_status}\n"
            f"{history_line}"
            f"{sheet_line}"
        )

    # ------------------------------------------------------------------ #

    def _show_profile(self):
        """Run DataProfiler and display output in the TUI chat."""
        try:
            from app.tools.data_profiler import DataProfiler

            profiler = DataProfiler()

            # Build context the profiler needs
            ctx = dict(self.pipeline._base_context)
            ctx["file_path"] = getattr(
                self.pipeline,
                "_file_path",
                getattr(self.pipeline.logger, "file_path", "dataset"),
            )

            profile_text = profiler.run(ctx)
            self.chat_history += f"\n{profile_text}\n"

            self.chat.update(self.chat_history)
        except Exception as e:
            self.chat_history += f"\n❌ Profile failed: {e}\n"

            self.chat.update(self.chat_history)

    def _show_history(self):
        """Show last 5 queries from this session + path to full history file."""
        try:
            recent = self.pipeline.logger.get_recent(5)
            path = self.pipeline.logger.path

            if not recent:
                self.chat_history += (
                    f"\n📋 No queries logged yet this session.\n"
                    f"   Full history: {path}\n"
                )
            else:
                lines = [
                    f"\n📋 Last {len(recent)} quer{'y' if len(recent) == 1 else 'ies'} this session:"
                ]
                lines.append("─" * 50)
                for i, (q, a) in enumerate(recent, 1):
                    # Show query + first line of answer only
                    first_line = a.splitlines()[0] if a else "—"
                    lines.append(f"  Q{i}: {q}")
                    lines.append(
                        f"      → {first_line[:60]}{'…' if len(first_line) > 60 else ''}"
                    )
                lines.append("─" * 50)
                lines.append(f"📁 Full history: {path}")
                self.chat_history += "\n".join(lines) + "\n"

            self.chat.update(self.chat_history)
        except Exception as e:
            self.chat_history += f"\n❌ Could not load history: {e}\n"
            self.chat.update(self.chat_history)

    def _close_session(self):
        """Save session log and show the file path to user."""
        try:
            saved_path = self.pipeline.logger.close()
            if saved_path:
                self.chat_history += f"\n📝 Session saved:\n   {saved_path}\n"
                self.chat.update(self.chat_history)
        except Exception:
            pass

    def on_unmount(self) -> None:
        """Called when app closes via any method (Ctrl+C, window close)."""
        try:
            self.pipeline.logger.close()
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()

        if not query:
            return

        q_lower = query.lower().strip()
        print(f"DEBUG input: repr={repr(query)} q_lower={repr(q_lower)}")

        if q_lower in ("exit", "quit", "/q", "/quit", "/exit", "/bye", "bye"):
            self._close_session()
            self.exit()
            return

        # Slash commands — handled entirely in TUI, never reach pipeline
        if q_lower in ("/history", "/h", "history"):
            self.chat_history += f"\n>> {query}"
            self.chat.update(self.chat_history)
            self._show_history()
            self.input.value = ""
            return

        if q_lower in ("/profile", "/p", "profile"):
            self.chat_history += f"\n>> {query}"
            self.chat.update(self.chat_history)
            self._show_profile()
            self.input.value = ""
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
