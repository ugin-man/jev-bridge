# Verification — 2.0.0

The v2 rework is tested with synthetic fixtures and offline tool traffic. No real
TypeSafe API key is used and no paid Jev request is made by the suite.

Local Linux / Python 3.13: the suite currently has 57 tests; 54 pass and 3 skip
(the two optional MCP SDK tests and the Windows DPAPI test). The MCP dependency
could not be installed in this container, so SDK validation is delegated to CI,
where JEV_REQUIRE_MCP_TESTS=1 makes missing SDK support a failure rather than a skip.

CI exercises Windows/Linux/macOS and Python 3.11/3.13, installing the package with
the MCP and keyring extras. It tests a real stdio SDK client/server handshake,
tool enumeration, offline evaluation, error propagation and missing-key behavior.
Windows also exercises DPAPI with a synthetic key. See Actions for the exact commit;
a workflow file alone is not evidence that those jobs passed.

New tests cover Unicode preservation without a language parameter, neutral storage,
legacy-store preservation, configurable batches larger than 20, documented Choice
maximum, structured/null descriptions, CLI stdin, no accidental execution, installation
backup updates, native-vault rejection of unsafe backends and existing-result protection.

Still unverified: actual Jev responses/accuracy, each desktop application's end-to-end
workflow, native interactive macOS/Linux vaults, user-local Windows launchers and
corporate proxy environments. A protocol test is not a live model or app benchmark.
