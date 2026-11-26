import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import job_assessment as assessment
from model_preferences import save_settings
from web_service import WebService, seed_web_demo
from workspace_bundle import export_bundle, restore_bundle, recovered_database


class JobAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);path=self.root/'jobs.db';seed_web_demo(path)
        self.service=WebService(path,demo=True);self.addCleanup(self.service.assessment.shutdown)
        self.store=self.service.store;self.session=self.service.assessment
        from model_preferences import save_settings
        save_settings(self.store,{'kind':'openai','model':'gpt-4.1-mini','port':0})
        p=self.service.profile();self.job=self.service.save_job({'title':'Synthetic engineer','company':'Practice Co','market':'india_remote','posting':'Python required. SQL useful.'})
        self.args={'profile_id':p['id'],'profile_sha256':p['snapshot_sha256'],'job_id':self.job['id'],'fact_ids':['project-python']}
        self.facts=[p['profile']['facts'][0]]
        self.proposal={'advisory_score':60,'summary':'Synthetic advisory opinion, not a hiring probability.',
            'requirements':[{'quote':'Python required.','status':'supported','fact_ids':['project-python'],'reason':'Reviewed synthetic Python project; not production employment.'},
                            {'quote':'SQL useful.','status':'not_shown','fact_ids':[],'reason':'No selected SQL evidence; investigate rather than infer absence.'}],
            'questions':['What scope of SQL is needed?']}

    def complete(self,args=None):
        p=self.session.preview(args or self.args)
        self.session.send({'id':p['id'],'sha256':p['sha256'],'key':'SYNTHETIC-CREDENTIAL','confirmed':True})
        self.session.entries[p['id']]['thread'].join(3)
        result=self.session.status({'id':p['id']});self.assertEqual(result['status'],'completed')
        return p,result

    def save(self,args=None,score=60):
        p,result=self.complete(args);review=copy.deepcopy(result['proposal']);review['advisory_score']=score
        saved=self.session.accept({'id':p['id'],'proposal_sha256':result['proposal_sha256'],'reviewed':review,'confirmed':True})
        return saved

    def test_request_excludes_contacts_private_sources_unselected_facts_and_requires_reviewed_selection(self):
        profile=self.service.profile()['profile'];payload=assessment.request_payload(self.job,profile,['project-python'])
        self.assertNotIn(profile['email'].encode(),payload);self.assertNotIn(profile['name'].encode(),payload)
        self.assertNotIn(profile['facts'][0]['source'].encode(),payload)
        self.assertNotIn(profile['facts'][1]['claim'].encode(),payload)
        for ids in ([],['missing'],['project-python']*2):
            with self.assertRaises(ValueError):assessment.request_payload(self.job,profile,ids)
        profile['facts'][0]['reviewed']=False
        with self.assertRaises(ValueError):assessment.request_payload(self.job,profile,['project-python'])

    def test_contract_exact_quotes_selected_citations_bounded_opinion_and_deterministic_coverage(self):
        self.assertEqual(assessment.validate(self.proposal,self.job['posting'],self.facts),self.proposal)
        self.assertEqual(assessment.coverage(self.proposal),{'supported':1,'quoted':2,'percent':50})
        mutations=[('score',True),('score',101),('score',10.5),('quote','Invented quote'),('status','qualified'),('fact','invented'),('unsupported',None),('duplicate',None),('extra',None)]
        for kind,value in mutations:
            r=copy.deepcopy(self.proposal)
            if kind=='score':r['advisory_score']=value
            elif kind=='quote':r['requirements'][0]['quote']=value
            elif kind=='status':r['requirements'][0]['status']=value
            elif kind=='fact':r['requirements'][0]['fact_ids']=[value]
            elif kind=='unsupported':r['requirements'][0]['fact_ids']=[]
            elif kind=='duplicate':r['requirements'].append(copy.deepcopy(r['requirements'][0]))
            elif kind=='extra':r['eligible']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):assessment.validate(r,self.job['posting'],self.facts)
        self.assertIsNone(assessment.coverage(self.proposal|{'requirements':[]})['percent'])

    def test_preview_consent_one_shot_and_redacted_failure(self):
        session=assessment.AssessmentSession(self.store,demo=False);self.addCleanup(session.shutdown)
        with patch('job_assessment.providers.request_model',side_effect=RuntimeError('SECRET raw failure')) as provider:
            p=session.preview(self.args);provider.assert_not_called()
            for changes in ({'confirmed':False},{'sha256':'wrong'}):
                with self.assertRaises(ValueError):session.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key','confirmed':True}|changes)
            provider.assert_not_called();session.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key','confirmed':True});session.entries[p['id']]['thread'].join(3)
            self.assertEqual(session.status({'id':p['id']})['status'],'failed');self.assertNotIn('SECRET',json.dumps(session.status({'id':p['id']})))
            with self.assertRaises(ValueError):session.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key','confirmed':True})
            self.assertNotIn('key',session.entries[p['id']])

    def test_each_provider_structured_output_passes_the_same_assessment_validation(self):
        from test_model_providers import wrapped
        for kind in ('openai','anthropic','mistral','ollama','lmstudio'):
            config={'kind':kind,'model':'synthetic-model','port':11434 if kind in ('ollama','lmstudio') else 0}
            parsed=assessment.providers.structured_response(wrapped(kind,self.proposal),config)
            self.assertEqual(assessment.validate(parsed,self.job['posting'],self.facts),self.proposal)

    def test_review_saves_immutably_without_mutating_profile_stage_or_model_proposal(self):
        old_profile=self.service.profile();old_job=self.service.job(self.job['id']);p,result=self.complete()
        original=copy.deepcopy(result['proposal']);review=copy.deepcopy(original);review['advisory_score']=65;review['summary']='Human corrected synthetic opinion.'
        args={'id':p['id'],'proposal_sha256':result['proposal_sha256'],'reviewed':review,'confirmed':False}
        with self.assertRaises(ValueError):self.session.accept(args)
        args['confirmed']=True;saved=self.session.accept(args)
        self.assertEqual(self.session.accept(args),saved)
        r,_,_=assessment.load(self.store,saved['id']);self.assertEqual(r['proposal'],original);self.assertEqual(r['reviewed'],review)
        self.assertNotIn('SYNTHETIC-CREDENTIAL',json.dumps(r));self.assertEqual(self.service.profile(),old_profile)
        self.assertEqual(self.service.job(self.job['id'])['history'],old_job['history'])
        with self.assertRaises(ValueError):self.session.accept(args|{'proposal_sha256':'wrong'})

    def test_review_cannot_add_unproposed_quotes_or_omit_all_scoped_requirements(self):
        p,result=self.complete();args={'id':p['id'],'proposal_sha256':result['proposal_sha256'],'confirmed':True}
        for rows in ([],[{'quote':'SQL useful.','status':'uncertain','fact_ids':[],'reason':'Valid posting quote but outside this synthetic proposal.'}]):
            with self.assertRaises(ValueError):self.session.accept(args|{'reviewed':self.proposal|{'requirements':rows}})
        self.assertFalse(assessment.folder(self.store).exists())

    def test_rankings_use_only_latest_exact_review_and_identical_comparison_inputs_with_market_filters(self):
        first=self.save(score=70);second=self.save(score=40)
        other=self.service.save_job({'title':'Other practice role','company':'Practice Two','market':'relocation','posting':'Python required.'})
        third=self.save(self.args|{'job_id':other['id']},score=80)
        ranked=assessment.listing(self.store)
        self.assertEqual(ranked['total'],2);self.assertEqual([i['id'] for i in ranked['items']],[third['id'],second['id']])
        self.assertEqual(assessment.listing(self.store,market='india_remote')['total'],1)
        self.assertEqual(assessment.listing(self.store,job_id=self.job['id'])['total'],2)
        self.assertEqual(assessment.listing(self.store,job_id=self.job['id'])['items'][0]['id'],second['id'])
        save_settings(self.store,{'kind':'ollama','model':'another-model','port':11434})
        separate=self.save(score=99);all_data=assessment.listing(self.store)
        self.assertEqual(len(all_data['groups']),2)
        self.assertTrue(all(i['comparison_key']==all_data['group'] for i in all_data['items']))
        self.assertEqual(assessment.listing(self.store,group=separate['comparison_key'])['total'],1)
        self.assertNotEqual(first['comparison_key'],separate['comparison_key'])

    def test_recovery_replays_sources_and_preserves_original_reviewed_assessment_bytes(self):
        saved=self.save();path=assessment.folder(self.store)/(saved['id']+'.json');original=path.read_bytes()
        bundle=export_bundle(self.store,self.service.artifacts);restored=restore_bundle(bundle,self.root/'recovered')
        other=WebService(recovered_database(self.root/'recovered',restored['id']),demo=True)
        self.assertEqual((assessment.folder(other.store)/path.name).read_bytes(),original)
        self.assertEqual(other.assessment_load({'id':saved['id']})['record'],json.loads(original))
        data=json.loads(original);data['profile_sha256']='0'*64;path.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaises(ValueError):export_bundle(self.store,self.service.artifacts)
        self.assertTrue(assessment.listing(self.store)['issues'])

    def test_partial_file_publication_retry_is_idempotent_and_different_wording_is_refused(self):
        p,result=self.complete();args={'id':p['id'],'proposal_sha256':result['proposal_sha256'],'reviewed':result['proposal'],'confirmed':True}
        real_publish=assessment.publish_bytes
        def publish_then_fail(path,payload):real_publish(path,payload);raise OSError('Synthetic cleanup interruption after publication')
        with patch('job_assessment.publish_bytes',side_effect=publish_then_fail),self.assertRaises(OSError):self.session.accept(args)
        files=list(assessment.folder(self.store).iterdir());self.assertEqual(len(files),1);original=files[0].read_bytes()
        changed=copy.deepcopy(args);changed['reviewed']['advisory_score']=1
        with self.assertRaisesRegex(ValueError,'same reviewed'):self.session.accept(changed)
        saved=self.session.accept(args);self.assertEqual(saved['id'],files[0].stem)
        self.assertEqual(len(list(assessment.folder(self.store).iterdir())),1);self.assertEqual(files[0].read_bytes(),original)

    def test_structured_context_keeps_dates_but_excludes_reference_contact_fields(self):
        from test_career_entries import entry
        profile=self.service.profile()['profile'];profile['facts']=[entry('References',email='private-reference@example.invalid',phone='+1 555 0199',relationship='Synthetic project mentor')]
        payload=assessment.request_payload(self.job,profile,['references'])
        self.assertIn(b'Synthetic project mentor',payload);self.assertNotIn(b'private-reference@example.invalid',payload);self.assertNotIn(b'+1 555 0199',payload)
        profile['facts']=[entry('Experience',started='2025-01',current=True)]
        payload=assessment.request_payload(self.job,profile,['experience']);self.assertIn(b'2025-01',payload)
        self.assertNotIn(b'PRIVATE synthetic source',payload)

    def test_rehashed_request_with_wrong_source_context_is_rejected(self):
        saved=self.save();path=assessment.folder(self.store)/(saved['id']+'.json');r=json.loads(path.read_bytes())
        payload=json.loads(r['payload']);context=json.loads(payload['input'][0]['content']);context['facts'][0]['claim']='Unrelated invented candidate context'
        payload['input'][0]['content']=json.dumps(context);r['payload']=json.dumps(payload)
        r['request_sha256']=assessment.providers.request_fingerprint(r['payload'].encode(),r['provider'])
        path.write_text(json.dumps(r),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'exact source context'):assessment.load(self.store,saved['id'])
        with self.assertRaises(ValueError):export_bundle(self.store,self.service.artifacts)

    def test_legacy_openrouter_transport_options_reopen_without_rewriting_records(self):
        from job_store import JobStore
        save_settings(self.store,{'kind':'openrouter','model':'openrouter/free','port':0})
        for options in ({},{'compact':True},{'compact':True,'focus':''}):
            saved=self.save(self.args|options);path=assessment.folder(self.store)/(saved['id']+'.json')
            r=json.loads(path.read_bytes());wire=json.loads(r['payload'])
            wire.pop('reasoning');wire.pop('plugins')
            r['payload']=json.dumps(wire,ensure_ascii=False,indent=2)
            r['request_sha256']=assessment.providers.request_fingerprint(r['payload'].encode(),r['provider'])
            original=json.dumps(r,ensure_ascii=False,indent=2).encode();path.write_bytes(original)
            reopened=JobStore(self.store.path)
            record,_,_=assessment.load(reopened,saved['id'])
            self.assertEqual(record['payload'],r['payload'])
            self.assertIn(saved['id'],[item['id'] for item in assessment.listing(reopened,job_id=self.job['id'])['items']])
            self.assertEqual(path.read_bytes(),original)
            # The compatibility path cannot mask rehashed changes to the source,
            # instructions, schema, budget or partially changed transport options.
            for key,value in (('messages',[]),('max_tokens',1),('reasoning',{'effort':'high'}),('response_format',{})):
                altered=copy.deepcopy(r);payload=wire|{key:value}
                altered['payload']=json.dumps(payload,ensure_ascii=False,indent=2)
                altered['request_sha256']=assessment.providers.request_fingerprint(altered['payload'].encode(),altered['provider'])
                with self.subTest(options=options,key=key),self.assertRaisesRegex(ValueError,'exact source context'):
                    assessment.replay(reopened,json.dumps(altered).encode())

    def test_rate_limit_holds_assessment_and_tailoring_route_without_another_call(self):
        import time
        session=assessment.AssessmentSession(self.store,demo=False,cooldowns=self.service.tailoring.cooldowns,lock=self.service.tailoring.lock)
        self.addCleanup(session.shutdown)
        with patch('job_assessment.providers.request_model',side_effect=assessment.providers.ModelError('rate_limited',429,120)) as provider:
            p=session.preview(self.args);session.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key','confirmed':True})
            session.entries[p['id']]['thread'].join(3)
            failure=session.status({'id':p['id']});self.assertEqual(failure['retry_after'],120)
            self.assertIn('120 seconds',failure['error'])
            fresh=session.preview(self.args)
            with self.assertRaises(assessment.providers.ModelError) as caught:
                session.send({'id':fresh['id'],'sha256':fresh['sha256'],'key':'synthetic-key','confirmed':True})
            self.assertEqual(caught.exception.code,'cooldown');self.assertEqual(provider.call_count,1)
            self.assertIs(session.cooldowns,self.service.tailoring.cooldowns)
            tailoring=self.service.tailoring.preview(self.args|{'instruction':'Use the supplied facts.'})
            with self.assertRaises(assessment.providers.ModelError) as caught:
                self.service.tailoring.send({'id':tailoring['id'],'sha256':tailoring['sha256'],'key':'synthetic-key','confirmed':True})
            self.assertEqual(caught.exception.code,'cooldown')
            session.cooldowns[('openai','gpt-4.1-mini')]=time.monotonic()-1
            session.send({'id':fresh['id'],'sha256':fresh['sha256'],'key':'synthetic-key','confirmed':True})
            session.entries[fresh['id']]['thread'].join(3);self.assertEqual(provider.call_count,2)

    def test_cancel_drops_late_results_and_previews_expire(self):
        started=threading.Event();release=threading.Event();session=assessment.AssessmentSession(self.store,demo=False);self.addCleanup(session.shutdown)
        from test_model_providers import wrapped
        def slow(*args):started.set();release.wait(3);return wrapped('openai',self.proposal)
        with patch('job_assessment.providers.request_model',side_effect=slow):
            p=session.preview(self.args);session.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key','confirmed':True});self.assertTrue(started.wait(1));session.cancel({'id':p['id']});release.set();session.entries[p['id']]['thread'].join(3)
        self.assertEqual(session.status({'id':p['id']})['status'],'cancelled');self.assertFalse(assessment.folder(self.store).exists())
        session.entries[p['id']]['at']-=601
        with self.assertRaisesRegex(ValueError,'expired'):session.status({'id':p['id']})
