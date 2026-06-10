"""
JSONConnector — loads .json and .jsonl files into a DataFrame.

Supported structures
--------------------
1. Flat array          [{"a": 1}, {"a": 2}]
2. Nested-key          {"data": [...], "meta": {...}}  → user picks the key
3. Nested records      [{"a": 1, "b": {"c": 2}}]      → auto-flattened
4. JSON Lines (.jsonl) one JSON object per line
"""

import json
import pandas as pd
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

from app.data.type_caster import smart_cast_df

console = Console()


def _normalize_col(col: str) -> str:
    return col.lower().strip().replace(" ", "_").replace(".", "_")


def _detect_structure(data) -> tuple:
    """
    Returns (structure_type, array_keys) where:
      structure_type: "flat_array" | "nested_key" | "nested_records" | "unknown"
      array_keys:     list of keys containing arrays (only for nested_key)
    """
    if isinstance(data, list):
        if not data:
            return "empty", []
        if all(isinstance(r, dict) for r in data):
            has_nested = any(
                isinstance(v, dict)
                for r in data[:10]  # sample first 10 rows
                for v in r.values()
            )
            return ("nested_records" if has_nested else "flat_array"), []

    if isinstance(data, dict):
        array_keys = [
            k
            for k, v in data.items()
            if isinstance(v, list) and v and isinstance(v[0], dict)
        ]
        if array_keys:
            return "nested_key", array_keys

    return "unknown", []


def _load_to_df(data, structure: str, chosen_key: str = None) -> pd.DataFrame:
    """Convert parsed JSON data to a DataFrame based on detected structure."""
    if structure == "flat_array":
        return pd.DataFrame(data)

    elif structure == "nested_records":
        return pd.json_normalize(data)

    elif structure == "nested_key" and chosen_key:
        records = data[chosen_key]
        # Also flatten if those records have nested objects
        has_nested = any(isinstance(v, dict) for r in records[:10] for v in r.values())
        if has_nested:
            return pd.json_normalize(records)
        return pd.DataFrame(records)

    return pd.DataFrame()


class JSONConnector:
    """
    Loads a .json or .jsonl file into a DataFrame.

    For nested JSON with multiple array keys, prompts the user
    interactively to choose which key to use as the table.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def run(self, context: dict) -> dict:
        path = Path(self.file_path)

        # ── Load raw JSON ─────────────────────────────────────────────────
        try:
            if path.suffix.lower() == ".jsonl":
                # JSON Lines — one object per line
                df = pd.read_json(self.file_path, lines=True)
                df.columns = [_normalize_col(c) for c in df.columns]
                df = smart_cast_df(df)
                return self._finalise(context, df)

            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except json.JSONDecodeError as e:
            context["error"] = f"Invalid JSON file: {e}"
            return context
        except Exception as e:
            context["error"] = f"Failed to load JSON: {e}"
            return context

        # ── Detect structure ──────────────────────────────────────────────
        structure, array_keys = _detect_structure(data)

        if structure == "empty":
            context["error"] = "JSON file is empty."
            return context

        if structure == "unknown":
            context["error"] = (
                "Unrecognised JSON structure.\n"
                "QueryMind expects an array of objects or a dict containing one.\n"
                'Example: [{"col": val}, ...] or {"data": [{"col": val}, ...]}'
            )
            return context

        # ── Nested key — ask user which key to use ────────────────────────
        chosen_key = None
        if structure == "nested_key":
            if len(array_keys) == 1:
                chosen_key = array_keys[0]
                console.print(
                    f"\n[dim]📋 Nested JSON detected. "
                    f"Using key '[bold]{chosen_key}[/bold]' as the data table.[/dim]"
                )
            else:
                console.print(
                    f"\n[yellow]📋 Nested JSON detected with multiple array keys:[/yellow]"
                )
                for i, k in enumerate(array_keys, 1):
                    count = len(data[k])
                    console.print(f"  [bold]{i}.[/bold] {k}  ({count:,} records)")

                while True:
                    raw = Prompt.ask(
                        "[cyan]👉 Which key contains your data? (enter number)[/cyan]"
                    ).strip()
                    if raw.lower() in {"exit", "quit"}:
                        context["error"] = "Cancelled by user."
                        return context
                    try:
                        idx = int(raw) - 1
                        if 0 <= idx < len(array_keys):
                            chosen_key = array_keys[idx]
                            break
                        console.print(
                            f"[red]❌ Enter a number between 1 and {len(array_keys)}[/red]"
                        )
                    except ValueError:
                        console.print("[red]❌ Please enter a number[/red]")

        # ── Convert to DataFrame ──────────────────────────────────────────
        try:
            df = _load_to_df(data, structure, chosen_key)
        except Exception as e:
            context["error"] = f"Failed to parse JSON into table: {e}"
            return context

        if df.empty:
            context["error"] = "JSON parsed successfully but produced an empty table."
            return context

        # Normalise column names + smart cast
        df.columns = [_normalize_col(c) for c in df.columns]
        df = smart_cast_df(df)

        if structure == "nested_records":
            console.print(
                f"[dim]📋 Nested records flattened — "
                f"dot notation converted to underscores "
                f"(e.g. address.city → address_city)[/dim]"
            )

        print(f"✅ JSON loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")
        print(f"   Columns: {df.columns.tolist()}")

        return self._finalise(context, df)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _finalise(self, context: dict, df: pd.DataFrame) -> dict:
        if len(df.columns) < 2:
            context["error"] = (
                f"Only 1 column found ('{df.columns[0]}'). "
                f"QueryMind needs at least a metric and a dimension column."
            )
            return context

        context["dataframe"] = df
        context["schema"] = {
            "columns": [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
        }
        return context
