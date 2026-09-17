"""Real MCP SDK client/server tests. TypeSafe traffic stays disabled."""
from __future__ import annotations
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jev/scripts"))
HAS_MCP = importlib.util.find_spec("mcp") is not None
if os.environ.get("JEV_REQUIRE_MCP_TESTS") == "1" and not HAS_MCP:
    raise RuntimeError("CI requires the MCP extra; these tests must not silently skip.")


@unittest.skipUnless(HAS_MCP, "Install the MCP extra to test the official SDK")
class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_round_trip_and_error_result(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory() as temporary:
            params = StdioServerParameters(command=sys.executable,
                args=["-I", str(ROOT / "jev/scripts/jev_bridge.py"), "mcp"],
                env={**os.environ, "JEV_BRIDGE_HOME": temporary, "TYPESAFE_API_KEY": ""})
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    initialized = await session.initialize()
                    self.assertEqual(initialized.serverInfo.name, "jev-bridge")
                    tools = await session.list_tools()
                    self.assertEqual({t.name for t in tools.tools},
                                     {"jev_status", "jev_validate", "jev_evaluate", "jev_batch"})
                    result = await session.call_tool("jev_status", {})
                    self.assertFalse(result.isError)
                    result = await session.call_tool("jev_evaluate", {"state": "红色", "questions": {
                        "color": {"type": "noul", "instructions": "Is it red?"}}})
                    self.assertFalse(result.isError)
                    data = json.loads(result.content[0].text)
                    self.assertFalse(data["network_called"])
                    self.assertNotIn("answers", data)
                    failed = await session.call_tool("jev_validate", {"request": {"state": "fixture", "questions": {}}})
                    self.assertTrue(failed.isError)
                    denied = await session.call_tool("jev_evaluate", {"state": "fixture", "questions": {
                        "q": {"type": "noul", "instructions": "Red?"}}, "execute": True})
                    self.assertTrue(denied.isError)
                    self.assertIn("missing_api_key", denied.content[0].text)

    async def test_in_process_tools_use_the_shared_runtime(self):
        from jev_bridge import Bridge
        from jev_mcp import create_server
        from jev_core import JevClient
        from test_skill import fake_response
        with tempfile.TemporaryDirectory() as temporary:
            calls = []
            def transport(*args):
                calls.append(1)
                return fake_response(*args)
            client = JevClient(Path(temporary), transport=transport,
                               key_loader=lambda _: ("SYNTHETIC", "fixture"))
            server = create_server(Bridge(home=Path(temporary), client=client))
            await server.call_tool("jev_evaluate", {"state": "fixture", "questions": {
                "q": {"type": "noul", "instructions": "Red?"}}, "execute": True})
            self.assertEqual(calls, [1])
