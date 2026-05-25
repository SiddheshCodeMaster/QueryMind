"""
SessionLogger — records every query and answer to a Markdown file.

One file per QueryMind session, named with a timestamp so sessions
never overwrite each other. Saved to ~/querymind_sessions/ by default.

File format
-----------
# QueryMind Session — 2024-01-15 14:32
**File:** sales.csv
**Metric:** sales  |  **Dimension:** region  |  **Time:** order_date

---

## Q1 · 14:32:01
**Query:** top 5 regions by sales

📊 Top 5 by Region
────────────────────────────────────────────────────────────
  East    ████████████████████   592,171.49
  ...

💡 Insight
  East leads with total Sales of $592,171.49 (30.8% of total).

---
"""

import os
from datetime import datetime
from pathlib import Path


class SessionLogger:
    """
    Appends queries and answers to a Markdown session file.
    Thread-safe for single-threaded Textual use.
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
        self.enabled = True

        # Resolve save directory
        if save_dir:
            self.save_dir = Path(save_dir)
        else:
            self.save_dir = Path.home() / "querymind_sessions"

        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Session file name: querymind_2024-01-15_14-32-00.md
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.session_file = self.save_dir / f"querymind_{ts}.md"

        self._write_header()

    # ── Public API ────────────────────────────────────────────────────────

    def log(self, query: str, answer: str, error: str | None = None):
        """Append one query+answer pair to the session file."""
        if not self.enabled:
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
        else:
            # Clean up ANSI/Rich markup that doesn't render in Markdown
            clean_answer = self._clean(answer)
            lines += [clean_answer, ""]

        lines.append("---")
        lines.append("")

        self._append("\n".join(lines))

    def close(self):
        """Write a footer and return the path to the saved file."""
        if not self.enabled:
            return None

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer = (
            f"\n*Session ended: {ts} · "
            f"{self.query_count} quer{'y' if self.query_count == 1 else 'ies'} logged.*\n"
        )
        self._append(footer)
        return str(self.session_file)

    @property
    def path(self) -> str:
        return str(self.session_file)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _write_header(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        fname = Path(self.file_path).name
        metric = self.semantic_map.get("metric", "—")
        dim = self.semantic_map.get("dimension", "—")
        time = self.semantic_map.get("time") or "none"

        header = (
            f"# QueryMind Session — {ts}\n\n"
            f"**File:** {fname}  \n"
            f"**Metric:** {metric}  |  "
            f"**Dimension:** {dim}  |  "
            f"**Time:** {time}\n\n"
            f"---\n\n"
        )
        self.session_file.write_text(header, encoding="utf-8")

    def _append(self, text: str):
        with self.session_file.open("a", encoding="utf-8") as f:
            f.write(text)

    def _clean(self, text: str) -> str:
        """
        Strip Rich markup tags ([bold], [green], etc.) so the saved
        Markdown is readable in any text editor or GitHub preview.
        """
        import re

        # Remove Rich colour/style tags like [bold cyan], [/green], etc.
        text = re.sub(r"\[/?[a-zA-Z_ ]+\]", "", text)
        return text.strip()
