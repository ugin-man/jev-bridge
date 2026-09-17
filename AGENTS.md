# Development contract

Build a host-neutral way to delegate judgments to Jev. The user describes work; the
host agent handles preparation and execution. Do not hardcode conversational language,
require Codex, narrow the product to one example, or demand information inferable from
context. Keep generative work with the host and deterministic work in code.

Research before inventing constraints. TypeSafe's official skill, API, SDK types and
cookbooks are primary references. Read SOURCES.md and current relevant docs. Distinguish
provider limits from configurable local budgets and unsupported host capabilities.

Maintain one runtime for Skill, MCP, CLI and Python. Use the official MCP SDK instead
of creating a private protocol. Avoid speculative framework rewrites and untested
host support claims. Preserve old entry points and explicit legacy stores when feasible.

No secrets, personal contact information, live input, logs or results in Git. Tests
use synthetic fixtures only. No real API calls, automatic purchases, quota bypasses,
account switching or approval weakening during development. Explain data transfer and
fees within the user's actual scope; do not repeatedly ask for already granted consent.

Before and after changes, run `python -I -m unittest discover -s tests -v`.
CI must install the MCP extra and require real SDK protocol tests. Test Windows, Linux
and macOS; report skips and actual API/host verification separately. Tests of Unicode
round trips are not language-understanding benchmarks. Check packaging in a clean
installation, not only source imports.

Read current Git state before writing; preserve unrelated changes. Prefer a topic
branch and reviewable PR. Never force-push. Verify remote refs and Actions for the
exact commit before claiming delivery. A GitHub update does not update local copies.
