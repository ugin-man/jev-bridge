# Reusable user requests

Use the official TypeSafe skill and its live cookbook links to design a workflow:
[upstream dependency](UPSTREAM.md). We do not maintain a competing cookbook here.

The bridge's local reuse format is `recipe.json` containing `questions` and an
optional `name`, with `data.json` containing exactly `state` or `items`.
Run via `run --recipe recipe.json --data data.json --execute --out new-result.json`.
The host prepares these files. Keep private data/results outside version control;
keep credentials out of recipes. Reuse a question only while its meaning and
relevant evidence are unchanged.

`assets/` contains small synthetic smoke/compatibility fixtures, not official
prompts, recommended universal rubrics or a list of supported domains. They remain
useful for checking our execution layer without duplicating upstream teaching.
