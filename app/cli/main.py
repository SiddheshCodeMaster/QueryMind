import os
import sys
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from app.core.pipeline import QueryMindPipeline
from app.cli.tui_app import QueryMindApp
from app.data.connectors.csv_connector import CSVConnector
from app.data.connectors.excel_connector import ExcelConnector
from app.executor.sheet_selector import prompt_sheet_selection

console = Console()

EXCEL_EXTS = {".xlsx", ".xls", ".xlsm", ".xlsb"}
CSV_EXTS = {".csv", ".tsv"}

# Words that mean "I want to quit" at any prompt
EXIT_WORDS = {"exit", "quit", "/exit", "/quit", "bye", "q", ":q"}


# ─────────────────────────────────────────────
# CLEAN EXIT SIGNAL
# ─────────────────────────────────────────────


class UserExitError(Exception):
    """Raised when the user types an exit command at any prompt."""

    pass


def ask(message: str, default: str = None) -> str:
    """
    Wrapper around Prompt.ask that:
    - Checks for exit words before returning
    - Raises UserExitError so the caller doesn't need any special logic
    - Handles KeyboardInterrupt (Ctrl+C) as a clean exit too
    """
    try:
        value = (
            Prompt.ask(message, default=default)
            if default is not None
            else Prompt.ask(message)
        )
    except (KeyboardInterrupt, EOFError):
        raise UserExitError()

    if value.strip().lower() in EXIT_WORDS:
        raise UserExitError()

    return value


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────


def normalize_column(col: str) -> str:
    return col.lower().strip().replace(" ", "_")


def validate_column(input_col: str, columns: list) -> str | None:
    col = normalize_column(input_col)
    if col not in columns:
        console.print(f"[red]❌ '{col}' not found. Choose from the list above.[/red]")
        return None
    return col


def prompt_column(message: str, columns: list, optional: bool = False) -> str | None:
    """Prompt for a column name, with exit-word detection on every attempt."""
    while True:
        value = (
            ask(f"[cyan]{message}[/cyan]", default="")
            if optional
            else ask(f"[cyan]{message}[/cyan]")
        )
        if optional and value.strip() == "":
            return None
        validated = validate_column(value, columns)
        if validated:
            return validated


def detect_column_types(df: pd.DataFrame) -> tuple:
    """Returns (numeric_cols, categorical_cols, datetime_cols)."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    obj_cols = df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols, categorical = [], []
    for col in obj_cols:
        if col == "_sheet":
            continue
        col_data = df[col]
        if isinstance(col_data, pd.DataFrame):
            col_data = col_data.iloc[:, 0]  # duplicate col name → take first
        sample = col_data.dropna().head(20)
        try:
            pd.to_datetime(sample, infer_datetime_format=True)
            datetime_cols.append(col)
        except Exception:
            categorical.append(col)
    return numeric, categorical, datetime_cols


def show_columns(df: pd.DataFrame, numeric: list, categorical: list, datetime: list):
    table = Table(title="Detected Columns", border_style="blue", show_lines=False)
    table.add_column("Column", style="bold white")
    table.add_column("Type", style="dim")
    table.add_column("Sample values", style="dim")

    for col in df.columns:
        if col == "_sheet":
            continue
        if col in numeric:
            col_type = "[green]numeric[/green]"
        elif col in datetime:
            col_type = "[magenta]datetime[/magenta]"
        else:
            col_type = "[yellow]categorical[/yellow]"
        try:
            col_data = df[col]
            # Duplicate column names → df[col] returns DataFrame not Series
            if isinstance(col_data, pd.DataFrame):
                col_data = col_data.iloc[:, 0]
            sample = col_data.dropna().head(3).tolist()
            sample_str = ", ".join(str(v) for v in sample)
        except Exception:
            sample_str = "(error reading samples)"
        table.add_row(col, col_type, sample_str)

    console.print(table)


# ─────────────────────────────────────────────
# FILE LOADING
# ─────────────────────────────────────────────


def load_file(file_path: str) -> tuple:
    """
    Returns (connector, preview_df).
    Raises RuntimeError for bad files, UserExitError if user quits mid-flow.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in EXCEL_EXTS:
        selected_sheets = prompt_sheet_selection(
            file_path
        )  # exit-aware (see sheet_selector.py)
        if not selected_sheets:
            raise RuntimeError("No sheets selected.")

        connector = ExcelConnector(file_path, selected_sheets)

        frames = []
        xl = pd.ExcelFile(file_path)
        for s in selected_sheets:
            df = xl.parse(s, nrows=100)
            df.columns = [normalize_column(c) for c in df.columns]
            df["_sheet"] = s
            frames.append(df)
        preview_df = pd.concat(frames, ignore_index=True, sort=False)

        real_cols = [c for c in preview_df.columns if c != "_sheet"]
        if len(real_cols) < 2:
            col_name = real_cols[0] if real_cols else "none"
            raise RuntimeError(
                f"The selected sheet(s) only have 1 column ('{col_name}'). "
                f"QueryMind needs at least one metric column and one dimension column. "
                f"Please select sheets with 2 or more columns."
            )
        return connector, preview_df

    elif ext in CSV_EXTS:
        from app.data.connectors.csv_connector import (
            _detect_encoding,
            _detect_delimiter,
        )

        connector = CSVConnector(file_path)
        encoding = _detect_encoding(file_path)
        delimiter = _detect_delimiter(file_path, encoding)
        try:
            preview_df = pd.read_csv(
                file_path,
                encoding=encoding,
                sep=delimiter,
                nrows=100,
                on_bad_lines="warn",
            )
        except pd.errors.EmptyDataError:
            raise RuntimeError(
                f"'{file_path}' is completely empty. "
                f"Please provide a file with headers and at least one row of data."
            )
        if preview_df.empty:
            raise RuntimeError(
                f"'{file_path}' contains only headers and no data rows. "
                f"Please provide a file with at least one row of data."
            )
        preview_df.columns = [normalize_column(c) for c in preview_df.columns]
        # Warn about duplicate column names after normalization
        dupes = [
            c for c in preview_df.columns if preview_df.columns.tolist().count(c) > 1
        ]
        if dupes:
            unique_dupes = list(dict.fromkeys(dupes))  # preserve order, deduplicate
            console.print(
                f"[yellow]⚠️  Duplicate column names detected after normalization: "
                f"{unique_dupes}. Only the first occurrence of each will be used.[/yellow]"
            )
            preview_df = preview_df.loc[:, ~preview_df.columns.duplicated()]
        if len(preview_df.columns) < 2:
            raise RuntimeError(
                f"'{file_path}' only has 1 column ('{preview_df.columns[0]}'). "
                f"QueryMind needs at least one metric column and one dimension column. "
                f"Please provide a file with 2 or more columns."
            )
        return connector, preview_df

    else:
        raise RuntimeError(
            f"Unsupported file type: '{ext}'. "
            f"Supported: {sorted(EXCEL_EXTS | CSV_EXTS)}"
        )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────


