import copy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

from board_workspace import BoardWorkspace, imported_snapshot, parse_receipt
from discovery_archive import archive_bytes, parse_archive, compare_observations
from provider_boards import parse_source
from web_service import WebService
from workspace_bundle import export_bundle, inspect_bundle, restore_bundle, recovered_database
from test_provider_boards import lever_fixture


class BrowserBoardsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.service=WebService(self.root/'jobs.db');self.boards=self.service.boards;self.addCleanup(self.boards.shutdown)

    def feed(self,change=None):
        data=lever_fixture()
        if change:data[0].update(change)
        return parse_source(json.dumps(data).encode(),'lever','synthetic')

    def replay(self,feed=None):return self.boards.replay(archive_bytes(feed or self.feed()))['id']
    def save(self,identifier,**change):
        args={'identifier':identifier,'row_id':'synthetic-id','company':'Checked synthetic employer','market':'india_remote','digest':self.boards.ready(identifier)['sha256'],'confirmed':True};args.update(change)
        return self.boards.import_row(**args)

    def wait(self,identifier):
        self.boards.entries[identifier]['thread'].join(3);self.assertFalse(self.boards.entries[identifier]['thread'].is_alive())
        return next(e for e in self.boards.listing()['items'] if e['id']==identifier)

    def test_initialization_page_local_filters_and_archive_replay_do_not_fetch(self):
        with patch('board_workspace.fetch_source') as request:
            identifier=self.replay();self.assertEqual(self.boards.page(identifier)['total'],1)
            self.assertEqual(self.boards.page(identifier,query='data remote')['total'],1)
            self.assertEqual(self.boards.page(identifier,query='SQL')['total'],0)
            self.assertEqual(self.boards.page(identifier,query='SQL',descriptions=True)['total'],1)
            self.assertEqual(self.boards.page(identifier,exclude='engineer')['total'],0)
            self.assertEqual(self.boards.row(identifier,'synthetic-id')['title'],'Data Engineer');request.assert_not_called()
        self.assertEqual(self.service.store.list_jobs(),[])

    def test_explicit_one_get_and_failure_never_creates_partial_application(self):
        with patch('board_workspace.fetch_source',return_value=self.feed()) as request:
            with self.assertRaises(ValueError):self.boards.start('lever','synthetic',False)
            request.assert_not_called();identifier=self.boards.start('lever','synthetic',True)['id'];self.assertEqual(self.wait(identifier)['status'],'ready');self.assertEqual(request.call_count,1)
        self.boards.close(identifier)
        with patch('board_workspace.fetch_source',side_effect=ValueError('Sensitive upstream body')):
            identifier=self.boards.start('lever','synthetic',True)['id'];result=self.wait(identifier)
            self.assertEqual(result['status'],'failed');self.assertNotIn('Sensitive',result['error']);self.assertEqual(self.service.store.list_jobs(),[])

    def test_all_four_practice_providers_are_labelled_offline_fixtures(self):
        for provider in ('greenhouse','lever','lever-eu','ashby'):
            boards=BoardWorkspace(self.service.store,demo=True);self.addCleanup(boards.shutdown)
            with patch('board_workspace.fetch_source') as request:
                identifier=boards.start(provider,'synthetic',True)['id'];boards.entries[identifier]['thread'].join(3)
                self.assertEqual(boards.listing()['items'][0]['status'],'ready');self.assertIn('Synthetic',boards.page(identifier)['items'][0]['title']);request.assert_not_called()

    def test_cancel_blocks_late_success_and_overlapping_fetch(self):
        started=threading.Event();release=threading.Event();self.addCleanup(release.set)
        def fetch(*args):started.set();release.wait(3);return self.feed()
        with patch('board_workspace.fetch_source',side_effect=fetch):
            identifier=self.boards.start('lever','synthetic',True)['id'];self.assertTrue(started.wait(1))
            with self.assertRaises(ValueError):self.boards.start('lever','other',True)
            self.boards.close(identifier);release.set();self.wait(identifier)
            self.assertEqual(self.boards.entries[identifier]['status'],'cancelled');self.assertNotIn('feed',self.boards.entries[identifier])
            with self.assertRaises(ValueError):self.boards.page(identifier)

    def test_capacity_expiry_and_expired_close_are_explicit(self):
        identifiers=[self.replay() for _ in range(3)]
        with self.assertRaisesRegex(ValueError,'at most three'):self.replay()
        self.boards.entries[identifiers[0]]['at']-=1201
        with self.assertRaisesRegex(ValueError,'expired'):self.boards.page(identifiers[0])
        self.boards.close(identifiers[0]);self.assertEqual(len(self.boards.listing()['items']),2)
        self.assertTrue(self.replay())

    def test_invalid_actions_filters_urls_keys_and_unknown_rows_fail_closed(self):
        identifier=self.replay()
        for kwargs in ({'offset':1},{'offset':True},{'query':'x'*201},{'descriptions':'true'}):
            with self.assertRaises(ValueError):self.boards.page(identifier,**kwargs)
        for kwargs in ({'confirmed':False},{'digest':'x'*64},{'market':'unknown'},{'company':'bad\nlabel'}):
            with self.assertRaises(ValueError):self.save(identifier,**kwargs)
        with self.assertRaises(ValueError):self.boards.row(identifier,'missing')
        with self.assertRaises(ValueError):self.boards.start('lever','https://other.invalid',True)
        with self.assertRaises(ValueError):self.service.board_action({'action':'fetch','provider':'lever','token':'synthetic','confirmed':True,'key':'not accepted'})
        self.assertEqual(self.service.store.list_jobs(),[])

    def test_repeat_source_time_does_not_create_another_application_or_replace_first_evidence(self):
        identifier=self.replay();result=self.save(identifier);self.assertFalse(result['already_saved'])
        receipt=self.root/'web-artifacts/board-imports'/(result['id']+'.json');original=receipt.read_bytes()
        feed=self.feed();feed['fetched_at']='2027-01-01T00:00:00+00:00';second=self.replay(feed)
        repeated=self.save(second);self.assertEqual(repeated['id'],result['id']);self.assertTrue(repeated['already_saved'])
        self.assertEqual(len(self.service.store.list_jobs()),1);self.assertEqual(receipt.read_bytes(),original)
        self.assertEqual(self.service.store.application_history(result['id']),[])

    def test_changed_record_and_separate_market_get_independent_reviews(self):
        first=self.save(self.replay());second=self.save(self.replay(self.feed({'descriptionPlain':'Changed Python project work.'})))
        third=self.save(self.replay(),market='relocation')
        self.assertEqual(len({first['id'],second['id'],third['id']}),3)
        self.assertTrue(all(not self.service.store.application_history(i['id']) for i in (first,second,third)))

    def test_archive_download_is_exact_and_tampered_source_replay_rejected(self):
        raw=archive_bytes(self.feed());identifier=self.boards.replay(raw)['id'];self.assertEqual(self.boards.ready(identifier)['archive'],raw)
        changed=json.loads(raw);changed['source_sha256']='0'*64
        with self.assertRaises(ValueError):parse_archive(json.dumps(changed).encode())
        with self.assertRaises(ValueError):parse_archive(b'x'*(12*1024*1024+1))

    def test_managed_recovery_replays_receipt_source_posting_and_preserves_exact_bytes(self):
        identifier=self.replay();saved=self.save(identifier);bundle=export_bundle(self.service.store,self.root/'web-artifacts')
        parts,summary=inspect_bundle(bundle);self.assertEqual(summary['artifacts']['board-imports'],1)
        result=restore_bundle(bundle,self.root/'restored');store=WebService(recovered_database(self.root/'restored',result['id'])).store
        self.assertEqual(store.load(saved['id'])['snapshot'],self.service.store.load(saved['id'])['snapshot'])
        for name,value in parts.items():
            if name.startswith('web-artifacts/board-'):self.assertEqual((store.path.parent/name).read_bytes(),value)

    def test_missing_or_wrong_receipt_is_rejected_even_after_manifest_rehash(self):
        self.save(self.replay());bundle=export_bundle(self.service.store,self.root/'web-artifacts')
        for mode in ('missing','wrong'):
            with zipfile.ZipFile(BytesIO(bundle)) as z:parts={n:z.read(n) for n in z.namelist()}
            receipt=next(n for n in parts if n.startswith('web-artifacts/board-imports/'));manifest=json.loads(parts['manifest.json'])
            if mode=='missing':parts.pop(receipt);manifest['files'].pop(receipt)
            else:
                data=json.loads(parts[receipt]);data['row_id']='not-in-source';parts[receipt]=json.dumps(data).encode();manifest['files'][receipt]={'bytes':len(parts[receipt]),'sha256':hashlib.sha256(parts[receipt]).hexdigest()}
            parts['manifest.json']=json.dumps(manifest).encode();output=BytesIO()
            with zipfile.ZipFile(output,'w') as z:
                for name,value in parts.items():z.writestr(name,value)
            with self.assertRaises(ValueError):inspect_bundle(output.getvalue())

    def test_receipt_write_failure_can_retry_without_duplicate_review(self):
        from safe_export import publish_bytes
        identifier=self.replay();calls=0
        def publish(path,payload):
            nonlocal calls
            calls+=1
            if 'board-imports' in str(path):raise OSError('Synthetic receipt write failure')
            publish_bytes(path,payload)
        with patch('board_workspace.publish_bytes',side_effect=publish),self.assertRaises(OSError):self.save(identifier)
        self.assertEqual(len(self.service.store.list_jobs()),1)
        saved=self.save(identifier);self.assertTrue(saved['already_saved'])
        export_bundle(self.service.store,self.root/'web-artifacts')

    def test_evidence_link_revision_inherits_source_receipt_and_can_recover(self):
        from test_profile import synthetic_profile
        saved=self.save(self.replay());profile_id=self.service.store.save_profile(json.dumps(synthetic_profile()).encode());profile=self.service.store.load_profile(profile_id)
        result=self.service.review_from_profile({'job_id':saved['id'],'profile_id':profile_id,'profile_sha256':profile['snapshot_sha256'],'quote':'Build Python pipelines.','fact_ids':['project-python'],'confirmed':True})
        self.assertNotEqual(result['id'],saved['id']);self.assertEqual(self.service.store.application_history(result['id']),[])
        archive=export_bundle(self.service.store,self.root/'web-artifacts');parts,summary=inspect_bundle(archive)
        self.assertEqual(summary['artifacts']['board-imports'],2)
        old=parse_receipt(parts['web-artifacts/board-imports/'+saved['id']+'.json']);new=parse_receipt(parts['web-artifacts/board-imports/'+result['id']+'.json'])
        self.assertEqual(old['archive_sha256'],new['archive_sha256']);self.assertNotEqual(old['input_sha256'],new['input_sha256'])

    def test_revision_receipt_write_failure_retries_existing_review_safely(self):
        saved=self.save(self.replay());data=json.loads(self.service.store.load(saved['id'])['snapshot']);data['requirements']=[{'id':'new-requirement','quote':'Build Python pipelines.','fact_ids':[]}]
        args={'id':saved['id'],'review':data,'confirmed':True}
        with patch('board_workspace.publish_bytes',side_effect=OSError('Synthetic derived receipt failure')),self.assertRaises(OSError):self.service.save_review(args)
        self.assertEqual(len(self.service.store.list_jobs()),2)
        result=self.service.save_review(args);self.assertEqual(len(self.service.store.list_jobs()),2)
        export_bundle(self.service.store,self.root/'web-artifacts')

    def test_existing_oversized_receipt_is_refused_without_overwrite_or_duplicate(self):
        identifier=self.replay();saved=self.save(identifier);path=self.root/'web-artifacts/board-imports'/(saved['id']+'.json')
        oversized=b'x'*16385;path.write_bytes(oversized)
        with self.assertRaisesRegex(ValueError,'size limit'):self.save(identifier)
        self.assertEqual(path.read_bytes(),oversized);self.assertEqual(len(self.service.store.list_jobs()),1)

    def test_compare_different_boards_refused_and_absence_is_not_closed(self):
        before=self.feed();after=parse_source(b'[]','lever','synthetic')
        self.assertEqual(compare_observations(before,after)[0]['state'],'not_observed')
        after['token']='other'
        with self.assertRaises(ValueError):compare_observations(before,after)
        self.assertEqual(self.service.store.list_jobs(),[])
