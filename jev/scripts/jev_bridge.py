"""Host-neutral Jev entry point and importable API. Natural language stays with the host."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

# Source-tree execution also works in Python isolated mode.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import jev as cli

__version__ = "2.0.0"
JevError = cli.JevError


class Bridge:
    """One runtime for CLI, MCP and Python integrations; no host-model dependency."""
    def __init__(self, home: Path | None = None, *, client=None):
        chosen, source = (Path(home), "explicit") if home is not None else cli.selected_home()
        self.client = client if client is not None else cli.JevClient(chosen)
        self.source = source

    def status(self) -> dict:
        return {**self.client.status(), "bridge_version": __version__,
                "storage_home": str(self.client.home), "home_source": self.source}

    def evaluate(self, request: dict[str, Any], *, execute: bool = False) -> dict:
        if type(execute) is not bool:
            raise JevError("invalid_argument", "execute must be boolean")
        if not isinstance(request, dict) or set(request) not in (
                {"state", "questions"}, {"items", "questions"}):
            raise JevError("invalid_request", "Supply state/questions or items/questions.")
        return cli.execute_request(self.client, request, execute=execute)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "mcp":
        from jev_mcp import main as serve
        return serve(args[1:])
    if args == ["--version"]:
        print(__version__)
        return 0
    return cli.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
