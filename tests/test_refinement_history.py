import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import refinement_history as history
from tailoring_session import TailoringSession
from web_service import WebService, seed_web_demo
from workspace_bundle import export_bundle, restore_bundle, recovered_database


class RefinementHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);path=self.root/'jobs.db';seed_web_demo(path)
        self.service=WebService(path,demo=True);self.store=self.service.store
        from model_preferences import save_settings
        save_settings(self.store,{'kind':'openai','model':'gpt-4.1-mini','port':0})
        self.session=self.service.tailoring;self.addCleanup(self.session.shutdown)
        p=self.service.profile();self.job=self.store.list_jobs()[0]['id']
        self.args={'profile_id':p['id'],'profile_sha256':p['snapshot_sha256'],'job_id':self.job,
                   'fact_ids':['project-python'],'instruction':'Keep the synthetic project context.'}

    def complete(self,**changes):
        p=self.session.preview(self.args|changes)
        self.session.send({'id':p['id'],'sha256':p['sha256'],'key':'SYNTHETIC-CREDENTIAL-NEVER-STORE','confirmed':True})
        self.session.entries[p['id']]['thread'].join(3)
        result=self.session.status({'id':p['id']});self.assertEqual(result['status'],'completed')
        return p,result

    def test_opt_in_only_completed_turns_persist_and_credential_fields_never_do(self):
        preview=self.session.preview(self.args|{'retain_history':True})
        self.assertFalse(history.directory(self.store).exists())
        self.session.cancel({'id':preview['id']})
        p,result=self.complete();self.assertNotIn('history_id',result)
        self.assertFalse(history.directory(self.store).exists());self.session.cancel({'id':p['id']})
        p,result=self.complete(retain_history=True)
        record=history.load_turn(self.store,result['history_id'])
        text=(history.directory(self.store)/(record['id']+'.json')).read_text(encoding='utf-8')
        self.assertNotIn('SYNTHETIC-CREDENTIAL',text);self.assertNotIn('Synthetic Candidate',text)
        self.assertNotIn('Synthetic project exercise',text)
        self.assertEqual(record['payload'],p['payload']);self.assertTrue(record['offline_demo'])
        self.assertEqual(record['draft'],result['draft'])

    def test_revision_retains_edited_previous_and_parent_immutably(self):
        p,first=self.complete(retain_history=True);turn=first['history_id']
        old=(history.directory(self.store)/(turn+'.json')).read_bytes()
        previous=copy.deepcopy(first['draft']);previous['summary']['text']='User edited synthetic summary.'
        self.session.cancel({'id':p['id']})
        _,second=self.complete(retain_history=True,parent_id=turn,previous=previous,instruction='Shorter, with no invented metrics.')
        record=history.load_turn(self.store,second['history_id'])
        self.assertEqual(record['parent_id'],turn);self.assertEqual(record['conversation_id'],turn)
        self.assertEqual(record['previous'],previous);self.assertEqual((history.directory(self.store)/(turn+'.json')).read_bytes(),old)

    def test_reopen_after_new_session_makes_no_provider_call_and_requires_fresh_accuracy(self):
        _,result=self.complete(retain_history=True);other=TailoringSession(self.store,demo=False)
        self.addCleanup(other.shutdown)
        with patch('tailoring_session.propose',side_effect=AssertionError('No provider call')):
            reopened=other.reopen({'id':result['history_id'],'job_id':self.job})
        self.assertNotEqual(reopened['id'],result['id']);self.assertEqual(reopened['draft'],result['draft']);self.assertTrue(reopened['offline_demo'])
        args={'id':reopened['id'],'result_sha256':reopened['result_sha256'],'fact_edits':[],
              'fields':{'summary':'Human-reviewed restored wording.'},'confirmed':False}
        with self.assertRaisesRegex(ValueError,'confirm'):other.accept(args)
        old=self.store.active_profile()['id'];accepted=other.accept(args|{'confirmed':True})
        self.assertEqual(self.store.active_profile()['id'],old)
        self.assertNotEqual(accepted['profile']['id'],old)

    def test_parent_selection_and_exact_job_identity_fail_before_send(self):
        p,result=self.complete(retain_history=True);self.session.cancel({'id':p['id']})
        for change in ({'retain_history':False},{'previous':None},{'fact_ids':['skill-sql']}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.session.preview(self.args|{'retain_history':True,'parent_id':result['history_id'],'previous':result['draft']}|change)
        other=self.service.save_job({'title':'Other','company':'Fixture','market':'india_remote','posting':'Python.'})
        with self.assertRaisesRegex(ValueError,'another exact job'):
            self.session.reopen({'id':result['history_id'],'job_id':other['id']})
        with self.assertRaises(ValueError):self.session.preview(self.args|{'retain_history':'yes'})

    def test_history_storage_failure_keeps_valid_proposal_available_with_generic_warning(self):
        with patch('tailoring_session.refinement_history.save_turn',side_effect=OSError('PRIVATE disk details')):
            _,result=self.complete(retain_history=True)
        self.assertIn('history_warning',result);self.assertNotIn('history_id',result)
        self.assertNotIn('PRIVATE',json.dumps(result));self.assertTrue(result['draft'])
        self.session.accept({'id':result['id'],'result_sha256':result['result_sha256'],'fact_edits':[],
                             'fields':{'summary':'Human reviewed despite local storage failure.'},'confirmed':True})

    def test_corruption_missing_parent_cycle_and_path_traversal_fail_closed(self):
        p,first=self.complete(retain_history=True);self.session.cancel({'id':p['id']})
        _,second=self.complete(retain_history=True,parent_id=first['history_id'],previous=first['draft'])
        path=history.directory(self.store)/(second['history_id']+'.json');original=path.read_bytes();data=json.loads(original)
        data['draft']['summary']['text']='Changed without updating fingerprint';path.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'fingerprint'):history.load_turn(self.store,second['history_id'])
        path.write_bytes(original);root_path=history.directory(self.store)/(first['history_id']+'.json');root_path.unlink()
        with self.assertRaises(OSError):history.load_turn(self.store,second['history_id'])
        self.assertTrue(self.session.history({'job_id':self.job})['issues'])
        with self.assertRaises(ValueError):history.load_turn(self.store,'../outside')
        record=json.loads(original);record['parent_id']=record['id']
        with self.assertRaises(ValueError):history.snapshot(json.dumps(record).encode())
        with self.assertRaises((ValueError,KeyError,OSError)):export_bundle(self.store,self.service.artifacts)

    def test_recovery_preserves_complete_turn_graph_and_reopens_without_network(self):
        p,first=self.complete(retain_history=True);self.session.cancel({'id':p['id']})
        _,second=self.complete(retain_history=True,parent_id=first['history_id'],previous=first['draft'])
        before={p.name:p.read_bytes() for p in history.directory(self.store).iterdir()}
        bundle=export_bundle(self.store,self.service.artifacts)
        restored=restore_bundle(bundle,self.root/'recovered')
        other=WebService(recovered_database(self.root/'recovered',restored['id']),demo=True)
        self.assertEqual({p.name:p.read_bytes() for p in history.directory(other.store).iterdir()},before)
        reopened=other.tailoring.reopen({'id':second['history_id'],'job_id':self.job})
        self.assertEqual(reopened['draft'],second['draft']);self.assertEqual(other.tailoring.history({'job_id':self.job})['total'],2)

    def test_whole_conversation_removal_is_explicit_and_preserves_other_roots(self):
        p,first=self.complete(retain_history=True);self.session.cancel({'id':p['id']})
        p,second=self.complete(retain_history=True,parent_id=first['history_id'],previous=first['draft']);self.session.cancel({'id':p['id']})
        _,separate=self.complete(retain_history=True)
        args={'conversation_id':first['history_id'],'job_id':self.job,'confirmed':False}
        with self.assertRaises(ValueError):self.session.remove_history(args)
        self.assertEqual(self.session.history({'job_id':self.job})['total'],3)
        self.assertEqual(self.session.remove_history(args|{'confirmed':True}),{'removed':2})
        self.assertEqual(self.session.history({'job_id':self.job})['total'],1)
        history.load_turn(self.store,separate['history_id'])
        with self.assertRaises(OSError):history.load_turn(self.store,second['history_id'])

    def test_interrupted_removal_can_retry_without_missing_parent_dead_end(self):
        p,first=self.complete(retain_history=True);self.session.cancel({'id':p['id']})
        p,second=self.complete(retain_history=True,parent_id=first['history_id'],previous=first['draft']);self.session.cancel({'id':p['id']})
        _,third=self.complete(retain_history=True,parent_id=second['history_id'],previous=second['draft'])
        original_unlink=Path.unlink;count=0
        def interrupted(path,*args,**kwargs):
            nonlocal count
            count+=1
            if count==2:raise OSError('Synthetic interrupted deletion')
            return original_unlink(path,*args,**kwargs)
        args={'conversation_id':first['history_id'],'job_id':self.job,'confirmed':True}
        with patch.object(Path,'unlink',interrupted),self.assertRaises(OSError):self.session.remove_history(args)
        self.assertTrue((history.directory(self.store)/(first['history_id']+'.json')).exists())
        self.assertEqual(self.session.remove_history(args),{'removed':2})
        self.assertEqual(self.session.history({'job_id':self.job})['total'],0)

    def test_retained_cancellation_never_publishes_a_late_turn(self):
        import threading
        started=threading.Event();release=threading.Event()
        from ai_tailoring import synthetic_draft
        def slow(*args):started.set();release.wait(3);return synthetic_draft([self.service.profile()['profile']['facts'][0]])
        session=TailoringSession(self.store,demo=False);self.addCleanup(session.shutdown)
        with patch('tailoring_session.propose',side_effect=slow):
            p=session.preview(self.args|{'retain_history':True})
            session.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-not-a-key','confirmed':True})
            self.assertTrue(started.wait(1));session.cancel({'id':p['id']});release.set();session.entries[p['id']]['thread'].join(3)
        self.assertEqual(session.status({'id':p['id']})['status'],'cancelled')
        self.assertFalse(history.directory(self.store).exists())

    def test_history_pagination_and_overlong_paths_are_bounded(self):
        for i in range(21):
            p,_=self.complete(retain_history=True,instruction='Synthetic turn '+str(i));self.session.cancel({'id':p['id']})
        first=self.session.history({'job_id':self.job});second=self.session.history({'job_id':self.job,'offset':20})
        self.assertEqual(first['total'],21);self.assertEqual(len(first['items']),20);self.assertEqual(len(second['items']),1)
        for offset in (-1,1,True,1001):
            with self.assertRaises(ValueError):self.session.history({'job_id':self.job,'offset':offset})
        records={}
        for i in range(51):
            key=f'{i:032x}';parent=f'{i-1:032x}' if i else ''
            records[key]={'id':key,'parent_id':parent,'conversation_id':'0'*32,'job_id':'job','job_sha256':'a','profile_id':'p','profile_sha256':'b','fact_ids':['one']}
        with self.assertRaisesRegex(ValueError,'50-turn'):history.verify_chain(records[f'{50:032x}'],lambda i:records[i])
