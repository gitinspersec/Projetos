"""
©AngelaMos | 2026
__main__.py

Allows the package to be run with `python -m password_manager`

When Python sees `python -m <package>`, it looks for this file and
runs it. Same effect as the `pv` script entry point declared in
pyproject.toml — useful when the script is not on PATH yet
"""

# Local: the Typer application object — this is what actually parses
# the CLI args and dispatches to subcommands like `list` or `add`.
from password_manager.main import app

if __name__ == "__main__":
    app()
