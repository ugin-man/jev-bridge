# Verification — 2.0.0

The v2 rework is tested with synthetic fixtures and offline tool traffic. No real
TypeSafe API key is used and no paid Jev request is made by the suite.

Local Linux / Python 3.13: the suite currently has 57 tests; 54 pass and 3 skip
(the two optional MCP SDK tests and the Windows DPAPI test). The MCP dependency
could not be installed in this container, so SDK validation is delegated to CI,
where JEV_REQUIRE_MCP_TESTS=1 makes missing SDK support a failure rather than a skip.

## Confirmed GitHub Actions results

Commit `f802b254d5a184c68968d3a80a868d8b36afc7dc` passed all six jobs in
https://github.com/ugin-man/jev-bridge/actions/runs/35216245605
(Windows, Linux and macOS, each with Python 3.11 and 3.13).

CI installed the package with the MCP/keyring extras and ran an actual stdio SDK
client/server handshake, tool discovery, offline evaluation, error propagation and
missing-key checks. Windows also passed the DPAPI round trip with a synthetic key.
The Windows/Python 3.13 log confirms MCP 1.30.0, keyring 25.7.0, and 57 tests with
one platform-specific skip (the POSIX path test), no failures. On POSIX, the
Windows-only DPAPI test is skipped instead. All 57 test cases are exercised across
the matrix; this is not 57 model-accuracy measurements.

The uploaded source tree was hash-matched to the local test tree. A separate local
package installation and installed-command offline validation also succeeded.
Subsequent commits should be checked against their own Actions results.

New tests cover Unicode preservation without a language parameter, neutral storage,
legacy-store preservation, configurable batches larger than 20, documented Choice
maximum, structured/null descriptions, CLI stdin, no accidental execution, installation
backup updates, native-vault rejection of unsafe backends and existing-result protection.

Still unverified: actual Jev responses/accuracy, each desktop application's end-to-end
workflow, native interactive macOS/Linux vaults, user-local Windows launchers and
corporate proxy environments. A protocol test is not a live model or app benchmark.
