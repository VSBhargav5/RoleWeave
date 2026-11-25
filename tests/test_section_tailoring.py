"""Small AI contracts and cumulative application drafts, with synthetic responses only."""
import copy
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pypdf import PdfReader

import ai_tailoring as tailoring
import job_assessment as assessment
import model_providers as providers
import refinement_history as history
from application_draft import load_draft
from model_preferences import save_settings
from tailoring_session import TailoringSession
from test_ai_tailoring import proposed
from test_model_providers import config, wrapped
from web_service import WebService, seed_web_demo
from workspace_bundle import export_bundle, restore_bundle, recovered_database


class SectionTailoringTests(unittest.TestCase):
    def test_six_source_summary_and_empty_full_template_are_supported(self):
        sources=[{'id':'source-'+str(i)} for i in range(6)]
        ids=[f['id'] for f in sources]
        small={'headline':{'text':'Data Engineer','fact_ids':ids},
               'summary':{'text':'Source-backed summary. '*40,'fact_ids':ids},'questions':[]}
        self.assertEqual(tailoring.task_result(small,sources,'summary')['summary'],small['summary'])
        full={key:{'text':'','fact_ids':[]} for key in tailoring.FIELDS}
        full.update(bullets=[],**small)
        self.assertEqual(tailoring.task_result(full,sources,'summary'),tailoring.task_result(small,sources,'summary'))
        for changes,code in (({'summary':{'text':'x'*1201,'fact_ids':ids}},'length'),
                             ({'summary':{'text':'Supported text','fact_ids':['invented']}},'references'),
                             ({'unexpected':'value'},'shape')):
            with self.assertRaises(tailoring.SectionDraftError) as error:tailoring.task_result(small|changes,sources,'summary')
            self.assertEqual(error.exception.code,code)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);seed_web_demo(self.root/'jobs.db')
        self.service=WebService(self.root/'jobs.db',demo=True);self.store=self.service.store
        self.addCleanup(self.service.tailoring.shutdown);self.addCleanup(self.service.assessment.shutdown)
        self.profile=self.service.profile();self.job=self.service.job(self.store.list_jobs()[0]['id'])
        self.args={'profile_id':self.profile['id'],'profile_sha256':self.profile['snapshot_sha256'],
                   'job_id':self.job['id'],'fact_ids':['project-python'],'instruction':'Tailor concise source-backed wording.'}

    def complete(self,task,base=None,retain=False):
        args=self.args|{'task':task,'retain_history':retain}
        if base:args.update(profile_id=base['profile']['id'],profile_sha256=base['profile']['snapshot_sha256'],base_draft_id=base['draft_id'])
        preview=self.service.tailoring.preview(args)
        self.service.tailoring.send({'id':preview['id'],'sha256':preview['sha256'],'key':'','confirmed':True})
        self.service.tailoring.entries[preview['id']]['thread'].join(3)
        result=self.service.tailoring.status({'id':preview['id']});self.assertEqual(result['status'],'completed',result)
        return preview,result

    def accept(self,preview,result,fields=None,edits=None):
        return self.service.tailoring.accept({'id':preview['id'],'result_sha256':result['result_sha256'],
            'fields':fields or {},'fact_edits':edits or [],'confirmed':True})

    def test_only_requested_fields_and_small_bounds_reach_each_provider(self):
        for task,keys in tailoring.TASK_FIELDS.items():
            original=tailoring.request_payload(self.job,self.profile['profile'],['project-python'],'Shorter.',proposed(),task)
            body=json.loads(original);self.assertEqual(body['max_output_tokens'],8192);schema=body['text']['format']['schema']
            self.assertEqual(set(schema['properties']),{*keys,'questions'})
            content=json.loads(body['input'][0]['content'])
            self.assertEqual(set(content['previous_draft']),{*keys,'questions'})
            self.assertEqual(content['task'],task)
            for kind in providers.KINDS:
                with self.subTest(task=task,kind=kind):
                    request=providers.request_payload(original,config(kind))
                    self.assertNotIn(self.profile['profile']['email'].encode(),request)
                    response={k:proposed()[k] for k in (*keys,'questions')}
                    actual=providers.structured_response(wrapped(kind,response),config(kind))
                    normalized=tailoring.task_result(actual,[{'id':'project-python'}],task)
                    self.assertEqual(normalized['summary']['text'],response.get('summary',{}).get('text',''))
            if task=='summary':self.assertEqual(schema['properties']['summary']['properties']['text']['maxLength'],1200)
            if task=='experience':self.assertEqual(schema['properties']['bullets']['maxItems'],3)

    def test_section_response_rejects_wrong_scope_long_output_and_invented_source(self):
        source=[{'id':'project-python'}];good={k:proposed()[k] for k in ('headline','summary','questions')}
        for edit in ({'bullets':[]},{'summary':{'text':'x'*1201,'fact_ids':['project-python']}},
                     {'headline':{'text':'Invented','fact_ids':['unknown']}},{'questions':['x'*201]}):
            with self.subTest(edit=edit),self.assertRaises(ValueError):tailoring.task_result(good|edit,source,'summary')
        with self.assertRaises(ValueError):tailoring.request_payload(self.job,self.profile['profile'],['project-python'],'Shorter.',task='entire-resume')
        large=copy.deepcopy(self.profile['profile']);large['facts'][0]['claim']='x'*12001
        with self.assertRaises(ValueError):tailoring.request_payload(self.job,large,['project-python'],'Shorter.',task='summary')

    def test_summary_experience_letter_passes_accumulate_without_altering_master(self):
        p,r=self.complete('summary');first=self.accept(p,r,{'summary':'Reviewed application summary.'})
        self.assertEqual(len(first['selected_fact_ids']),len([f for f in self.profile['profile']['facts'] if f['reviewed']]))
        p,r=self.complete('experience',first);second=self.accept(p,r,edits=[{'id':'project-python','text':'Reviewed application project.'}])
        self.assertEqual(second['profile']['profile']['summary'],'Reviewed application summary.')
        p,r=self.complete('letter',second);third=self.accept(p,r,{'letter_intro':'Reviewed letter introduction.'})
        self.assertEqual(third['profile']['profile'],second['profile']['profile'])
        p,r=self.complete('summary',third,retain=True)
        reopened=self.service.tailoring.reopen({'id':r['history_id'],'job_id':self.job['id']})
        fourth=self.accept(reopened,reopened,{'summary':'A later reviewed summary.'})
        saved=load_draft(self.store,fourth['draft_id'])
        self.assertEqual(saved['letter']['letter_intro'],'Reviewed letter introduction.')
        self.assertEqual(saved['profile']['profile']['facts'][0]['claim'],'Reviewed application project.')
        self.assertEqual(saved['selected_fact_ids'],third['selected_fact_ids'])
        from resume_render import resume_pdf
        pdf=PdfReader(BytesIO(resume_pdf(saved['profile']['profile'],saved['selected_fact_ids'])))
        printed=' '.join(' '.join(page.extract_text() for page in pdf.pages).split())
        self.assertIn('A later reviewed summary.',printed);self.assertIn('Reviewed application project.',printed)
        self.assertEqual(self.store.active_profile()['id'],self.profile['id'])
        self.assertEqual(self.store.load_profile(first['profile']['id'])['profile']['summary'],'Reviewed application summary.')
        self.assertEqual(history.load_turn(self.store,r['history_id'])['format'],'roleweave-refinement-turn-v2')
        bundle=export_bundle(self.store,self.service.artifacts);restored=restore_bundle(bundle,self.root/'restored')
        other=WebService(recovered_database(self.root/'restored',restored['id']),demo=True)
        self.addCleanup(other.tailoring.shutdown);self.addCleanup(other.assessment.shutdown)
        recovered=load_draft(other.store,fourth['draft_id'])
        self.assertEqual(recovered['profile'],saved['profile']);self.assertEqual(recovered['letter'],saved['letter'])
        self.assertEqual(other.tailoring.reopen({'id':r['history_id'],'job_id':self.job['id']})['task'],'summary')

    def test_failed_next_pass_does_not_change_saved_draft(self):
        p,r=self.complete('summary');saved=self.accept(p,r,{'summary':'Keep this accepted section.'})
        before=load_draft(self.store,saved['draft_id'])
        session=TailoringSession(self.store,demo=False);self.addCleanup(session.shutdown)
        save_settings(self.store,config('openrouter'))
        args=self.args|{'task':'experience','profile_id':saved['profile']['id'],
            'profile_sha256':saved['profile']['snapshot_sha256'],'base_draft_id':saved['draft_id']}
        preview=session.preview(args)
        with patch('model_providers.request_model',side_effect=providers.ModelError('output_limit')):
            session.send({'id':preview['id'],'sha256':preview['sha256'],'key':'synthetic','confirmed':True})
            session.entries[preview['id']]['thread'].join(3)
        self.assertEqual(session.status({'id':preview['id']})['error_code'],'RW-AI-OUTPUT-LIMIT')
        self.assertEqual(load_draft(self.store,saved['draft_id']),before)

    def test_about_only_experience_is_explicit_source_and_replaces_about_once(self):
        from test_career_entries import entry
        from resume_render import resume_text
        fact=entry('Experience','about-only',title='Synthetic software evaluator',organization='Practice',
                   about='Evaluated synthetic Python agent changes with repository tests.',started='2025-01',current=True)
        profile=self.profile['profile']|{'facts':[fact]}
        identifier=self.store.save_profile(json.dumps(profile).encode());item=self.store.load_profile(identifier)
        save_settings(self.store,config('openrouter'))
        args=self.args|{'profile_id':identifier,'profile_sha256':item['snapshot_sha256'],'fact_ids':['about-only'],'task':'experience'}
        session=TailoringSession(self.store,demo=False);self.addCleanup(session.shutdown)
        preview=session.preview(args);body=json.loads(preview['payload']);prompt=body['messages'][0]['content']
        self.assertIn('empty claim does not mean an empty entry',prompt)
        self.assertNotIn('not permission to invent accomplishments for an empty claim',prompt)
        response={'bullets':[{'fact_id':'about-only','text':'Reviewed synthetic Python agent changes using repository tests.'}],'questions':[]}
        with patch('model_providers.request_model',return_value=wrapped('openrouter',response)):
            session.send({'id':preview['id'],'sha256':preview['sha256'],'key':'synthetic','confirmed':True})
            session.entries[preview['id']]['thread'].join(3)
        result=session.status({'id':preview['id']});self.assertEqual(result['status'],'completed',result)
        saved=session.accept({'id':preview['id'],'result_sha256':result['result_sha256'],'fields':{},
            'fact_edits':[{'id':'about-only','text':response['bullets'][0]['text']}],'confirmed':True})
        actual=saved['profile']['profile']['facts'][0]
        self.assertEqual(actual['claim'],'');self.assertEqual(actual['details']['fields']['about'],response['bullets'][0]['text'])
        expected=copy.deepcopy(fact['details']);expected['fields']['about']=response['bullets'][0]['text']
        self.assertEqual(actual['details'],expected)
        self.assertEqual(self.store.load_profile(identifier)['profile']['facts'][0],fact)
        printed=resume_text(saved['profile']['profile'],['about-only'])
        self.assertEqual(printed.count(response['bullets'][0]['text']),1)
        self.assertNotIn(fact['details']['fields']['about'],printed)
        from resume_render import resume_pdf
        pdf=PdfReader(BytesIO(resume_pdf(saved['profile']['profile'],['about-only'])))
        printed=' '.join(' '.join(page.extract_text() for page in pdf.pages).split())
        self.assertEqual(printed.count(response['bullets'][0]['text']),1)

    def test_empty_section_remains_inspectable_but_cannot_be_accepted(self):
        save_settings(self.store,config('openrouter'))
        session=TailoringSession(self.store,demo=False);self.addCleanup(session.shutdown)
        preview=session.preview(self.args|{'task':'experience','retain_history':True})
        with patch('model_providers.request_model',return_value=wrapped('openrouter',{'bullets':[],'questions':[]})):
            session.send({'id':preview['id'],'sha256':preview['sha256'],'key':'synthetic','confirmed':True})
            session.entries[preview['id']]['thread'].join(3)
        result=session.status({'id':preview['id']});self.assertEqual(result['status'],'completed')
        with self.assertRaises(ValueError):session.accept({'id':preview['id'],'result_sha256':result['result_sha256'],
            'fact_edits':[],'fields':{},'confirmed':True})
        self.assertEqual(history.load_turn(self.store,result['history_id'])['draft']['bullets'],[])
        self.assertEqual(self.store.active_profile()['id'],self.profile['id'])

    def test_compact_assessment_is_bounded_saved_and_replayed_separately(self):
        args={k:v for k,v in self.args.items() if k!='instruction'}|{'compact':True}
        preview=self.service.assessment.preview(args);body=json.loads(preview['payload'])
        schema=body['response_format']['json_schema']['schema']
        self.assertEqual(schema['properties']['requirements']['maxItems'],6)
        self.service.assessment.send({'id':preview['id'],'sha256':preview['sha256'],'key':'','confirmed':True})
        self.service.assessment.entries[preview['id']]['thread'].join(3)
        result=self.service.assessment.status({'id':preview['id']});self.assertEqual(result['status'],'completed',result)
        saved=self.service.assessment.accept({'id':preview['id'],'proposal_sha256':result['proposal_sha256'],'reviewed':result['proposal'],'confirmed':True})
        record,_,_=assessment.load(self.store,saved['id'])
        self.assertEqual(record['format'],'roleweave-job-assessment-v2')
        self.assertNotEqual(record['comparison_key'],assessment.comparison_key(record['profile_sha256'],record['fact_ids'],record['provider']))
        with self.assertRaises(ValueError):assessment.validate_compact(result['proposal']|{'questions':['Long']*4})

    def test_focused_assessment_limits_scope_and_replays_without_breaking_old_records(self):
        excerpt='Design Python data pipelines. Implement data validation and automated testing.'
        job=self.service.save_job({'title':'Synthetic data engineer','company':'Practice SDK','market':'india_remote',
                                  'posting':'Company background. '*1000+excerpt+' Compensation details.'})
        args={k:v for k,v in self.args.items() if k!='instruction'}|{'job_id':job['id'],'compact':True,'focus':excerpt}
        session=assessment.AssessmentSession(self.store,demo=False);self.addCleanup(session.shutdown)
        preview=session.preview(args);body=json.loads(preview['payload'])
        self.assertEqual(body['max_tokens'],8192)
        content=json.loads(body['messages'][1]['content']);self.assertEqual(content['job']['posting'],excerpt)
        self.assertNotIn('Company background.',preview['payload'])
        self.assertEqual(body['response_format']['json_schema']['schema']['properties']['requirements']['maxItems'],3)
        proposal={'advisory_score':60,'summary':'Selected Python project evidence.',
                  'requirements':[{'quote':'Design Python data pipelines.','status':'supported','fact_ids':['project-python'],'reason':'A selected Python project is stated.'}],
                  'questions':['What production scale is required?']}
        with patch('model_providers.request_model',return_value=wrapped('openrouter',proposal)):
            session.send({'id':preview['id'],'sha256':preview['sha256'],'key':'synthetic','confirmed':True})
            session.entries[preview['id']]['thread'].join(3)
        result=session.status({'id':preview['id']});self.assertEqual(result['status'],'completed',result)
        saved=session.accept({'id':preview['id'],'proposal_sha256':result['proposal_sha256'],'reviewed':proposal,'confirmed':True})
        record,_,_=assessment.load(self.store,saved['id'])
        self.assertEqual(record['format'],'roleweave-job-assessment-v3');self.assertEqual(record['focus'],excerpt)
        with self.assertRaises(ValueError):session.preview(args|{'focus':'Not an exact part of this posting'})
        self.assertNotEqual(record['comparison_key'],assessment.comparison_key(record['profile_sha256'],record['fact_ids'],record['provider'],True,''))
        for kind in providers.KINDS:
            base=assessment.request_payload(job,self.profile['profile'],['project-python'],True,excerpt)
            converted=json.loads(providers.request_payload(base,config(kind)))
            budget=converted.get('max_output_tokens',converted.get('max_tokens',converted.get('options',{}).get('num_predict')))
            self.assertEqual(budget,8192)


if __name__=='__main__':unittest.main()
