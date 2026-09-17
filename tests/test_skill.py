"""Offline tests. Every model reply in this suite is a synthetic fixture."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


bridge = module('jev_skill_cli', ROOT / 'jev/scripts/jev.py')
installer = module('jev_skill_installer', ROOT / 'install_skill.py')
JevClient, JevError = bridge.JevClient, bridge.JevError


def fake_response(data, key, settings):
    request = json.loads(data)
    answers = {}
    for qid, q in request['questions'].items():
        kind = q['type']
        if kind == 'noul':
            answers[qid] = {'type': 'noul', 'noul': 0.8}
        elif kind == 'choice':
            keys = list(q['criteria'])
            answers[qid] = {'type': kind, 'choice': keys[0], 'confidence': 1.0,
                            'probabilities': {k: float(i == 0) for i, k in enumerate(keys)}}
        else:
            keys = [str(i) for i in range(len(q['criteria']))]
            answers[qid] = {'type': kind, 'score': 0.0, 'confidence': 1.0,
                            'probabilities': {k: float(i == 0) for i, k in enumerate(keys)},
                            'legend': {str(i): v for i, v in enumerate(q['criteria'])}}
    return {'model': 'jev-latest', 'answers': answers,
            'usage': {'input_tokens': 42, 'output_tokens': 7}}


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jev-skill-tests-')
        self.home = Path(self.temp.name)
        self.calls = []
        def transport(data, key, settings):
            self.calls.append(json.loads(data))
            return fake_response(data, key, settings)
        self.client = JevClient(self.home / 'client', transport=transport,
                                key_loader=lambda _: ('TEST_ONLY_NOT_A_REAL_KEY', 'fixture'))
        self.smoke = bridge.read_json_file(str(ROOT / 'jev/assets/smoke.json'))

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, value):
        path = self.home / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return str(path)

    def test_skill_metadata_and_references(self):
        text = (ROOT/'jev/SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\nname: jev\n'))
        self.assertIn('description:', text.split('---', 2)[1])
        self.assertLess(len(text.splitlines()), 250)
        for filename in ['API.md', 'CONNECTIONS.md', 'RECIPES.md']:
            self.assertTrue((ROOT/'jev/references'/filename).is_file())
        self.assertIn('allow_implicit_invocation: true', (ROOT/'jev/agents/openai.yaml').read_text(encoding="utf-8"))

    def test_all_request_examples_validate_without_key_or_network(self):
        with patch.object(self.client, 'key_loader', side_effect=AssertionError('must not load key')):
            for filename in ['smoke.json', 'product-pair.json']:
                req=bridge.read_json_file(str(ROOT/'jev/assets'/filename))
                r=bridge.validate_request(self.client, req)
                self.assertFalse(r['network_called'])
        self.assertEqual(self.calls, [])

    def test_recipe_and_data_make_valid_batch(self):
        req=bridge.request_from_files(None, str(ROOT/'jev/assets/support-recipe.json'), str(ROOT/'jev/assets/support-data.json'))
        r=bridge.validate_request(self.client, req)
        self.assertEqual(r['api_requests'], 2)
        self.assertFalse(r['network_called'])

    def test_no_execute_flag_means_no_network(self):
        r=bridge.execute_request(self.client, self.smoke)
        self.assertFalse(r['network_called'])
        self.assertFalse(r['execution_authorized'])
        self.assertFalse((self.client.home/'usage.sqlite3').exists())
        self.assertEqual(self.calls, [])

    def test_explicit_execute_uses_one_injected_transport_call(self):
        r=bridge.execute_request(self.client, self.smoke, execute=True)
        self.assertTrue(r['ok'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(set(self.calls[0]), {'state','model','questions'})
        self.assertEqual(set(r['answers']), set(self.smoke['questions']))

    def test_noul_and_score_response_shapes(self):
        req={'state':'fixture', 'questions':{'a':{'type':'noul','instructions':'Question?'},
              'b':{'type':'score','instructions':'Rate','criteria':['low','medium','high']}}}
        r=bridge.execute_request(self.client, req, execute=True)
        self.assertEqual(r['answers']['a']['noul'], .8)
        self.assertNotIn('confidence', r['answers']['a'])
        self.assertEqual(r['answers']['b']['score'], 0.0)

    def test_bad_score_stops_before_transport(self):
        req={'state':'fixture','questions':{'a':{'type':'score','instructions':'Rate','criteria':['one']}}}
        with self.assertRaises(JevError):
            bridge.execute_request(self.client, req, execute=True)
        self.assertEqual(self.calls, [])

    def test_duplicate_ids_rejected_before_any_transport(self):
        req={'items':[{'id':'a','state':'one'},{'id':'a','state':'two'}],'questions':self.smoke['questions']}
        with self.assertRaises(JevError):
            bridge.execute_request(self.client, req, execute=True)
        self.assertEqual(self.calls, [])

    def test_21_items_rejected(self):
        req={'items':[{'id':str(i),'state':'sample'} for i in range(21)],'questions':self.smoke['questions']}
        with self.assertRaises(JevError):
            bridge.execute_request(self.client, req, execute=True)
        self.assertEqual(self.calls, [])

    def test_batch_keeps_records_separate(self):
        req={'items':[{'id':'a','state':'alpha'},{'id':'b','state':'beta'}],'questions':self.smoke['questions']}
        r=bridge.execute_request(self.client, req, execute=True)
        self.assertEqual([c['state'] for c in self.calls], ['alpha','beta'])
        self.assertEqual([item['id'] for item in r['results']], ['a','b'])

    def test_failed_batch_does_not_retry_or_drop_not_started(self):
        def failing(data, key, settings):
            self.calls.append(json.loads(data))
            if len(self.calls)==2:
                raise JevError('timeout','Synthetic timeout', ambiguous_charge=True)
            return fake_response(data,key,settings)
        self.client.transport=failing
        req={'items':[{'id':str(i),'state':'sample'} for i in range(3)],'questions':self.smoke['questions']}
        r=bridge.execute_request(self.client, req, execute=True)
        self.assertFalse(r['ok'])
        self.assertEqual(len(self.calls),2)
        self.assertEqual(r['not_started_ids'],['2'])
        self.assertTrue(r['results'][0]['ok'])
        self.assertFalse(r['results'][1]['ok'])

    def test_daily_cap_shared_and_not_bypassed(self):
        self.client.home.mkdir()
        (self.client.home/'settings.json').write_text('{"max_daily_requests":1}')
        bridge.execute_request(self.client,self.smoke,execute=True)
        with self.assertRaises(JevError) as e:
            bridge.execute_request(self.client,self.smoke,execute=True)
        self.assertEqual(e.exception.code,'daily_limit')
        self.assertEqual(len(self.calls),1)

    def test_nonfinite_and_duplicate_json_rejected(self):
        for text in ['{"state":NaN,"questions":{}}','{"state":"a","state":"b","questions":{}}']:
            path=self.home/'bad.json';path.write_text(text)
            with self.assertRaises(JevError):
                bridge.read_json_file(str(path))

    def test_utf8_bom_accepted(self):
        p=self.home/'bom.json';p.write_bytes(b'\xef\xbb\xbf'+json.dumps(self.smoke,ensure_ascii=False).encode())
        self.assertEqual(bridge.read_json_file(str(p)),self.smoke)

    def test_missing_file_gives_structured_error(self):
        with self.assertRaises(JevError) as e:
            bridge.read_json_file(str(self.home/'missing.json'))
        self.assertEqual(e.exception.code,'input_file_missing')

    def test_recipe_rejects_hidden_extra_fields(self):
        recipe=self.write_json('recipe.json',{'questions':self.smoke['questions'],'api_key':'not_real'})
        data=self.write_json('data.json',{'state':'sample'})
        with self.assertRaises(JevError):
            bridge.request_from_files(None,recipe,data)

    def test_conflicting_input_modes_rejected(self):
        with self.assertRaises(JevError):
            bridge.request_from_files('x.json','y.json','z.json')

    def test_single_request_rejects_unknown_model_or_endpoint(self):
        req={**self.smoke,'endpoint':'https://example.invalid'}
        path=self.write_json('bad.json',req)
        with self.assertRaises(JevError):
            bridge.request_from_files(path,None,None)

    def test_home_reuses_existing_worker_without_copying(self):
        base=self.home/'codex'
        worker=base/'tools/jev-worker';helper=base/'tools/jev-helper'
        for p in [worker,helper]:
            (p/'secrets').mkdir(parents=True)
            (p/'secrets/api-key.dpapi').write_bytes(b'NOT_A_KEY_FIXTURE')
        with patch.dict(os.environ,{'CODEX_HOME':str(base)},clear=True):
            selected,why=bridge.selected_home()
        self.assertEqual(selected,worker.resolve())
        self.assertEqual(why,'existing_encrypted_key')
        self.assertFalse((base/'tools/jev-skill').exists())

    def test_home_prefers_configured_helper_key_to_empty_worker(self):
        base=self.home/'codex';worker=base/'tools/jev-worker';helper=base/'tools/jev-helper'
        worker.mkdir(parents=True);(helper/'secrets').mkdir(parents=True)
        (helper/'secrets/api-key.dpapi').write_bytes(b'NOT_A_KEY_FIXTURE')
        with patch.dict(os.environ,{'CODEX_HOME':str(base)},clear=True):
            chosen,_=bridge.selected_home()
        self.assertEqual(chosen,helper.resolve())

    def test_explicit_home_and_fallback(self):
        with patch.dict(os.environ,{'JEV_SKILL_HOME':str(self.home/'explicit')},clear=True):
            self.assertEqual(bridge.selected_home()[0],(self.home/'explicit').resolve())
        with patch.dict(os.environ,{'CODEX_HOME':str(self.home/'codex')},clear=True):
            self.assertEqual(bridge.selected_home()[0],(self.home/'codex/tools/jev-skill').resolve())

    def test_output_reservation_and_no_overwrite(self):
        path=self.home/'result.json'
        f=bridge.reserve_output(str(path))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))['status'],'execution_not_finished')
        bridge.finish_output(f,{'ok':True,'value':'日本語'})
        f.close()
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))['value'],'日本語')
        with self.assertRaises(JevError) as e:
            bridge.reserve_output(str(path))
        self.assertEqual(e.exception.code,'output_exists')

    def test_installer_copies_only_skill_and_is_idempotent(self):
        dest=self.home/'skills';config=self.home/'config.toml';config.write_bytes(b'model="unchanged"')
        a=installer.install(ROOT/'jev',dest)
        b=installer.install(ROOT/'jev',dest)
        self.assertTrue(a['installed']);self.assertTrue(b['already_installed'])
        self.assertEqual(config.read_bytes(),b'model="unchanged"')
        self.assertEqual(installer.inventory(dest/'jev'),installer.inventory(ROOT/'jev'))
        self.assertFalse((dest/'.jev-install.lock').exists())

    def test_installer_refuses_different_existing_skill(self):
        dest=self.home/'skills';(dest/'jev').mkdir(parents=True)
        (dest/'jev/SKILL.md').write_text('DO NOT CHANGE')
        with self.assertRaises(ValueError):
            installer.install(ROOT/'jev',dest)
        self.assertEqual((dest/'jev/SKILL.md').read_text(encoding="utf-8"),'DO NOT CHANGE')

    def test_installer_refuses_existing_lock(self):
        dest=self.home/'skills';dest.mkdir();(dest/'.jev-install.lock').write_text('other process')
        with self.assertRaises(FileExistsError):
            installer.install(ROOT/'jev',dest)
        self.assertEqual((dest/'.jev-install.lock').read_text(encoding="utf-8"),'other process')

    def run_cli(self,*args,extra_env=None):
        env=os.environ.copy()
        for k in ['TYPESAFE_API_KEY','JEV_WORKER_HOME','JEV_HELPER_HOME']:
            env.pop(k,None)
        env['JEV_SKILL_HOME']=str(self.home/'cli')
        env.update(extra_env or {})
        result=subprocess.run([sys.executable,'-I',str(ROOT/'jev/scripts/jev.py'),*args],
                              text=True,encoding='utf-8',capture_output=True,env=env,timeout=10)
        return result,json.loads(result.stdout)

    def test_real_subprocess_validate(self):
        p,r=self.run_cli('validate','--file',str(ROOT/'jev/assets/smoke.json'))
        self.assertEqual(p.returncode,0)
        self.assertFalse(r['network_called'])

    def test_real_subprocess_default_run_offline(self):
        p,r=self.run_cli('run','--file',str(ROOT/'jev/assets/smoke.json'),'--out',str(self.home/'out.json'))
        self.assertEqual(p.returncode,0)
        self.assertFalse(r['network_called'])
        self.assertEqual(json.loads((self.home/'out.json').read_text(encoding="utf-8"))['dry_run'],True)

    def test_real_subprocess_status_never_prints_secret(self):
        fake='TEST_ONLY_DO_NOT_PRINT_9r7H'
        p,r=self.run_cli('status',extra_env={'TYPESAFE_API_KEY':fake})
        self.assertEqual(p.returncode,0)
        self.assertNotIn(fake,p.stdout+p.stderr)
        self.assertTrue(r['api_key_ready_locally'])
        self.assertFalse(r['credential_validated_with_service'])
        self.assertFalse(r['network_called'])

    def test_real_subprocess_missing_key_stops_before_transport(self):
        p,r=self.run_cli('run','--file',str(ROOT/'jev/assets/smoke.json'),'--execute')
        self.assertEqual(p.returncode,1)
        self.assertEqual(r['error']['code'],'missing_api_key')

    def test_real_subprocess_existing_output_refuses_before_key(self):
        path=self.home/'out.json';path.write_text('existing')
        p,r=self.run_cli('run','--file',str(ROOT/'jev/assets/smoke.json'),'--execute','--out',str(path))
        self.assertEqual(p.returncode,1)
        self.assertEqual(r['error']['code'],'output_exists')
        self.assertEqual(path.read_text(encoding="utf-8"),'existing')


if __name__=='__main__':
    unittest.main()
