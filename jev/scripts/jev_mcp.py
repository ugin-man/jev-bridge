"""Optional MCP adapter using the official Python SDK, not a custom protocol."""
from __future__ import annotations
import argparse
import json
import sys
from typing import Any
from jev_bridge import Bridge, JevError

INSTRUCTIONS = """Use Jev for typed judgments that serve the user's task. You prepare
questions and interpret actual results; the user need not write code or choose
API types. Questions map IDs to {type, instructions, criteria}. Types: choice
(criteria maps option names to descriptions), noul (yes probability; optional
true/false descriptions), score (2-10 ordered descriptive levels). IDs are not
seen by Jev: put the full question in instructions. Independent questions over
the same evidence can share a request. Infer presentation from conversation.
execute=false validates without network; execute=true sends evidence to TypeSafe
and may consume credits. Honor scoped consent and host approvals. Never call a
mock or offline result a Jev judgment, invent explanations, or treat confidence
as measured accuracy. Tools return decisions; they do not execute chosen actions.
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
