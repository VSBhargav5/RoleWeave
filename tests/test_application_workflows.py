import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import answer_library
from rehearsal_cards import suggested_requirements
from web_service import WebService, seed_web_demo
from workspace_bundle import export_bundle, inspect_bundle, restore_bundle, recovered_database


def answer(identifier='synthetic-answer', **changes):
    return {'id':identifier,'question':'Describe your Python experience','answer':'Built reviewed synthetic Python pipelines.',
            'aliases':['Tell us about Python projects'],'host':'example.invalid','page':'https://example.invalid/apply',
            'updated_at':'2026-11-26T09:00:00+00:00',**changes}


class ApplicationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);seed_web_demo(self.root/'jobs.db')
        self.service=WebService(self.root/'jobs.db',demo=True)
        self.addCleanup(self.service.tailoring.shutdown);self.addCleanup(self.service.assessment.shutdown)

    def change(self,action,**data):
        current=self.service.answers({'action':'read'})
        return self.service.answers({'action':action,'expected_sha256':current['sha256'],'confirmed':True,**data})

    def test_answer_crud_restart_stale_guard_and_helper_json_roundtrip(self):
        initial=self.service.answers({'action':'read'});self.assertEqual(initial['library'],answer_library.empty())
        saved=self.change('save',answer=answer())
        self.assertEqual(WebService(self.root/'jobs.db').answers({'action':'read'}),saved)
        with self.assertRaisesRegex(ValueError,'changed'):
            self.service.answers({'action':'delete','id':'synthetic-answer','expected_sha256':initial['sha256'],'confirmed':True})
        duplicate=answer_library.parse(json.dumps(saved['library']).encode())
        self.assertEqual(self.change('import',library=duplicate)['library'],saved['library'])
        duplicate['answers'][0]['answer']='Reviewed correction.'
        with self.assertRaisesRegex(ValueError,'conflicts'):self.change('import',library=duplicate)
        self.assertEqual(self.change('import',library=duplicate,replace=True)['library'],duplicate)
        self.assertEqual(self.change('delete',id='synthetic-answer')['library'],answer_library.empty())

    def test_invalid_answers_and_failed_import_do_not_mutate_library(self):
        self.change('save',answer=answer());original=self.service.answers({'action':'read'})
        for row in (answer(question='Will you need visa sponsorship?'),answer(aliases=['What is your salary?']),answer(page='https://another.invalid/apply'),answer(page='https://user:secret@example.invalid/apply'),answer(host='bad/host',page=''),answer(updated_at='yesterday'),answer(answer='')):
            with self.subTest(row=row['question']),self.assertRaises(ValueError):self.change('save',answer=row)
            self.assertEqual(self.service.answers({'action':'read'}),original)
        incoming={'format':'roleweave-answers-v1','answers':[answer('valid-new'),answer('invalid',question='Work authorization')]}
        with self.assertRaises(ValueError):self.change('import',library=incoming)
        self.assertEqual(self.service.answers({'action':'read'}),original)

    def test_answer_library_is_verified_and_restored_with_old_bundle_compatibility(self):
        old=export_bundle(self.service.store,self.service.artifacts)
        self.assertNotIn('answers.json',inspect_bundle(old)[0])
        expected=self.change('save',answer=answer())
        payload=export_bundle(self.service.store,self.service.artifacts);parts,summary=inspect_bundle(payload)
        self.assertEqual(answer_library.parse(parts['answers.json']),expected['library'])
        result=restore_bundle(payload,self.root/'restored')
        restored=WebService(recovered_database(self.root/'restored',result['id']))
        self.assertEqual(restored.answers({'action':'read'}),expected)
        result=restore_bundle(old,self.root/'old-restored')
        self.assertEqual(WebService(recovered_database(self.root/'old-restored',result['id'])).answers({'action':'read'})['library'],answer_library.empty())

    def test_batch_interview_requirements_create_one_review_and_preserve_original(self):
        p=self.service.profile();posting='We are pioneers in smart cities.\n* Strong proficiency in Python.\n* Experience building ETL pipelines.\nSalary based on experience.\nBenefits include professional development.'
        job=self.service.save_job({'title':'Synthetic data engineer','company':'Practice','market':'india_remote','posting':posting})
        choices=suggested_requirements(posting)
        self.assertEqual(choices,['Strong proficiency in Python.','Experience building ETL pipelines.'])
        args={'job_id':job['id'],'profile_id':p['id'],'profile_sha256':p['snapshot_sha256'],'fact_ids':['project-python'],'quotes':choices,'confirmed':True}
        result=self.service.prepare_rehearsal(args)
        self.assertEqual(len(result['practice_cards']),2)
        self.assertEqual(self.service.job(job['id'])['practice_cards'],[])
        for quotes in ([],choices*2,['Invented requirement'],choices+['Not in the posting']):
            with self.assertRaises(ValueError):self.service.prepare_rehearsal(args|{'quotes':quotes})
        with self.assertRaisesRegex(ValueError,'already linked'):self.service.prepare_rehearsal(args|{'job_id':result['id']})

    def test_saved_search_next_pages_keep_decisions_and_require_unchanged_filters(self):
        state=self.service.save_discovery_search({'name':'Python roles','query':'Python','location':'India','country':'IN','remote':True,'market':'india_remote','archived':False,'expected_revision':0})
        sid=state['searches'][0]['id']
        first=self.service.run_discovery({'id':sid,'expected_revision':state['revision'],'confirmed':True})
        original=first['candidates'][0]['id'];parent=first['runs'][-1]
        first=self.service.discovery_decision({'id':original,'action':'keep','expected_revision':first['revision'],'confirmed':True})
        second=self.service.run_discovery({'id':sid,'expected_revision':first['revision'],'confirmed':True,'previous_run':parent['id']})
        self.assertEqual(second['runs'][-1]['offset'],20);self.assertEqual(len(second['candidates']),4)
        self.assertEqual(next(c for c in second['candidates'] if c['id']==original)['status'],'kept')
        third=self.service.run_discovery({'id':sid,'expected_revision':second['revision'],'confirmed':True,'previous_run':second['runs'][-1]['id']})
        self.assertEqual(third['runs'][-1]['offset'],40);self.assertFalse(third['runs'][-1]['has_next'])
        self.assertEqual(WebService(self.root/'jobs.db').discovery.read(),third)
        with self.assertRaisesRegex(ValueError,'successful page'):
            self.service.run_discovery({'id':sid,'expected_revision':third['revision'],'confirmed':True,'previous_run':third['runs'][-1]['id']})
        saved=third['searches'][0]
        edited=self.service.save_discovery_search({**{k:v for k,v in saved.items() if k!='revision'},'query':'SQL','expected_revision':third['revision']})
        with self.assertRaisesRegex(ValueError,'unchanged'):
            self.service.run_discovery({'id':sid,'expected_revision':edited['revision'],'confirmed':True,'previous_run':parent['id']})

    def test_source_pages_replay_at_their_recorded_offsets_after_recovery(self):
        from job_search import parse_search
        self.service.demo=False;results=[]
        for offset,count in ((0,20),(20,1)):
            rows=[{'public_slug':'page-'+str(offset+i),'title':'Python engineer '+str(offset+i),'company':'Synthetic','description':'Python required.','url':'https://example.invalid/jobs/'+str(offset+i),'location':'India','work_mode':'remote'} for i in range(count)]
            raw=json.dumps({'data':rows,'meta':{'offset':offset,'limit':20,'total':21}}).encode()
            result=parse_search(raw,offset);results.append(result);self.service.searcher.snapshots[result['source_sha256']]=raw
        self.service.searcher.search=Mock(side_effect=results)
        state=self.service.save_discovery_search({'name':'Source page replay','query':'Python','location':'India','country':'IN','remote':True,'market':'india_remote','archived':False,'expected_revision':0})
        sid=state['searches'][0]['id'];state=self.service.run_discovery({'id':sid,'expected_revision':state['revision'],'confirmed':True})
        state=self.service.run_discovery({'id':sid,'expected_revision':state['revision'],'confirmed':True,'previous_run':state['runs'][-1]['id']})
        self.assertEqual(self.service.searcher.search.call_args.args[-1],20)
        self.assertEqual(state['candidates'][-1]['source_offset'],20)
        payload=export_bundle(self.service.store,self.service.artifacts)
        restored=restore_bundle(payload,self.root/'page-recovery')
        recovered=WebService(recovered_database(self.root/'page-recovery',restored['id']))
        self.assertEqual(recovered.discovery.read(),state)
