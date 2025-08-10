from rich.console import Console
from rich.traceback import install

console = Console()
install(show_locals=False, suppress=[str])

def info(msg: str):
    console.log(f"[bold green]INFO[/]: {msg}")

def warn(msg: str):
    console.log(f"[bold yellow]WARN[/]: {msg}")

def error(msg: str):
    console.log(f"[bold red]ERROR[/]: {msg}")
