from app.core.pipeline import QueryMindPipeline
from app.cli.tui_app import QueryMindApp

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
import pandas as pd
import os

console = Console()


# ----------------------------
# HELPERS
# ----------------------------


def normalize_column(col: str) -> str:
    return col.lower().strip().replace(" ", "_")


def validate_column(input_col: str, columns: list) -> str | None:
    col = normalize_column(input_col)
    if col not in columns:
        console.print(f"[red]❌ '{col}' not found. Choose from the list above.[/red]")
        return None
    return col


def prompt_column(message: str, columns: list, optional: bool = False) -> str | None:
    while True:
        value = (
            Prompt.ask(f"[cyan]{message}[/cyan]", default="")
            if optional
            else Prompt.ask(f"[cyan]{message}[/cyan]")
        )

        if optional and value.strip() == "":
            return None

        validated = validate_column(value, columns)
        if validated:
            return validated


def detect_column_types(df: pd.DataFrame) -> tuple[list, list, list]:
    """Returns (numeric_cols, categorical_cols, datetime_cols)."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    obj_cols = df.select_dtypes(exclude="number").columns.tolist()

    datetime_cols = []
    categorical = []
    for col in obj_cols:
        sample = df[col].dropna().head(20)
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
        if col in numeric:
            col_type = "[green]numeric[/green]"
        elif col in datetime:
            col_type = "[magenta]datetime[/magenta]"
        else:
            col_type = "[yellow]categorical[/yellow]"

        sample = df[col].dropna().head(3).tolist()
        sample_str = ", ".join(str(v) for v in sample)
        table.add_row(col, col_type, sample_str)

    console.print(table)


# ----------------------------
# MAIN
# ----------------------------


def main():
    console.print(
        Panel.fit(
            "[bold cyan]🧠 QueryMind[/bold cyan]\n[green]CLI AI Data Analyst[/green]",
            border_style="blue",
        )
    )

    # ----------------------------
    # FILE INPUT
    # ----------------------------
    while True:
        file_path = Prompt.ask("\n[cyan]📁 Enter CSV file path[/cyan]")
        try:
            df = pd.read_csv(file_path)
            console.print(
                f"[green]✅ Loaded {len(df):,} rows × {len(df.columns)} columns[/green]"
            )
            break
        except Exception as e:
            console.print(f"[red]❌ Failed to load: {e}[/red]")
            console.print("[yellow]Please try again.[/yellow]")

    # Normalise column names
    df.columns = [normalize_column(col) for col in df.columns]
    columns = df.columns.tolist()

    numeric_cols, categorical_cols, datetime_cols = detect_column_types(df)

    # Show detected columns
    console.print()
    show_columns(df, numeric_cols, categorical_cols, datetime_cols)

    # ----------------------------
    # SEMANTIC MAPPING
    # ----------------------------
    console.print("\n[bold cyan]🧠 Help me understand your data[/bold cyan]")
    console.print("[dim]Use column names exactly as shown above.[/dim]\n")

    # Suggest defaults
    default_metric = numeric_cols[0] if numeric_cols else ""
    default_dimension = categorical_cols[0] if categorical_cols else ""
    default_time = datetime_cols[0] if datetime_cols else ""

    if default_metric:
        console.print(f"[dim]  Suggested metric    → {default_metric}[/dim]")
    if default_dimension:
        console.print(f"[dim]  Suggested dimension → {default_dimension}[/dim]")
    if default_time:
        console.print(f"[dim]  Suggested time      → {default_time}[/dim]")
    console.print()

    metric = prompt_column(
        "👉 Which column is the main VALUE to measure? (metric)", columns
    )
    dimension = prompt_column(
        "👉 Which column to GROUP BY by default? (dimension)", columns
    )
    time_col = prompt_column(
        "👉 Time column for trend queries? (optional — press Enter to skip)",
        columns,
        optional=True,
    )

    semantic_map = {
        "metric": metric,
        "dimension": dimension,
        "time": time_col,
    }

    console.print(
        f"\n[green]✅ Semantic map set:[/green] metric=[bold]{metric}[/bold]  "
        f"dimension=[bold]{dimension}[/bold]  "
        f"time=[bold]{time_col or 'none'}[/bold]"
    )

    # ----------------------------
    # PIPELINE + TUI
    # ----------------------------
    console.print("\n[green]✅ Launching QueryMind UI...[/green]\n")

    pipeline = QueryMindPipeline(file_path, semantic_map)
    app = QueryMindApp(pipeline)
    app.run()

    os.system("cls" if os.name == "nt" else "clear")
    print("🧠 QueryMind closed.\n")


if __name__ == "__main__":
    main()
