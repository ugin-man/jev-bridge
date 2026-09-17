"""Regression tests for home discovery without a Windows user profile."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("jev_home_test_cli", ROOT / "jev/scripts/jev.py")
bridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)


class HomeResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jev-home-tests-")
        self.home = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_codex_home_skips_system_home_lookup(self):
        base = self.home / "configured"
        with patch.dict(os.environ, {"CODEX_HOME": str(base)}, clear=True):
            with patch.object(Path, "home", side_effect=RuntimeError("no profile")) as lookup:
                selected, source = bridge.selected_home()
        lookup.assert_not_called()
        self.assertEqual(selected, base / "tools" / "jev-skill")
        self.assertEqual(source, "skill_storage")
        self.assertFalse(base.exists())

    def test_missing_system_home_has_structured_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", side_effect=RuntimeError("no profile")):
                with self.assertRaises(bridge.JevError) as caught:
                    bridge.selected_home()
        self.assertEqual(caught.exception.code, "home_directory_unavailable")
        self.assertFalse(caught.exception.as_dict()["automatic_retry"])

    def test_default_home_used_only_when_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=self.home) as lookup:
                selected, source = bridge.selected_home()
        lookup.assert_called_once_with()
        self.assertEqual(selected, self.home / ".codex" / "tools" / "jev-skill")
        self.assertEqual(source, "skill_storage")


if __name__ == "__main__":
    unittest.main()
