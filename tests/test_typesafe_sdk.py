"""Real upstream SDK and HTTP stack, with synthetic in-process HTTP only."""
from __future__ import annotations
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'jev/scripts'))
import jev_bridge
import jev_core
import typesafe_transport
from test_skill import fake_response

HAS_SDK = importlib.util.find_spec('typesafe_sdk') is not None
if os.environ.get('JEV_REQUIRE_TYPESAFE_TESTS') == '1' and not HAS_SDK:
    raise RuntimeError('CI must install the real TypeSafe SDK; do not skip these tests.')


@unittest.skipUnless(HAS_SDK, 'Install the declared TypeSafe SDK dependency')
class TypeSafeSDKTests(unittest.TestCase):
    def setUp(self):
        import httpx2
        self.http = httpx2
        self.settings = jev_core.Settings()
        self.payload = {'state': {'text': '赤い red rouge'}, 'model': 'jev-latest', 'questions': {
            'color': {'type': 'choice', 'instructions': 'Color?', 'criteria': {'red': None, 'other': None}},
            'present': {'type': 'noul', 'instructions': 'A color is present?'},
            'level': {'type': 'score', 'instructions': 'Degree?', 'criteria': ['low', 'high']}}}
        self.data = jev_core.encode_json(self.payload)
        self.calls = []

    def send(self, handler, settings=None):
        def capture(request):
            self.calls.append(request)
            return handler(request)
        return typesafe_transport.send(self.data, 'SYNTHETIC_API_KEY', settings or self.settings,
                                       http_transport=self.http.MockTransport(capture))

    def response(self, request, usage=None):
        value = fake_response(request.content, 'SYNTHETIC', self.settings)
        if usage is not None:
            value['usage'] = usage
        return self.http.Response(200, json=value)

    def test_public_sdk_real_serialization_and_parsing(self):
        result = self.send(self.response)
        self.assertEqual(len(self.calls), 1)
        request = self.calls[0]
        self.assertEqual(str(request.url), jev_core.API_URL)
        self.assertEqual(request.method, 'POST')
        self.assertEqual(json.loads(request.content), self.payload)
        self.assertEqual(request.headers['authorization'], 'Bearer SYNTHETIC_API_KEY')
        self.assertEqual(result['answers']['color']['choice'], 'red')
        self.assertEqual(result['answers']['level']['legend'], {'0': 'low', '1': 'high'})
        jev_core.validate_response(result, self.payload['questions'])

    def test_no_environment_endpoint_or_model_override(self):
        with patch.dict(os.environ, {'TYPESAFE_BASE_URL': 'https://invalid.example/',
                                     'TYPESAFE_DEFAULT_MODEL': 'not-the-requested-model'}):
            self.send(self.response)
        self.assertEqual(str(self.calls[0].url), jev_core.API_URL)
        self.assertEqual(json.loads(self.calls[0].content)['model'], 'jev-latest')

    def test_sdk_retries_disabled_and_errors_sanitized(self):
        for status in [401, 402, 429, 500, 529]:
            with self.subTest(status=status):
                self.calls.clear()
                with self.assertRaises(jev_core.JevError) as caught:
                    self.send(lambda request: self.http.Response(status, json={'error': 'PRIVATE_ECHO SYNTHETIC_API_KEY'},
                                                               headers={'retry-after': '0'}))
                error = caught.exception.as_dict()
                self.assertEqual(len(self.calls), 1)
                self.assertEqual(error['http_status'], status)
                self.assertFalse(error['automatic_retry'])
                self.assertNotIn('PRIVATE_ECHO', str(error))
                self.assertNotIn('SYNTHETIC_API_KEY', str(error))

    def test_redirect_is_not_followed(self):
        with self.assertRaises(jev_core.JevError) as caught:
            self.send(lambda request: self.http.Response(302, headers={'location': 'https://invalid.example/steal'}))
        self.assertEqual(caught.exception.status, 302)
        self.assertEqual(len(self.calls), 1)

    def test_timeout_not_retried(self):
        def fail(request):
            raise self.http.ReadTimeout('PRIVATE_ECHO', request=request)
        with self.assertRaises(jev_core.JevError) as caught:
            self.send(fail)
        self.assertEqual(caught.exception.code, 'timeout')
        self.assertTrue(caught.exception.ambiguous_charge)
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn('PRIVATE_ECHO', str(caught.exception))

    def test_connection_failure_not_retried(self):
        def fail(request):
            raise self.http.ConnectError('PRIVATE_ECHO', request=request)
        with self.assertRaises(jev_core.JevError) as caught:
            self.send(fail)
        self.assertEqual(caught.exception.code, 'network_error')
        self.assertEqual(len(self.calls), 1)

    def test_invalid_response_is_not_a_result(self):
        with self.assertRaises(jev_core.JevError) as caught:
            self.send(lambda request: self.http.Response(200, json={'PRIVATE_ECHO': 'broken'}))
        self.assertEqual(caught.exception.code, 'invalid_api_response')
        self.assertTrue(caught.exception.ambiguous_charge)
        self.assertNotIn('PRIVATE_ECHO', str(caught.exception))

    def test_stream_limit_and_closure_before_sdk_parsing(self):
        trace = []
        class Stream(self.http.SyncByteStream):
            def __iter__(self):
                for _ in range(100):
                    trace.append('chunk')
                    yield b'x' * 20
            def close(self):
                trace.append('closed')
        with self.assertRaises(jev_core.JevError) as caught:
            self.send(lambda request: self.http.Response(200, stream=Stream()),
                      settings=replace(self.settings, max_response_bytes=30))
        self.assertEqual(caught.exception.code, 'response_too_large')
        self.assertEqual(trace.count('chunk'), 2)
        self.assertIn('closed', trace)

    def test_real_sdk_to_bridge_pipeline_and_unknown_usage(self):
        with tempfile.TemporaryDirectory() as d:
            def adapter(data, key, settings):
                return typesafe_transport.send(data, key, settings,
                    http_transport=self.http.MockTransport(lambda r: self.response(r, usage={})))
            client = jev_core.JevClient(Path(d), transport=adapter,
                                       key_loader=lambda _: ('SYNTHETIC', 'fixture'))
            runtime = jev_bridge.Bridge(home=Path(d), client=client)
            result = runtime.evaluate({'state': self.payload['state'], 'questions': self.payload['questions']}, execute=True)
            self.assertTrue(result['ok'])
            self.assertEqual(result['usage'], {'input_tokens': None, 'output_tokens': None})
            self.assertFalse(result['local_token_accounting_updated'])
            self.assertEqual(runtime.status()['daily_usage']['reserved_requests'], 1)

if __name__ == '__main__':
    unittest.main()
