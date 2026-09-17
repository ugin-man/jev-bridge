# Development contract

Jev Bridge is an unofficial **execution companion** to official TypeSafe components,
not a replacement skill or SDK. Read the installed official `typesafe-ai` skill,
or its canonical GitHub file, before designing provider behavior. Follow its live
docs workflow. See jev/references/UPSTREAM.md for one-method installation options.

Do not vendor, rewrite, translate or periodically copy the official skill/cookbooks
into this repo. Keep jev/SKILL.md limited to bridge setup/execution. Provider HTTP
and response parsing use the official `typesafe-sdk` dependency. Our retained local
compatibility checks are guards for this bridge version, not universal provider
limitations. Update SDK bounds only with real-SDK regression tests.

Own the useful differences: common MCP/CLI/Python execution, credential storage,
local resource/usage accounting, bounded batches and saved-result handling. Use the
official MCP SDK. Keep existing entry points, permissions, stores and user work.
Do not impose a conversation language, app, domain or a second generative model.

No secrets, personal contact details, live input or results in Git. Test data must
be synthetic; never use paid API calls to run tests. No blind paid retries,
automatic purchases, quota bypass, account switch or weakened host approvals.

Run `python -I -m unittest discover -s tests -v` before and after edits. CI installs
the TypeSafe and MCP SDKs and requires actual protocol/SDK tests without live API
traffic. Check packaging outside the source tree. Report skips and real model/app
verification separately. Inspect remote state and preserve unrelated changes;
use a topic branch and reviewable PR, no force push. Verify remote delivery.
