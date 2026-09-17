# Use upstream; do not fork it

## Ownership

- **TypeSafe skill, docs and cookbooks:** upstream owns reasoning/design guidance.
- **TypeSafe Python SDK:** upstream owns provider HTTP requests and typed responses.
- **Jev Bridge:** local MCP/CLI/Python connections, credential storage, input/resource
  guards, local usage ledgers, bounded batches and saved-result handling.

The official skill is a separately installed/read upstream dependency. Its contents
are not shipped, translated, patched or synced into this repository. `jev/SKILL.md`
is only our execution companion. We do not claim a formal cross-skill dependency
feature in every host; the agent must actually load the official skill itself.

## Install the official skill once, using one method

First check the host's installed skills/plugins; reuse `typesafe-ai` when available.
For **Claude Code**, the official method is:

    claude plugin marketplace add typesafe-ai/skills
    claude plugin install typesafe@typesafe-ai

For **other supported agents**, use:

    npx skills add typesafe-ai/skills --skill typesafe-ai

Select the actual agent when prompted. Do not use both methods for the same host.
Use the upstream installer to manage upstream updates; do not have our installer
write a lookalike copy. These commands can install external software: use the host's
normal permissions. This bridge's Python installer manages only `jev/`.

For hosts without skill installation, read the official file directly:
https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md
https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md

If access fails and no installed copy is available, report that limitation; do not
invent official guidance. Already prepared bridge requests still work without a
skill installed. Read skills at task setup or when relevant guidance changes, not
on every item/API call. Do not alter prompt content to match a stale local summary.

## SDK installation and updates

`python -m pip install .` installs the bridge and its official `typesafe-sdk`
dependency. MCP and native-vault support remain optional extras. The supported SDK
range is declared in `pyproject.toml`; 2.1 targets the inspected 0.6 API. We do not
vendor the SDK or fetch new code at runtime. Upgrade the dependency deliberately,
read upstream changes, then run the real-SDK tests before release.

The adapter explicitly keeps our endpoint/model, verified TLS, redirect policy,
proxy opt-in and `RetryPolicy(max_retries=0)`. These are execution settings, not
replacement provider documentation. A missing SDK is reported before reserving
request budget; offline validation continues to work without it. Provider response
parsing belongs to the SDK, followed by bridge compatibility/integrity checks.

SDK logging is off unless configured by the host; SDK debug logging can contain
request/response bodies. Do not enable it for private workloads by default.

## Canonical references

- https://github.com/typesafe-ai/skills (official installation and skill)
- https://docs.typesafe.ai/llms.txt (live documentation index)
- https://github.com/typesafe-ai/typesafe-sdk-python (official Python implementation)
- https://docs.typesafe.ai/sdk/python/ (SDK reference)

This project is an unofficial companion. Using official dependencies is not an
endorsement or a claim of superior model accuracy or end-to-end performance.