def main():
    console.print(
        Panel.fit(
            "[bold cyan]🧠 QueryMind[/bold cyan]\n[green]CLI AI Data Analyst[/green]",
            border_style="blue",
        )
    )
    console.print(
        "[dim]  Type [bold]exit[/bold] or [bold]quit[/bold] at any prompt to leave.[/dim]\n"
    )

    try:
        # ── File input ────────────────────────────────────────────────────
        while True:
            file_path = ask(
                "\n[cyan]📁 Enter file path[/cyan] [dim](.csv, .xlsx, .xls)[/dim]"
            )
            try:
                connector, preview_df = load_file(file_path)
                rows = len(preview_df)
                console.print(
                    f"[green]✅ Loaded {rows:,} preview rows × "
                    f"{len([c for c in preview_df.columns if c != '_sheet'])} columns[/green]"
                )
                break
            except UserExitError:
                raise  # bubble up — sheet selector raised it mid-flow
            except RuntimeError as e:
                console.print(f"[red]❌ {e}[/red]")
                console.print(
                    "[yellow]Please try again or type 'exit' to quit.[/yellow]"
                )
            except Exception as e:
                console.print(f"[red]❌ Failed to load: {e}[/red]")
                console.print(
                    "[yellow]Please try again or type 'exit' to quit.[/yellow]"
                )

        columns_all = [c for c in preview_df.columns if c != "_sheet"]
        numeric_cols, categorical_cols, datetime_cols = detect_column_types(preview_df)

        # ── Show column overview ──────────────────────────────────────────
        console.print()
        show_columns(preview_df, numeric_cols, categorical_cols, datetime_cols)

        # ── Semantic mapping ──────────────────────────────────────────────
        console.print("\n[bold cyan]🧠 Help me understand your data[/bold cyan]")
        console.print("[dim]Use column names exactly as shown above.[/dim]\n")

        default_metric = numeric_cols[0] if numeric_cols else ""
        default_dimension = categorical_cols[0] if categorical_cols else ""
        default_time = datetime_cols[0] if datetime_cols else ""

        if default_metric:
            console.print(f"[dim]  Suggested metric    → {default_metric}[/dim]")
        if default_dimension:
            console.print(f"[dim]  Suggested dimension → {default_dimension}[/dim]")
        if default_time:
            console.print(f"[dim]  Suggested time col  → {default_time}[/dim]")
        console.print()

        metric = prompt_column(
            "👉 Which column is the main VALUE to measure? (metric)", columns_all
        )
        dimension = prompt_column(
            "👉 Which column to GROUP BY by default? (dimension)", columns_all
        )
        time_col = prompt_column(
            "👉 Time column for trend queries? (optional — press Enter to skip)",
            columns_all,
            optional=True,
        )

        semantic_map = {"metric": metric, "dimension": dimension, "time": time_col}

        console.print(
            f"\n[green]✅ Semantic map:[/green] "
            f"metric=[bold]{metric}[/bold]  "
            f"dimension=[bold]{dimension}[/bold]  "
            f"time=[bold]{time_col or 'none'}[/bold]"
        )

        # ── Build pipeline ────────────────────────────────────────────────
        console.print("\n[dim]Loading data and building pipeline…[/dim]")
        try:
            pipeline = QueryMindPipeline(connector, semantic_map)
        except RuntimeError as e:
            console.print(f"[red]❌ Pipeline failed to start: {e}[/red]")
            return

        console.print("[green]✅ Launching QueryMind UI…[/green]\n")

        app = QueryMindApp(pipeline)
        app.run()

    except UserExitError:
        pass  # fall through to goodbye message

    os.system("cls" if os.name == "nt" else "clear")
    console.print(
        Panel.fit(
            "[bold cyan]👋 Goodbye![/bold cyan]\n"
            "[dim]Thanks for using QueryMind.[/dim]",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    main()
