# Bridge envelope, not a second TypeSafe reference

Use the official skill and current TypeSafe docs for questions, criteria and model
semantics: see [UPSTREAM.md](UPSTREAM.md). We intentionally do not mirror that guide.

The bridge accepts exactly one of these envelopes:

- `state` and `questions`: one record and the provider's question definitions.
- `items` and `questions`: independent `{id, state}` records sharing definitions.

The host creates the inputs. `model` and resource settings belong to local
configuration, not this untrusted request envelope. Individual questions are passed
to the official SDK; this version retains compatibility checks for the bridge's
existing question/answer interface. Unsupported new SDK fields require an adapter
update, not an invented claim that TypeSafe can never support them.

CLI: `validate --file request.json`, `run --file request.json --execute --out result.json`.
`--file -` reads JSON from stdin. Python: `Bridge.evaluate(request, execute=False)`.
MCP: `jev_status`, `jev_validate`, `jev_evaluate`, `jev_batch`.

Validation is local, has no answers and does not need a key. Real execution adds
provider results and local execution metadata. Unreported token counts remain null,
not fabricated zeros. Batch results identify completed, failed and unstarted IDs.
These are sequential per-record SDK calls, not a provider batch discount or automatic
parallel execution. Resource counters describe local submitted-payload budgets,
not an account balance or currency-denominated spending limit.
