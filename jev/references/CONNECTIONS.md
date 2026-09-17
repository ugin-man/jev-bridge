# Connections

All routes share `scripts/jev.py` and the HTTP client under `_vendor/`. The latter
is this project's maintained client, not vendored TypeSafe SDK code.

## Agent Skill + local execution

Run `python -I <skill>/scripts/jev_bridge.py status`. Use the actual interpreter
and absolute skill path. `validate --file request.json` checks locally;
`run --file request.json --execute --out new-result.json` executes the authorized
request. The old `scripts/jev.py` entry remains compatible. `--file -` reads UTF-8
JSON from stdin, so non-Python programs can pipe requests without a temp file.

Saved definitions: `run --recipe recipe.json --data data.json --execute --out result.json`.
The host prepares these files. The user does not need to understand their syntax.

## MCP

Install the repository into a virtual environment with `python -m pip install '.[mcp]'`.
Configure a stdio server with that environment's absolute `jev-bridge` executable
and the argument `mcp`. With an absolute Python path instead, use arguments
`-I`, the absolute `jev/scripts/jev_bridge.py` path, and `mcp`.
Use the host's own MCP settings; do not replace its configuration wholesale.

Tools: `jev_status`, `jev_validate`, `jev_evaluate`, `jev_batch`. Evaluation defaults
to `execute=false`; the host sets it true after scoped authorization. The official
MCP Python SDK manages lifecycle, validation, cancellation and stdio transport.
In-flight HTTP calls cannot necessarily be cancelled after reaching TypeSafe.
No public HTTP listener or authentication proxy is silently created.

Codex, Claude Code, Claude Desktop, Gemini CLI and other stdio MCP hosts can use
this protocol route when their environment supports local servers. App-specific
visibility and approval behavior still require actual host testing. A remote-only
chat service cannot execute a local stdio process without a host-provided bridge.

## Python or other applications

After `pip install .`, `from jev_bridge import Bridge` exposes `status()` and
`evaluate(request, execute=False)`. Execution must be explicitly enabled.
Non-Python apps can use MCP or the JSON CLI. No extra generative-model API is
required: the host prepares the questions using its existing model.

## Storage and keys

`JEV_BRIDGE_HOME` selects storage explicitly. Fresh defaults are local application
data on Windows, `~/Library/Application Support/jev-bridge` on macOS, and
`$XDG_STATE_HOME/jev-bridge` (fallback `~/.local/state/jev-bridge`) on Linux.
No Codex installation is required. Explicit legacy `JEV_SKILL_HOME`,
`JEV_WORKER_HOME`, `JEV_HELPER_HOME` and `CODEX_HOME` still work; an existing old
store can be reused without copying its key or resetting its ledger.

`TYPESAFE_API_KEY` works in the process environment on all supported operating systems.
`set-key` uses Windows DPAPI or, with the `[keyring]` extra, a native macOS Keychain,
Linux Secret Service/KWallet or Windows credential vault. A headless machine without
a usable vault should use its secret manager/environment. Plaintext fallback is refused.
Saved credentials take precedence over environment values; broken storage is reported,
not silently replaced by another account. Key-entry UI/OS vaults require local testing.

Local `settings.json` controls limits. `max_batch_items` is no longer capped at 20
by the loader. Daily caps and `max_batch_seconds` may be set to 0 to disable those
local limits; do so only after reviewing the scope. Limits are not monetary ceilings.
`trust_environment=true` opts into configured HTTP proxies; verified TLS remains on.
