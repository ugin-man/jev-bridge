# Agent handoff

Read README.md, AGENTS.md, jev/SKILL.md and relevant connection notes. Determine the
actual host capabilities and existing installation before choosing a route. Do not
ask the user to choose syntax, presentation language, API types, or technical steps
that can be inferred. Use the available model; no new generative API key is needed.

1. Inspect the repository/version and Python interpreter. Preserve existing models,
   integrations, authentication and unrelated files.
2. Run the offline suite. Select Agent Skill, stdio MCP, CLI or Python integration
   based on actual capabilities. For skills, use the installer target/root appropriate
   to the host; compare an existing copy and use explicit backup update if needed.
3. MCP uses the official SDK extra and an absolute executable path. Add only the
   requested registration via the host's supported mechanism. Verify actual tool
   discovery and jev_status rather than treating config text as connection success.
4. Reuse the intended credential store and usage ledger. Guide missing key entry
   through a local non-echoing terminal or the user's secret manager, never chat.
5. Validate a request offline. After scoped authorization for TypeSafe transfer and
   potential credits, run one small real request. An offline mock success is not a
   real Jev response; do not report it as one.
6. Report host, route, commit, actual checks, outstanding failures and whether any
   real requests were sent. Do not remove quotas or change accounts to evade an error.

No application-binary patches, model-name impersonation or silent credential copies
are needed. The bridge does not add Jev to any vendor's model picker.
