"""Optional MCP adapter using the official Python SDK, not a custom protocol."""
from __future__ import annotations
import argparse
import json
import sys
from typing import Any
from jev_bridge import Bridge, JevError

INSTRUCTIONS = """Execution companion to the official TypeSafe skill. Use the installed
`typesafe-ai` skill for judgment design and provider guidance, or read its official
file at https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md.
This server adds connections, local budgets and result handling, not a replacement
skill. Prepare the user's inputs yourself. execute=false validates without network;
execute=true sends the authorized material to TypeSafe and may consume credits.
Preserve host approvals. Return actual results; do not call a mock a Jev judgment
or turn a decision into permission for another action. Reuse upstream guidance
already loaded in this task, not a network lookup per item.
"""


def create_server(bridge: Bridge | None = None):
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    runtime = bridge or Bridge()
    server = FastMCP("jev-bridge", instructions=INSTRUCTIONS)

    def invoke(request: dict, execute: bool) -> dict:
        try:
            return runtime.evaluate(request, execute=execute)
        except JevError as exc:
            raise ValueError(json.dumps(exc.as_dict(), ensure_ascii=False)) from None
        except (OSError, ValueError, TypeError):
            raise ValueError("Local operation failed; do not retry a paid request blindly.") from None

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def jev_status() -> dict:
        """Check local configuration and usage. Does not authenticate or call TypeSafe."""
        try:
            return runtime.status()
        except JevError as exc:
            raise ValueError(json.dumps(exc.as_dict())) from None

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def jev_validate(request: dict[str, Any]) -> dict:
        """Validate state/questions or items/questions offline. No API key required."""
        return invoke(request, False)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                            idempotentHint=False, openWorldHint=True))
    def jev_evaluate(state: str | dict[str, Any] | list[Any],
                     questions: dict[str, Any], execute: bool = False) -> dict:
        """Evaluate evidence with typed questions. Set execute=true only for authorized TypeSafe calls."""
        return invoke({"state": state, "questions": questions}, execute)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                            idempotentHint=False, openWorldHint=True))
    def jev_batch(items: list[dict[str, Any]], questions: dict[str, Any],
                  execute: bool = False) -> dict:
        """Evaluate independent {id,state} records. One API request per record; stops on first failure."""
        return invoke({"items": items, "questions": questions}, execute)

    return server


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    try:
        server = create_server()
    except ImportError:
        print('MCP support requires installing this project with the [mcp] extra.', file=sys.stderr)
        return 2
    except JevError as exc:
        print(json.dumps(exc.as_dict()), file=sys.stderr)
        return 2
    server.run(transport="stdio")
    return 0
