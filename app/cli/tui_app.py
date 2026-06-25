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
            placeholder="Ask a question  ·  /profile  ·  /history  ·  /export",
            id="input",
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

    def _export_last_result(self, custom_name: str = None):
        """
        Save the last query result to CSV or Excel.

        custom_name: optional filename from "/export myfile.csv" or
                     "/export myfile.xlsx". Extension determines format.
                     Falls back to a timestamped .csv if not given.
        """
        try:
            from pathlib import Path
            from datetime import datetime
            import pandas as pd
            import re

            result = getattr(self.pipeline, "last_result", None)

            if result is None:
                self.chat_history += (
                    f"\n📤 Nothing to export yet — run a query first.\n"
                )
                self.chat.update(self.chat_history)
                return

            # Normalise to a DataFrame
            if isinstance(result, pd.Series):
                export_df = result.reset_index()
                export_df.columns = [
                    self.pipeline.last_intent.get("dimension", "category"),
                    self.pipeline.last_intent.get("metric") or "value",
                ]
            elif isinstance(result, pd.DataFrame):
                export_df = result
            else:
                self.chat_history += (
                    f"\n❌ Could not export — unexpected result type.\n"
                )
                self.chat.update(self.chat_history)
                return

            save_dir = Path.home() / "querymind_sessions"
            save_dir.mkdir(parents=True, exist_ok=True)

            # ── Resolve filename and format ────────────────────────────────
            ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")

            if custom_name:
                # Sanitise: strip path separators, keep just the filename
                safe_name = re.sub(r'[\\/:*?"<>|]', "_", custom_name)
                suffix = Path(safe_name).suffix.lower()
                if suffix not in (".csv", ".xlsx"):
                    safe_name += ".csv"
                    suffix = ".csv"
                export_path = save_dir / safe_name
            else:
                export_path = save_dir / f"export_{ts}.csv"
                suffix = ".csv"

            query_text = self.pipeline.last_query or "(query not recorded)"

            # ── Write file ──────────────────────────────────────────────────
            if suffix == ".xlsx":
                # Embed the query as a header row above the table
                with pd.ExcelWriter(export_path, engine="openpyxl") as writer:
                    export_df.to_excel(
                        writer, index=False, sheet_name="Result", startrow=2
                    )
                    ws = writer.sheets["Result"]
                    ws["A1"] = f"Query: {query_text}"
                    ws["A2"] = (
                        f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
            else:
                # CSV: prepend query as a comment-style first line, then blank line
                with open(export_path, "w", encoding="utf-8", newline="") as f:
                    f.write(f"# Query: {query_text}\n")
                    f.write(
                        f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                export_df.to_csv(export_path, mode="a", index=False)

            self.chat_history += (
                f"\n📤 Exported {len(export_df):,} rows to:\n   {export_path}\n"
            )
            self.chat.update(self.chat_history)

        except Exception as e:
            self.chat_history += f"\n❌ Export failed: {e}\n"
            self.chat.update(self.chat_history)

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

        if q_lower in ("exit", "quit", "/q", "/quit", ":q", "/exit", "/bye", "bye"):
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

        if q_lower.startswith(("/export", "/e ", "export")) or q_lower in (
            "/export",
            "/e",
            "export",
        ):
            self.chat_history += f"\n>> {query}"
            self.chat.update(self.chat_history)
            # Parse optional filename: "/export myfile.csv" or "/export myfile.xlsx"
            parts = query.strip().split(maxsplit=1)
            custom_name = parts[1].strip() if len(parts) > 1 else None
            self._export_last_result(custom_name)
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
