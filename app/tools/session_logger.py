"""
SessionLogger — appends every query and answer to a single persistent
Markdown file: ~/querymind_sessions/querymind_history.md

The file grows forever across all sessions. Each session gets a clear
header block so the file stays readable. The /history command in the
TUI reads the last N entries back from this file.

File format
-----------
# QueryMind Session — 2024-01-15 14:32
**File:** sales.xlsx  |  **Metric:** sales  |  **Dimension:** region

---

## Q1 · 14:32:01
**Query:** top 5 regions by sales
📊 ...result...

---

## Q2 · 14:33:45
...

============================  SESSION END  ============================

"""

import re
from datetime import datetime
from pathlib import Path


HISTORY_FILENAME = "querymind_history.md"
SESSION_END_MARKER = "\n\n" + "=" * 30 + "  SESSION END  " + "=" * 30 + "\n\n"


class SessionLogger:
    """
    Appends queries + answers to a single persistent history file.
    Each run opens a new session block inside the same file.
    """

    def __init__(
        self,
        file_path: str,
        semantic_map: dict,
        save_dir: str | None = None,
    ):
        self.file_path = file_path
        self.semantic_map = semantic_map
        self.query_count = 0
        self._closed = False
        self._session_queries = []  # (query, answer) tuples for /history

        # Resolve save directory
        self.save_dir = (
            Path(save_dir) if save_dir else Path.home() / "querymind_sessions"
        )
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.save_dir / HISTORY_FILENAME

        self._write_session_header()

    # ── Public API ────────────────────────────────────────────────────────

    def log(self, query: str, answer: str, error: str | None = None):
        """Append one query+answer pair to the history file."""
        if self._closed:
            return

        self.query_count += 1
        ts = datetime.now().strftime("%H:%M:%S")

        lines = [
            f"## Q{self.query_count} · {ts}",
            f"**Query:** {query}",
            "",
        ]

        if error:
            lines += [f"❌ {error}", ""]
            display = f"❌ {error}"
        else:
            clean = self._clean(answer)
            lines += [clean, ""]
            display = clean

        lines += ["---", ""]

        self._append("\n".join(lines))
        self._session_queries.append((query, display))

    def close(self) -> str:
        """Write session-end marker and return path to history file."""
        if self._closed:
            return str(self.history_file)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer = (
            f"*Session ended: {ts} · "
            f"{self.query_count} "
            f"quer{'y' if self.query_count == 1 else 'ies'} logged.*"
        )
        self._append(footer + SESSION_END_MARKER)
        self._closed = True
        return str(self.history_file)

    def get_recent(self, n: int = 5) -> list[tuple[str, str]]:
        """Return the last N (query, answer) pairs from this session."""
        return self._session_queries[-n:]

    @property
    def path(self) -> str:
        return str(self.history_file)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _write_session_header(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        fname = Path(self.file_path).name or "unknown"
        metric = self.semantic_map.get("metric", "—")
        dim = self.semantic_map.get("dimension", "—")
        time = self.semantic_map.get("time") or "none"

        header = (
            f"# QueryMind Session — {ts}\n\n"
            f"**File:** {fname}  |  "
            f"**Metric:** {metric}  |  "
            f"**Dimension:** {dim}  |  "
            f"**Time:** {time}\n\n"
            f"---\n\n"
        )
        # Append to existing file (create if not exists)
        with self.history_file.open("a", encoding="utf-8") as f:
            f.write(header)

    def _append(self, text: str):
        with self.history_file.open("a", encoding="utf-8") as f:
            f.write(text)

    def _clean(self, text: str) -> str:
        """Strip Rich markup tags so saved Markdown is clean."""
        text = re.sub(r"\[/?[a-zA-Z0-9_ ]+\]", "", text)
        return text.strip()
