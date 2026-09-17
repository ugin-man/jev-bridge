# 2.1.0 — official foundation, independent execution layer

- Replaced duplicated TypeSafe teaching with a short bridge execution companion.
- Added one-method upstream skill setup; never vendor or overwrite the official skill.
- Default provider traffic uses official typesafe-sdk; removed handwritten urllib HTTP.
- Preserved MCP/CLI/Python, stores, budgets, validation, batches and result protection.
- Disabled SDK retries explicitly; retained endpoint/TLS/redirect/proxy policy.
- Missing SDK fails before budget reservation; unreported usage stays null.
- Added real-SDK mocked-HTTP regression tests and upstream-ownership checks.

# Changelog

## 2.0.0 — 2026-09-17

Host-neutral rework based on TypeSafe's official skill, API guidance, Agent Skills
and official MCP SDK. Removes language prescriptions, adds MCP/CLI/Python entry
points, neutral fresh-install storage, native keyring option, cross-host installer
and explicit backup updates. Expands Choice to 255 and structured/null descriptions;
removes arbitrary configuration ceilings. Preserves scoped execution, response
validation, existing entry points, explicit legacy stores and no-blind-retry behavior.

## 1.0.1

Fixed explicit CODEX_HOME discovery on Windows without an OS profile. Added three
regression tests. No real API calls.

## 1.0.0

Initial natural-language skill and bounded local HTTP client.
