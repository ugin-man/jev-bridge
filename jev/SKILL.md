---
name: jev
description: Execute TypeSafe judgments through Jev Bridge's MCP, CLI or Python interface. Companion to the official typesafe-ai skill, not a replacement. Use for bridge setup, credentials, validation, bounded execution and saved results when a task calls for Jev.
---

# Jev Bridge execution companion

Use the **official `typesafe-ai` skill** for TypeSafe capabilities, question design,
API/SDK guidance and cookbooks. Load its installed version; if unavailable, read
https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md
(raw: https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md).
Installation and update choices are in [UPSTREAM.md](references/UPSTREAM.md).
Do not copy, rewrite or maintain a second TypeSafe teaching skill in this project.
Use upstream guidance already loaded in this task; do not download it per record.

This companion adds only the execution connection:

1. Use an existing Jev MCP connection, or `scripts/jev_bridge.py`, or the `Bridge`
   Python API. Read [CONNECTIONS.md](references/CONNECTIONS.md) for this environment.
2. Prepare the actual materials and questions using the official skill. The host
   handles technical input and presentation; the user describes the work.
3. Check local status, then validate offline. Missing credentials belong in a local
   non-echoing prompt or secret manager, never chat. The official SDK is required
   for real requests; setup must not silently install packages or call paid APIs.
4. Execute only the authorized scope: CLI `run --execute`, MCP `execute=true`.
   Preserve existing approvals, credentials, ledgers and resource settings.
5. Return actual results and distinguish failures and unstarted records. Never
   present a dry run or host prediction as a Jev answer. Keep saved results in the
   user's working area; do not overwrite or blindly repeat a possibly billed call.

[API.md](references/API.md) documents only the bridge envelope. Provider semantics
come from upstream, not from this companion. Tools return judgments, not authority
to execute selected actions or expose private data.
