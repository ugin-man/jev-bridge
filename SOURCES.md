# Research and design record — 2026-09-17

Inspected primary sources, not a list of unverified search matches:

| Source | What was actually adopted |
| --- | --- |
| https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md | Start from desired behavior, preserve the host stack, research live docs, compose judgments; examples are not capability ceilings. The bridge skill was rewritten, not copied. |
| https://docs.typesafe.ai/agent-skill | Official installation already targets Claude Code, Codex and other agents. A Codex-only design was unnecessary. |
| https://github.com/typesafe-ai/typesafe-sdk-python | Checked the official client approach and typed-questions interface. This release retains our tested HTTP runtime; it does not claim to embed the SDK. |
| https://github.com/browser-use/jev-ultrafast | Reviewed dynamic candidate/action selection and questions.py. Learned to separate selecting supported actions from text generation. Browser code is not bundled or claimed implemented. |
| https://github.com/modelcontextprotocol/python-sdk | Use the official FastMCP server/client SDK as an optional adapter. No hand-rolled lifecycle or JSON-RPC loop. |
| https://agentskills.io/specification | Portable SKILL.md, scripts and references with progressive disclosure. Host-specific metadata is optional. |
| https://developers.openai.com/codex/skills | Shared .agents/skills placement and optional OpenAI metadata. |
| https://code.claude.com/docs/en/skills | Claude .claude/skills placement for the installer adapter. |
| https://geminicli.com/docs/tools/mcp-server/ | Gemini CLI accepts stdio MCP; no need to impersonate a model provider. Host registration and live behavior remain separate checks. |

## Corrected assumptions

- Removed output-in-Japanese instructions and any need for a language parameter.
- Removed mandatory Codex-centered storage and onboarding. Explicit legacy settings
  remain supported to preserve existing credentials and usage ledgers.
- Removed our hardcoded Choice limit of 100 in favor of the documented 255 maximum:
  https://docs.typesafe.ai/primitives/choice
- Accepted structured/null instructions and descriptions, including Noul criteria:
  https://docs.typesafe.ai/primitives/advanced
- Retained Score's 2–10 levels because that is documented upstream, not our preference:
  https://docs.typesafe.ai/primitives/score
- Removed settings-loader ceilings of 20 batch items and 30 seconds. Visible defaults
  remain local resource controls. They are not provider capability claims.
- Added explicit backup updates rather than requiring users to hand-edit installed code.

The HTTP reference (https://docs.typesafe.ai/api) has narrower wording for some
EntryType fields than the dedicated Advanced Structure page. The implementation
follows the latter's explicit table; tests check serialization, not actual model
acceptance. SDK and desktop compatibility must be tested against installed versions.

No third-party implementation code was copied. Existing project license terms remain
unchanged. References are not endorsements or proof of equivalent performance.
