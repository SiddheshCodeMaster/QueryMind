import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

console = Console()


def get_sheet_info(file_path: str) -> dict:
    """
    Returns {sheet_name: {"rows": int, "cols": int, "columns": [str]}}
    """
    xl = pd.ExcelFile(file_path)
    info = {}
    for name in xl.sheet_names:
        try:
            df = xl.parse(name, nrows=5)  # only peek — fast
            full_df = xl.parse(name)
            info[name] = {
                "rows": len(full_df),
                "cols": len(full_df.columns),
                "columns": full_df.columns.tolist(),
            }
        except Exception:
            info[name] = {"rows": "?", "cols": "?", "columns": []}
    return info


def prompt_sheet_selection(file_path: str) -> list:
    """
    Shows an interactive sheet picker in the terminal.
    Returns a list of selected sheet names.
    """
    console.print("\n[bold cyan]📋 Excel Sheet Selection[/bold cyan]")

    try:
        sheet_info = get_sheet_info(file_path)
    except Exception as e:
        console.print(f"[red]❌ Could not read sheets: {e}[/red]")
        return []

    sheet_names = list(sheet_info.keys())

    # Show sheet table
    table = Table(title="Available Sheets", border_style="blue", show_lines=True)
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Sheet", style="bold white")
    table.add_column("Rows", justify="right")
    table.add_column("Columns", justify="right")
    table.add_column("Sample columns", style="dim")

    for i, name in enumerate(sheet_names, 1):
        info = sheet_info[name]
        sample = ", ".join(str(c) for c in info["columns"][:5])
        if len(info["columns"]) > 5:
            sample += f" … (+{len(info['columns']) - 5} more)"
        table.add_row(
            str(i),
            name,
            str(info["rows"]),
            str(info["cols"]),
            sample,
        )

    console.print(table)

    # Selection prompt
    console.print(
        "\n[dim]Options:[/dim]\n"
        "  [yellow]•[/yellow] Enter sheet number(s) separated by commas: [bold]1[/bold] or [bold]1,2[/bold]\n"
        "  [yellow]•[/yellow] Type [bold]all[/bold] to load all sheets\n"
    )

    while True:
        raw = Prompt.ask("[cyan]👉 Select sheet(s)[/cyan]").strip().lower()

        if raw == "all":
            selected = sheet_names
            break

        # Parse comma-separated numbers
        parts = [p.strip() for p in raw.split(",")]
        try:
            indices = [int(p) for p in parts if p]
            selected = []
            valid = True
            for idx in indices:
                if 1 <= idx <= len(sheet_names):
                    name = sheet_names[idx - 1]
                    if name not in selected:
                        selected.append(name)
                else:
                    console.print(
                        f"[red]❌ '{idx}' is out of range (1–{len(sheet_names)})[/red]"
                    )
                    valid = False
                    break
            if valid and selected:
                break
        except ValueError:
            console.print("[red]❌ Please enter numbers or 'all'[/red]")

    # Confirm selection
    if len(selected) == 1:
        console.print(f"\n[green]✅ Loading sheet:[/green] [bold]{selected[0]}[/bold]")
    else:
        console.print(
            f"\n[green]✅ Loading {len(selected)} sheets:[/green] [bold]{', '.join(selected)}[/bold]"
        )
        console.print(
            "[yellow]ℹ️  Sheets will be merged with a '_sheet' column added "
            "so you can filter per sheet in queries.[/yellow]"
        )

    return selected
