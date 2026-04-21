from app.core.pipeline import QueryMindPipeline
from app.cli.tui_app import QueryMindApp

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import pandas as pd
import os

console = Console()


# ----------------------------
# HELPERS
# ----------------------------
def normalize_column(col):
    return col.lower().strip().replace(" ", "_")


def validate_column(input_col, columns):
    col = normalize_column(input_col)

    if col not in columns:
        console.print(f"[red]❌ Invalid column: {col}[/red]")
        return None

    return col


def prompt_column(message, columns, optional=False):
    while True:
        value = Prompt.ask(message, default="") if optional else Prompt.ask(message)

        if optional and value == "":
            return None

        validated = validate_column(value, columns)

        if validated:
            return validated


# ----------------------------
# MAIN
# ----------------------------
def main():
    console.print(
        Panel.fit(
            "[bold cyan]🧠 QueryMind[/bold cyan]\n"
            "[green]AI Data Analyst Terminal[/green]",
            border_style="blue",
        )
    )

    # ----------------------------
    # FILE INPUT
    # ----------------------------
    while True:
        file_path = Prompt.ask("\n📁 Enter file path")

        try:
            df = pd.read_csv(file_path)
            break

        except Exception as e:
            console.print(f"[red]❌ Failed to load file: {str(e)}[/red]")
            console.print("[yellow]Please try again.[/yellow]")

    # Normalize columns
    df.columns = [normalize_column(col) for col in df.columns]
    columns = df.columns.tolist()

    # Show columns
    console.print("\n[bold yellow]📊 Detected Columns:[/bold yellow]")
    for col in columns:
        console.print(f"- {col}")

    # ----------------------------
    # SEMANTIC MAPPING
    # ----------------------------
    console.print("\n[bold cyan]🧠 Help me understand your data:[/bold cyan]")

    metric = prompt_column("👉 Metric column", columns)
    dimension = prompt_column("👉 Default dimension", columns)
    time_col = prompt_column("👉 Time column (optional)", columns, optional=True)

    semantic_map = {
        "metric": metric,
        "dimension": dimension,
        "time": time_col,
    }

    console.print("\n[green]✅ Launching QueryMind UI...[/green]\n")

    # ----------------------------
    # PIPELINE
    # ----------------------------
    pipeline = QueryMindPipeline(file_path, semantic_map)

    # ----------------------------
    # START TEXTUAL APP
    # ----------------------------
    app = QueryMindApp(pipeline)
    app.run()
    os.system("cls" if os.name == "nt" else "clear")
    print("🧠 QueryMind closed.\n")


if __name__ == "__main__":
    main()
