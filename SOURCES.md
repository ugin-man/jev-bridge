# Upstream-first design record — 2.1

Inspected the actual official skill and Python SDK public implementation. The
uploaded official SKILL.md delegates concepts to live docs; we now follow it rather
than maintaining our own summary of question design.

- Official skill and installation: https://github.com/typesafe-ai/skills
  Upstream owns this file. It is installed/read directly and is NOT vendored here.
- Official SDK: https://github.com/typesafe-ai/typesafe-sdk-python
  Inspected `pyproject.toml` (0.6.0), public exports, synchronous client,
  `RetryPolicy`, endpoint construction, typed responses and `raw_http_response`.
  The bridge now calls `TypeSafeClient.system_one` with explicit zero retries.
- Upstream typed responses allow unreported token counts. Bridge results preserve
  null and do not pretend the local token ledger is complete in that case.
- Official MCP SDK: https://github.com/modelcontextprotocol/python-sdk
  Continues to own stdio lifecycle/protocol; it is distinct from the TypeSafe SDK.
- Earlier v2 design reference: https://github.com/browser-use/jev-ultrafast
  Informed action-selection composition, not bundled browser automation.

The former handwritten HTTP path was removed. Bridge-local validation remains a
versioned compatibility/integrity guard, not a competing provider SDK or universal
capability taxonomy. Synthetic assets test bridge behavior, not recommended general
rubrics. No upstream skill/SDK implementation code is copied into this project.

Web documentation retrieval failed in the editing environment for this revision;
SDK details were verified directly through the official GitHub source instead.
Real provider traffic remains untested here; SDK tests use its real code with an
injected local HTTP transport. Existing project licensing remains unchanged.
