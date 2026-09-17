# jev-bridge

**Ask your agent to use Jev. The agent handles the interface; you describe the work.**

An unofficial, host-neutral bridge to TypeSafe's Jev. Agent Skill, stdio MCP, JSON
CLI and Python API share the same execution runtime. There is no language selector,
required Codex account, product-matching-only workflow, or second generative model.

[日本語ガイド](README_JA.md) · [Connections](jev/references/CONNECTIONS.md) ·
[Research and design](SOURCES.md) · [Verification](TEST_REPORT.md)

## Start with your existing agent

Open this repository in an agent that can read files and run local tools, then ask:

> Read HANDOFF.md and set up the Jev bridge for this environment. Keep my existing
> models, authentication and other integrations. Handle the technical steps yourself;
> only ask me for information or authorization that is genuinely missing.

The agent selects the appropriate route. The user does not have to author JSON,
pick question types, or repeatedly specify presentation details.

| Route | When to use it |
| --- | --- |
| Agent Skill | A host that can load SKILL.md and execute local tools |
| MCP | A host supporting local stdio MCP, including non-skill hosts |
| CLI | Shell workflows and programs in any language that can exchange JSON |
| Python API | Import the shared bridge in your application |

A hosted chat interface without tool execution or a local MCP bridge cannot run a
local program merely by reading this README. Support is capability-based, not a
claim that every app/version has been tested.

## Installation

Python 3.11+ is required. The CLI has no third-party runtime dependencies.
In a virtual environment, `python -m pip install .` installs the `jev-bridge` command.
Use `python -m pip install '.[mcp]'` for the official MCP Python SDK adapter;
`python -m pip install '.[keyring]'` adds native OS credential-vault support.
These install from this source checkout; no PyPI publication is claimed.

For an Agent Skill, run `python install_skill.py`. It installs `jev/` into the shared
user `.agents/skills` directory. `--target claude` uses `.claude/skills`;
`--scope project` selects project-local installation; `--skills-root PATH` supports
other hosts. Host configuration and credentials are not rewritten.
`--update` explicitly replaces a different skill while keeping a backup outside the
active skills directory. Repeating an identical installation is a no-op.

Windows launchers remain available. The Python commands work across Windows,
macOS and Linux; no `.cmd` execution is required outside Windows.

## Use the runtime

`jev-bridge status` checks local state without an API call.
`jev-bridge validate --file request.json` validates offline.
`jev-bridge run --file request.json --execute --out result.json` executes an
authorized request. `--file -` reads from stdin. The agent writes the input.

For MCP, register an absolute `jev-bridge` executable with the single argument `mcp`.
The tools are `jev_status`, `jev_validate`, `jev_evaluate`, and `jev_batch`.
See [connection details](jev/references/CONNECTIONS.md) for source-tree commands,
credentials, existing stores, resource settings and host capability requirements.

For Python integrations, `from jev_bridge import Bridge` exposes `status()` and
`evaluate(request, execute=False)`. The same methods are used by MCP. Execution is
explicitly enabled only for the scope the user authorized.

## What changed in 2.0

Removed presentation-language requirements and the Codex-centered onboarding/storage
default. Added generic/Claude/project/custom skill installation, backup updates,
a packaged CLI/Python interface, and official-SDK MCP transport. Brought accepted
question descriptions in line with TypeSafe's structured/null EntryType guidance.
Choice supports the documented 255 options rather than our previous 100-option cap.
The settings loader no longer hard-caps batches at 20 or timeouts at 30 seconds.

Default resource budgets remain conservative and visible in `status`; configure them
for the authorized workload. A default is not a permanent service limit. Daily caps
and batch deadlines may explicitly be disabled with zero. No automatic retry, account
switch, top-up, blanket tool permission or plaintext-secret fallback was added.

## Scope and verification

The TypeSafe [official skill](https://github.com/typesafe-ai/skills) is the primary
reference for designing integrations. This project adds reusable execution and
connection routes; it does not replace Jev with a general text-generation model.
Selection, extraction from candidates, ranking, routing and action selection can be
combined by the host. Browser control itself is not bundled into this release.

All tests use synthetic data or offline protocol traffic. Real Jev accuracy,
account access and each desktop app's end-to-end behavior require separate testing.
See TEST_REPORT.md and the Actions run for the exact commit. Local skill copies do
not update merely because the GitHub repository changed.

Never commit keys, local settings, private input, result files or credential blobs.
TypeSafe charges are separate from the host model's usage. Local counters are not
an account balance or a currency-denominated spending limit.

Not an official OpenAI, Anthropic, Google or TypeSafe product.
