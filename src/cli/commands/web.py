"""Web command - start the local browser UI."""

import click


@click.command()
@click.option("--port", "-p", type=int, default=8765, help="Port to listen on. Default: 8765")
@click.option("--host", default="127.0.0.1", help="Bind address. Keep it on loopback.")
@click.option("--workers", "-w", type=int, default=None, help="PoB worker processes per run. Default: CPU count.")
@click.option("--no-browser", is_flag=True, default=False, help="Don't open a browser window.")
def web(port: int, host: str, workers, no_browser: bool):
    """
    Start the local web UI.

    Opens a page where you import a character or paste a Path of Building
    code, choose what to improve, watch the optimizer work, and copy the
    new build code back into Path of Building.
    """
    try:
        from src.web.app import run
    except ImportError as e:
        raise click.ClickException(
            f"The web UI needs fastapi and uvicorn ({e}). Install with: pip install fastapi uvicorn"
        )
    run(host=host, port=port, workers=workers, open_browser=not no_browser)
