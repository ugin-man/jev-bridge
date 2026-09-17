"""Bridge/upstream ownership without installing a skill or contacting a service."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'jev/scripts'))
import jev_bridge
import jev_core
import typesafe_transport
from test_skill import installer, fake_response


class UpstreamOwnershipTests(unittest.TestCase):
    def test_companion_delegates_to_unmodified_official_skill(self):
        text = (ROOT / 'jev/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('typesafe-ai', text)
        self.assertIn('https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md', text)
        self.assertIn('execution companion', text)
        self.assertNotIn('## Prepare the decision', text)
        self.assertFalse((ROOT / 'skills/typesafe-ai').exists())

    def test_installer_leaves_upstream_skill_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'skills'
            official = root / 'typesafe-ai' / 'SKILL.md'
            official.parent.mkdir(parents=True)
            original = b'UNMODIFIED SYNTHETIC UPSTREAM INSTALLATION\n'
            official.write_bytes(original)
            installer.install(ROOT / 'jev', root)
            installer.install(ROOT / 'jev', root, update=True)
            self.assertEqual(official.read_bytes(), original)
            self.assertTrue((root / 'jev/SKILL.md').is_file())

    def test_official_setup_is_separate_not_an_install_side_effect(self):
        text = (ROOT / 'jev/references/UPSTREAM.md').read_text(encoding='utf-8')
        self.assertIn('Do not use both methods', text)
        self.assertIn('npx skills add typesafe-ai/skills --skill typesafe-ai', text)
        self.assertIn('claude plugin install typesafe@typesafe-ai', text)
        src = (ROOT / 'install_skill.py').read_text(encoding='utf-8')
        self.assertNotIn('subprocess', src)

    def test_missing_sdk_does_not_reserve_request_budget(self):
        with tempfile.TemporaryDirectory() as d:
            client = jev_core.JevClient(Path(d), key_loader=lambda _: ('SYNTHETIC', 'fixture'))
            error = jev_core.JevError('missing_typesafe_sdk', 'Synthetic missing dependency')
            with patch.object(typesafe_transport, 'require_sdk', side_effect=error):
                with self.assertRaises(jev_core.JevError):
                    client.evaluate('fixture', {'q': {'type': 'noul', 'instructions': 'Red?'}})
                with self.assertRaises(jev_core.JevError):
                    client.batch([{'id': 'one', 'state': 'fixture'}],
                                 {'q': {'type': 'noul', 'instructions': 'Red?'}})
            self.assertFalse((Path(d) / 'usage.sqlite3').exists())

    def test_offline_validation_never_imports_provider_sdk(self):
        with tempfile.TemporaryDirectory() as d:
            client = jev_core.JevClient(Path(d))
            with patch.object(typesafe_transport, 'require_sdk', side_effect=AssertionError('No SDK in offline mode')):
                result = client.evaluate('fixture', {'q': {'type': 'noul', 'instructions': 'Red?'}}, dry_run=True)
            self.assertFalse(result['network_called'])
            self.assertNotIn('answers', result)

    def test_unknown_usage_is_not_zero_or_full_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            def transport(*args):
                value = fake_response(*args)
                value['usage'] = {}
                return value
            client = jev_core.JevClient(Path(d), transport=transport,
                                       key_loader=lambda _: ('SYNTHETIC', 'fixture'))
            result = client.evaluate('fixture', {'q': {'type': 'noul', 'instructions': 'Red?'}})
            self.assertEqual(result['usage'], {'input_tokens': None, 'output_tokens': None})
            self.assertFalse(result['local_token_accounting_updated'])
            self.assertEqual(client.status()['daily_usage']['reserved_requests'], 1)

    def test_legacy_raw_http_implementation_removed(self):
        source = (ROOT / 'jev/scripts/_vendor/jev_core.py').read_text(encoding='utf-8')
        self.assertNotIn('urllib.request', source)
        self.assertIn('from typesafe_transport import send', source)
        self.assertIn('typesafe-sdk', (ROOT / 'pyproject.toml').read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()
