# TypeSafe contract

Verified against the live TypeSafe API, Choice, Score and Advanced Structure pages
on 2026-09-17. Those pages, not this snapshot, are the upstream authority.

POST https://api.typesafe.ai/v1/systemone with a server-side Bearer API key.
Body: `state`, `model` (default `jev-latest`), and `questions` keyed by caller IDs.
This bridge selects the model through local settings, not untrusted input. The host
supplies `{state, questions}` or `{items: [{id, state}, ...], questions}`.

Each question contains `type`, `instructions`, and applicable `criteria`:
- Choice: options mapped to descriptions; documented maximum 255 options.
- Noul: a yes probability; optional `true`/`false` descriptions.
- Score: 2–10 ordered level descriptions, each independently meaningful.

Instructions and descriptions can be strings, objects, arrays, or null, including
structured Noul descriptions. IDs are routing keys, not prompts. Preserve Unicode
input; this bridge does not impose a language field or transform text automatically.

Response `answers` uses the same IDs. Noul has `noul` (0–1). Choice has `choice`,
`probabilities`, `confidence`. Score has `score`, `legend`, `probabilities`,
`confidence`; score is the probability-weighted level index. `usage` reports
`input_tokens` and `output_tokens`. No free-form reasoning field is supplied.

The bridge validates responses and returns raw decisions plus local execution
metadata. Probabilities/confidence are not measured accuracy. Offline validation
returns no answers. Repeated requests may incur repeated charges.

Requests on different records are separate HTTP requests, not a discounted provider
batch endpoint. Limits in settings.json protect local resources and can be adjusted;
they must not be presented as provider limits. Score 10 and Choice 255 are different:
they are documented upstream shape limits, so they remain enforced.

Sources:
- https://docs.typesafe.ai/api
- https://docs.typesafe.ai/primitives/choice
- https://docs.typesafe.ai/primitives/score
- https://docs.typesafe.ai/primitives/advanced
- https://docs.typesafe.ai/agent-skill
