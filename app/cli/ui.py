from rich.console import Console
from rich.panel import Panel

console = Console()


def show_header():
    console.print(
        Panel.fit(
            "[bold #2dd9fe] 🧠 QueryMind CLI [/bold #2dd9fe]\n"
            "[#74ee15 ] Your AI Data Analyst [/#74ee15]",
            border_style="blue",
        )
    )


def show_message(role, text):
    if role == "user":
        console.print(f"[bold blue]>> {text}[/bold blue]")
    else:
        console.print(f"[bold green]>>💡 {text}[/bold green]")
