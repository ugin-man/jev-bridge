# Agent handoff: official TypeSafe + Jev Bridge

Read AGENTS.md and the actual environment. Preserve existing models, integrations,
authentication and unrelated files. The user describes the work; handle inferable
technical details yourself.

1. **Load the official TypeSafe skill, not our rewrite.** Reuse an installed
   `typesafe-ai` skill/plugin. If missing, use exactly one official installation
   method appropriate to the host in `jev/references/UPSTREAM.md`, or read the
   official file directly when installation is unsupported. Do not copy or patch it
   into this repo. State an unavailable source; do not invent its contents.
2. **Set up our execution layer.** Use Skill companion, stdio MCP, CLI or Python
   according to actual host capabilities. Install this checkout into an appropriate
   Python 3.11+ environment; it declares the official TypeSafe SDK dependency.
   Add optional MCP/keyring extras as needed. Preserve normal install permissions.
3. **Keep ownership separate.** Our installer only manages the `jev` companion,
   never the official `typesafe-ai` skill. Update an existing companion with its
   backup option. Both may coexist; do not run two official installation methods.
4. **Verify the real connection path.** Check local status and offline validation.
   For MCP, use an absolute executable and verify actual discovery/status, not just
   a config entry. The official TypeSafe SDK readiness is distinct from API access.
5. **Reuse the intended secret store and ledger.** Missing keys go through local
   hidden input or the user's secret manager, never chat. After scoped permission
   for data transfer and possible TypeSafe credits, send one small real request.
6. Report commit, host, route, exact tests and any real requests separately. Tests
   must not spend credits. Do not call a mock a Jev judgment, switch accounts to
   evade errors, remove resource controls, or overwrite unrelated configuration.

Design comes from the official skill. Execution convenience comes from this bridge.
No model-picker changes or new generative-model subscription are required.
