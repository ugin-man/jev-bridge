# jev-bridge

**Official TypeSafe guidance and SDK, with a reusable execution layer on top.**

Describe the work to your existing agent. The official `typesafe-ai` skill teaches
it how to use TypeSafe. Jev Bridge adds ready-made MCP, CLI and Python connections,
credential storage, local usage controls, bounded batches and saved-result handling.
It does not maintain a rewritten official skill or an alternative TypeSafe SDK.

[日本語](README_JA.md) · [Upstream setup](jev/references/UPSTREAM.md) ·
[Connections](jev/references/CONNECTIONS.md) · [Verification](TEST_REPORT.md)

## Start with your agent

Open this checkout in an agent with local tool execution and ask:

> Read HANDOFF.md. Use the official TypeSafe skill and set up Jev Bridge for this
> environment. Keep my existing models, integrations and credentials. Handle the
> technical steps; ask only for genuinely missing information or permission.

The handoff reuses an installed official skill, or chooses **one** upstream
installation method. Our `jev` companion only explains bridge execution; it does
not install, overwrite or pretend to be `typesafe-ai`. Hosts without skill support
can read the official file directly and use MCP/CLI. Already structured requests
do not require installing a skill.

## What comes from where

| Owner | Responsibility |
| --- | --- |
| Official TypeSafe skill/docs | Capabilities, judgment design, API concepts and cookbooks |
| Official TypeSafe Python SDK | Provider requests and typed response parsing |
| Jev Bridge | Host connections, local credentials, budgets, batch/result handling |

There is no mandatory language selector, Codex account or fixed task domain.
The benefit is prepared execution tooling, not greater Jev intelligence. A remote
chat with neither local execution nor an MCP bridge cannot run local programs.

## Install

Python 3.11+ is required. In a suitable environment, `python -m pip install .`
installs the CLI and the declared official `typesafe-sdk` dependency. Use
`python -m pip install '.[mcp,keyring]'` to include the official MCP SDK and native
credential-vault support. This is installation from source, not a PyPI release claim.

For the optional execution companion, `python install_skill.py` copies `jev/` to
`.agents/skills`; `--target claude`, `--scope project`, and `--skills-root PATH`
provide other placements. `--update` keeps a backup. **This installs only our
companion**; install/update the official skill through upstream's own mechanism.
See [one-method official setup](jev/references/UPSTREAM.md).

## Interfaces

- MCP: absolute `jev-bridge` executable with argument `mcp`.
- CLI: `jev-bridge status`, `validate --file request.json`, and
  `run --file request.json --execute --out new-result.json`; stdin is `--file -`.
- Python: `from jev_bridge import Bridge`, then `evaluate(request, execute=False)`.
- Skill: the small `jev` execution companion alongside official `typesafe-ai`.

The agent builds requests; users do not edit JSON. Offline validation works without
a key or SDK. Real calls use the official SDK and are never silently redirected to
a legacy client. A missing SDK is reported before reserving paid-call budget.

## Execution policy and compatibility

Keep the existing storage/credential selection, configurable resource budgets,
explicit execution, no-blind-retry behavior and result protection. The SDK adapter
explicitly pins the provider endpoint/model, verified TLS, redirect refusal, proxy
opt-in and zero automatic retries. Incoming response streams are bounded; decoded
content is checked too. SDK/debug logs may contain payloads if the host enables them.
No log settings are enabled by the bridge.

Batches remain sequential separate calls. Counters are local resource accounting,
not a monetary cap. Unknown token usage stays null. Local bridge compatibility
checks are versioned independently of TypeSafe's capabilities. See
[connection notes](jev/references/CONNECTIONS.md) and [source record](SOURCES.md).

All tests use synthetic responses or local protocol traffic. SDK integration tests
are not live Jev access/accuracy tests, nor proof of every desktop host's behavior.
GitHub changes do not automatically update installed copies. Never commit private
keys, source documents, local settings or results.

Unofficial companion; not an official TypeSafe, OpenAI, Anthropic or Google product.
