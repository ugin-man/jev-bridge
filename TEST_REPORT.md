# Verification — 2.1.0

This revision makes the bridge an execution companion to unmodified official
TypeSafe guidance and uses the official Python SDK for provider traffic.

## Confirmed 2.1 CI

Commit `182cfd8afd367626d7befbfead81cfbaf35793cc` passed all six jobs in
https://github.com/ugin-man/jev-bridge/actions/runs/35230318433
(Windows, Linux and macOS, each with Python 3.11 and 3.13).

CI installed the declared dependencies, including typesafe-sdk 0.6.0 and the
actual MCP SDK. The Windows/Python 3.13 log confirms httpx2 2.13.0, MCP 1.30.0,
73 discovered tests, 72 passed, and one POSIX-only skip. Windows DPAPI and both
real MCP protocol tests passed. Every new TypeSafe SDK test executed, including
serialization, typed parsing, no retries, redirect refusal, stream size limits,
sanitary error handling and the full SDK-to-bridge-to-ledger path.
The POSIX-only path check and Windows-only DPAPI check are exercised on their
respective platforms; OS-specific skips are intentional.

All provider responses were supplied by an in-process HTTP MockTransport. The
SDK code is real; the Jev responses and credentials are synthetic. This verifies
integration behavior, NOT live account access, model accuracy or real throughput.
No real TypeSafe request or user-key operation was performed.

## Local checks

Linux/Python 3.13.5: 73 tests discovered, 61 passed and 12 skipped (nine TypeSafe
SDK tests, two MCP tests, one Windows DPAPI test). Dependencies unavailable locally
were tested in CI, where JEV_REQUIRE_TYPESAFE_TESTS=1 and JEV_REQUIRE_MCP_TESTS=1
make missing dependencies an error rather than a silent skip.

The local Git tree matched uploaded tree bdd1a5bfdf637a7392ba353ceb157a770c50dc30.
The wheel built without dependencies, then was installed in a fresh virtual
environment. From outside the source checkout, the installed `jev-bridge --version`
returned 2.1.0 and the smoke input validated with network_called=false. This clean
local check deliberately omitted SDK dependencies and exercised only offline mode.

## Still separate

The official skill installer is documented, not run against a user's host in CI.
Native interactive vaults, user-local launchers, each desktop host, actual Jev
responses and accuracy still need separate live verification. A source update does
not update installed user copies. Subsequent runtime commits require their own CI.

## Historical 2.0 reference

The previous runtime passed its six-environment checks at f802b254d5a184c68968d3a80a868d8b36afc7dc:
https://github.com/ugin-man/jev-bridge/actions/runs/35216245605
Its 57-test suite did not test the new TypeSafe SDK transport. The 2.1 evidence
above supersedes it for the changed provider connection.
