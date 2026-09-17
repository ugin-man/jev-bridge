"""Portable-runtime regressions; synthetic responses only, never paid calls."""
from __future__ import annotations
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jev/scripts"))
import jev_bridge
import jev
from jev_core import Settings, JevClient, JevError, build_payload, load_key, save_key, _dpapi
from bridge_support import storage_home
from test_skill import fake_response, installer as install_skill


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.calls = []
        def transport(data, key, settings):
            self.calls.append(json.loads(data))
            return fake_response(data, key, settings)
        client = JevClient(self.home / "store", transport=transport,
                           key_loader=lambda _: ("SYNTHETIC_ONLY", "fixture"))
        self.bridge = jev_bridge.Bridge(home=self.home, client=client)
        self.questions = {"decision": {"type": "noul", "instructions": "Is the item red?"}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_language_parameter_and_unicode_preserved(self):
        for text in ("赤いコップ", "أحمر", "红色杯子", "taza roja", "rouge 🫖"):
            result = self.bridge.evaluate({"state": text, "questions": self.questions}, execute=True)
            self.assertTrue(result["ok"])
            self.assertEqual(self.calls[-1]["state"], text)
            self.assertNotIn("language", self.calls[-1])

    def test_bridge_home_precedence(self):
        with patch.dict(os.environ, {"JEV_BRIDGE_HOME": str(self.home / "neutral"),
                                    "CODEX_HOME": str(self.home / "other")}, clear=True):
            with patch.object(Path, "home", side_effect=AssertionError("must not look up home")):
                self.assertEqual(storage_home(), (self.home / "neutral", "JEV_BRIDGE_HOME"))

    @unittest.skipUnless(os.name != "nt", "POSIX path test")
    def test_fresh_linux_storage_without_codex(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", return_value=self.home), \
                patch("bridge_support.sys.platform", "linux"):
            # pathlib's platform class is fixed before the os.name mock on Windows.
            expected = self.home / ".local/state/jev-bridge"
            self.assertEqual(storage_home()[0], expected)

    def test_explicit_codex_home_no_profile_lookup(self):
        with patch.dict(os.environ, {"CODEX_HOME": str(self.home)}, clear=True), \
                patch.object(Path, "home", side_effect=AssertionError("unnecessary lookup")):
            self.assertEqual(storage_home()[0], self.home / "tools/jev-skill")

    def test_missing_home_is_structured(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", side_effect=RuntimeError("missing")):
            with self.assertRaises(JevError) as err:
                jev.selected_home()
            self.assertEqual(err.exception.code, "home_directory_unavailable")

    def test_legacy_store_preserves_ledger_path(self):
        legacy = self.home / ".codex/tools/jev-skill"
        legacy.mkdir(parents=True)
        (legacy / "usage.sqlite3").write_bytes(b"fixture")
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", return_value=self.home):
            self.assertEqual(storage_home()[0], legacy)

    def test_platform_store_does_not_fall_back_after_failure(self):
        with patch.dict(os.environ, {"JEV_BRIDGE_HOME": str(self.home / "neutral")}, clear=True):
            path, _ = storage_home()
            path.mkdir()
            (path / "settings.json").write_text("invalid", encoding="utf-8")
            with self.assertRaises(JevError):
                jev_bridge.Bridge().status()
            self.assertEqual(storage_home()[0], path)

    def test_choice_255_options(self):
        qs = {"分类": {"type": "choice", "instructions": "Pick", "criteria": {str(i): None for i in range(255)}}}
        self.assertTrue(self.bridge.evaluate({"state": "fixture", "questions": qs})["ok"])
        qs["分类"]["criteria"]["256"] = None
        with self.assertRaises(JevError):
            self.bridge.evaluate({"state": "fixture", "questions": qs})

    def test_structured_and_null_noul(self):
        qs = {"n": {"type": "noul", "instructions": {"question": "Red?"},
                    "criteria": {"true": {"examples": ["red"]}, "false": None}}}
        self.assertTrue(self.bridge.evaluate({"state": {}, "questions": qs})["ok"])
        self.assertFalse(self.calls)

    def test_score_structure_and_service_limit(self):
        qs = {"s": {"type": "score", "instructions": None, "criteria": [None, {"degree": "high"}]}}
        self.assertTrue(self.bridge.evaluate({"state": [], "questions": qs})["ok"])
        qs["s"]["criteria"] = ["level"] * 11
        with self.assertRaises(JevError):
            self.bridge.evaluate({"state": "fixture", "questions": qs})

    def test_local_batch_limit_can_exceed_twenty(self):
        store = self.bridge.client.home
        store.mkdir()
        (store / "settings.json").write_text(json.dumps({"max_batch_items": 60}), encoding="utf-8")
        request = {"items": [{"id": str(i), "state": "fixture"} for i in range(50)], "questions": self.questions}
        self.assertEqual(self.bridge.evaluate(request)["api_requests"], 50)
        self.assertEqual(self.calls, [])

    def test_configurable_limits_accept_explicit_zero_daily_caps(self):
        self.home.joinpath("settings.json").write_text(json.dumps({"max_daily_requests": 0,
              "max_daily_payload_bytes": 0, "max_batch_seconds": 0, "request_timeout_seconds": 120,
              "max_batch_items": 300, "model": "new-model-id"}), encoding="utf-8")
        settings = Settings.load(self.home)
        self.assertEqual(settings.max_batch_items, 300)
        self.assertEqual(settings.model, "new-model-id")

    def test_invalid_settings_boolean_not_number(self):
        for value in ({"max_batch_items": True}, {"max_batch_items": 0}, {"trust_environment": "yes"}):
            (self.home / "settings.json").write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(JevError):
                Settings.load(self.home)

    def test_unknown_request_fields_are_rejected_without_network(self):
        with self.assertRaises(JevError):
            self.bridge.evaluate({"state": "fixture", "questions": self.questions, "api_key": "hidden"}, execute=True)
        self.assertEqual(self.calls, [])

    def test_execute_flag_type(self):
        with self.assertRaises(JevError):
            self.bridge.evaluate({"state": "fixture", "questions": self.questions}, execute="false")

    def test_public_cli_stdin_without_installed_host(self):
        env = {**os.environ, "JEV_BRIDGE_HOME": str(self.home / "process")}
        env.pop("TYPESAFE_API_KEY", None)
        process = subprocess.run([sys.executable, "-I", str(ROOT / "jev/scripts/jev_bridge.py"),
                                  "validate", "--file", "-"], input=json.dumps({"state": "红色", "questions": self.questions}),
                                  capture_output=True, text=True, encoding="utf-8", env=env, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertFalse(json.loads(process.stdout)["network_called"])

    def test_custom_installer_destination_and_backup_update(self):
        dest = self.home / "custom/skills"
        install_skill.install(ROOT / "jev", dest)
        original = dest / "jev/SKILL.md"
        original.write_text("local customization", encoding="utf-8")
        result = install_skill.install(ROOT / "jev", dest, update=True)
        self.assertEqual((Path(result["backup"]) / "SKILL.md").read_text(encoding="utf-8"), "local customization")
        self.assertEqual(install_skill.inventory(ROOT / "jev"), install_skill.inventory(dest / "jev"))

    def test_installer_target_roots(self):
        with patch.object(Path, "home", return_value=self.home):
            self.assertEqual(install_skill.target_root("claude", "user"), self.home / ".claude/skills")
            self.assertEqual(install_skill.target_root("generic", "user"), self.home / ".agents/skills")
        self.assertEqual(install_skill.target_root("generic", "project", self.home), self.home / ".agents/skills")

    def test_existing_output_refused_by_public_cli(self):
        out = self.home / "result.json"
        out.write_text("old", encoding="utf-8")
        env = {**os.environ, "JEV_BRIDGE_HOME": str(self.home / "process")}
        process = subprocess.run([sys.executable, "-I", str(ROOT / "jev/scripts/jev_bridge.py"),
            "run", "--file", str(ROOT / "jev/assets/smoke.json"), "--execute", "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=15)
        self.assertEqual(json.loads(process.stdout)["error"]["code"], "output_exists")
        self.assertEqual(out.read_text(), "old")

    def test_environment_credentials_without_platform_vault(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "SYNTHETIC_ONLY"}, clear=True):
            self.assertEqual(load_key(self.home), ("SYNTHETIC_ONLY", "process_environment"))

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI integration")
    def test_windows_dpapi_round_trip(self):
        save_key(self.home, "SYNTHETIC_ONLY")
        self.assertEqual(load_key(self.home), ("SYNTHETIC_ONLY", "windows_dpapi"))
        self.assertNotIn(b"SYNTHETIC_ONLY", (self.home / "secrets/api-key.dpapi").read_bytes())

    def test_native_vault_without_plaintext_fallback(self):
        from jev_core import secure_keyring
        fake = Mock()
        fake.get_keyring.return_value = object()
        with patch.dict(sys.modules, {"keyring": fake}):
            with self.assertRaises(JevError):
                secure_keyring()


if __name__ == "__main__":
    unittest.main()
