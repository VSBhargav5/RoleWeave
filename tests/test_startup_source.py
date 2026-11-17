import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import startup_source as hn
from provider_boards import parse_source, fetch_source, source_endpoint
from discovery_archive import archive_bytes, parse_archive, compare_observations
from network_io import request_bytes, Cancelled
from web_service import WebService
from workspace_bundle import export_bundle, restore_bundle, recovered_database, inspect_bundle


def job(identifier=1, **changes):
    return dict(id=identifier,type='job',title='Synthetic startup engineer',text='<p>Python &amp; SQL.</p>',time=1794873600,url='https://example.invalid/apply')|changes


def snapshot(records=None, token='jobs-0', ids=None):
    records=[job()] if records is None else records
    ids=ids if ids is not None else [r['id'] for r in records]
    return hn.snapshot(json.dumps(ids).encode(),[(i,json.dumps(r).encode()) for i,r in zip(ids,records)],token)


class StartupSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.service=WebService(self.root/'jobs.db',demo=True)
        self.addCleanup(self.service.boards.shutdown)

    def observed(self, raw=None):
        record=self.service.boards.replay(archive_bytes(parse_source(raw or snapshot(),'hackernews','jobs-0')))
        return self.service.boards.entry(record['id'])

    def imported(self, entry, company='Checked synthetic employer', market='india_remote'):
        page=self.service.boards.page(entry['id'])
        return self.service.boards.import_row(entry['id'],page['items'][0]['id'],company,market,entry['sha256'],True)

    def test_documented_fixed_endpoints_batch_grammar_and_explicit_public_boundary(self):
        self.assertEqual(source_endpoint('hackernews','jobs-0'),(hn.HOST,'/v0/jobstories.json'))
        for token in ('jobs-1','jobs-200','jobs-010','jobs--10','jobs-10?x=1','https://example.invalid'):
            with self.assertRaises(ValueError):source_endpoint('hackernews',token)
        for path in ('/v0/user/secret.json','/v0/item/0.json','/v0/item/1.json?x=1'):
            with self.assertRaises(ValueError):request_bytes(hn.HOST,path)
        with self.assertRaises(ValueError):request_bytes(hn.HOST,'/v0/jobstories.json',key='never')
        with self.assertRaises(ValueError):request_bytes(hn.HOST,'/v0/jobstories.json',body=b'never')

    def test_index_is_bounded_unique_positive_and_cannot_manufacture_item_coverage(self):
        for ids in (None,{},[True],[0],[1,1],list(range(1,202))):
            with self.assertRaises(ValueError):hn.index_ids(json.dumps(ids).encode())
        with self.assertRaises(ValueError):hn.parse_snapshot(snapshot(), 'jobs-10')
        with self.assertRaises(ValueError):hn.snapshot(b'[1,2]',[(1,json.dumps(job()).encode())],'jobs-0')
        self.assertEqual(hn.parse_snapshot(snapshot(records=[],ids=[]),'jobs-0')['jobs'],[])

    def test_byte_evidence_identity_order_hash_and_whole_batch_validation(self):
        raw=snapshot([job(1),job(2)]);data=json.loads(raw)
        for change in ('hash','order','missing','extra','format'):
            changed=copy.deepcopy(data)
            if change=='hash':changed['items'][0]['response']['sha256']='0'*64
            elif change=='order':changed['items'].reverse()
            elif change=='missing':changed['items'].pop()
            elif change=='extra':changed['unexpected']=True
            else:changed['format']='future'
            with self.assertRaises(ValueError):hn.parse_snapshot(json.dumps(changed).encode(),'jobs-0')
        self.assertEqual(hn.decoded(data['items'][0]['response'],hn.ITEM_LIMIT),json.dumps(job(1)).encode())
        with self.assertRaises(ValueError):hn.parse_snapshot(b'x'*(hn.SNAPSHOT_LIMIT+1),'jobs-0')

    def test_html_safe_plaintext_no_description_and_no_untrusted_destination_fetch(self):
        raw=snapshot([job(title='A &amp; B',text='<p>Python</p><script>evil()</script>',url='javascript:danger()'),job(2,text='')])
        feed=hn.parse_snapshot(raw,'jobs-0');self.assertEqual(feed['jobs'][0]['title'],'A & B')
        self.assertNotIn('evil()',feed['jobs'][0]['posting']);self.assertEqual(feed['jobs'][0]['url'],'https://news.ycombinator.com/item?id=1')
        self.assertIn('javascript:danger()',feed['jobs'][0]['posting'])
        self.assertIn('No description was returned',feed['jobs'][1]['posting'])
        self.assertIn('source notice only',feed['jobs'][1]['posting'])

    def test_removed_wrong_kind_bad_identity_or_oversized_notices_are_counted_without_truncation(self):
        records=[job(1,deleted=True),job(2,dead=True),job(3,type='comment'),job(4,text='x'*50001),job(5,time=True),job(6,dead=1)]
        feed=hn.parse_snapshot(snapshot(records),'jobs-0');self.assertEqual(feed['jobs'],[]);self.assertEqual(len(feed['excluded']),6)
        null=hn.snapshot(b'[1]',[(1,b'null')],'jobs-0');self.assertEqual(len(hn.parse_snapshot(null,'jobs-0')['excluded']),1)
        wrong=hn.snapshot(b'[1]',[(1,json.dumps(job(2)).encode())],'jobs-0');self.assertEqual(len(hn.parse_snapshot(wrong,'jobs-0')['excluded']),1)

    def test_fetch_reads_only_captured_numeric_items_with_one_shared_deadline(self):
        ids=list(range(1,23));responses=[json.dumps(ids).encode()]+[json.dumps(job(i)).encode() for i in ids[10:20]]
        cancel=threading.Event()
        with patch('startup_source.request_bytes',side_effect=responses) as request:
            feed=fetch_source('hackernews','jobs-10',cancel)
        self.assertEqual(len(feed['jobs']),10);self.assertEqual(request.call_count,11)
        self.assertEqual([c.args[:2] for c in request.call_args_list],[(hn.HOST,'/v0/jobstories.json')]+[(hn.HOST,'/v0/item/'+str(i)+'.json') for i in ids[10:20]])
        self.assertEqual(len({c.kwargs['deadline'] for c in request.call_args_list}),1)
        self.assertTrue(all(c.kwargs['cancel'] is cancel for c in request.call_args_list))
        self.assertTrue(feed['has_more_index'])

    def test_transport_failure_or_cancellation_never_accepts_a_partial_page(self):
        for error in (ValueError('synthetic connection failed'),Cancelled('cancelled')):
            with patch('startup_source.request_bytes',side_effect=[b'[1,2]',json.dumps(job(1)).encode(),error]) as request:
                with self.assertRaises(type(error)):hn.fetch_snapshot('jobs-0',threading.Event())
                self.assertEqual(request.call_count,3)

    def test_network_shared_deadline_refuses_before_connect_and_preserves_old_caller_defaults(self):
        for deadline in (True,float('nan'),float('inf'),time.monotonic()-1):
            with patch('network_io.http.client.HTTPSConnection') as connection:
                with self.assertRaises(ValueError):request_bytes(hn.HOST,'/v0/jobstories.json',deadline=deadline)
                connection.assert_not_called()
        response=Mock(status=200,length=0);response.getheader.return_value='application/json';response.read1.side_effect=[b'[]',b'']
        connection=Mock();connection.getresponse.return_value=response
        with patch('network_io.http.client.HTTPSConnection',return_value=connection):
            self.assertEqual(request_bytes(hn.HOST,'/v0/jobstories.json'),'[]'.encode())
        connection.request.assert_called_once();connection.close.assert_called_once()

    def test_synthetic_observation_explicit_consent_local_filters_and_archive_replay(self):
        with self.assertRaises(ValueError):self.service.boards.start('hackernews','jobs-0',False)
        record=self.service.boards.start('hackernews','jobs-0',True)
        entry=self.service.boards.entry(record['id']);entry['thread'].join(3)
        page=self.service.boards.page(entry['id'],query='Python',descriptions=True)
        self.assertEqual(page['total'],10);self.assertTrue(page['startup_scope']['synthetic']);self.assertEqual(page['startup_scope']['index_count'],22)
        self.assertEqual(self.service.boards.page(entry['id'],query='Python',descriptions=False)['total'],0)
        self.assertEqual(self.service.boards.page(entry['id'],exclude='Python',descriptions=True)['total'],0)
        feed=parse_archive(entry['archive']);self.assertEqual(feed['jobs'],entry['feed']['jobs'])

    def test_reviewed_import_exact_receipt_full_recovery_and_unchanged_dedupe(self):
        entry=self.observed();imported=self.imported(entry)
        with self.assertRaises(ValueError):self.service.boards.import_row(entry['id'],'hn-1','Unchecked','india_remote',entry['sha256'],False)
        with self.assertRaises(ValueError):self.service.boards.import_row(entry['id'],'hn-1','Checked','india_remote','0'*64,True)
        self.assertTrue(self.imported(entry)['already_saved'])
        raw=export_bundle(self.service.store,self.service.artifacts);parts,summary=inspect_bundle(raw)
        self.assertEqual(summary['artifacts']['board-imports'],1)
        result=restore_bundle(raw,self.root/'recovered');restored=WebService(recovered_database(self.root/'recovered',result['id']))
        self.assertEqual(restored.job(imported['id'])['posting'],self.service.job(imported['id'])['posting'])
        self.assertEqual(restored.store.list_jobs()[0]['source_url'],'https://news.ycombinator.com/item?id=1')

    def test_mutable_scores_do_not_create_reviews_but_changed_notice_and_market_do(self):
        first=self.imported(self.observed());self.service.track({'job_id':first['id'],'stage':'applied','note':'Synthetic only','follow_up':'','expected_revision':0})
        second=self.imported(self.observed(snapshot([job(score=99,unknown='extra')])));self.assertEqual(second['id'],first['id'])
        third=self.imported(self.observed(snapshot([job(text='Changed synthetic notice.')])));self.assertNotEqual(third['id'],first['id']);self.assertEqual(self.service.job(third['id'])['history'],[])
        self.service.boards.close(next(iter(self.service.boards.entries)))
        other=self.imported(self.observed(snapshot([job(text='Changed synthetic notice.')])),market='relocation');self.assertNotEqual(other['id'],third['id'])

    def test_receipt_tampering_and_missing_original_source_fail_recovery(self):
        entry=self.observed();saved=self.imported(entry)
        source=self.service.artifacts/'board-observations'/(entry['sha256']+'.json');source.unlink()
        with self.assertRaisesRegex(ValueError,'evidence'):export_bundle(self.service.store,self.service.artifacts)

    def test_cancelled_late_worker_cannot_publish_and_expired_session_cannot_import(self):
        service=WebService(self.root/'live-mocked.db',demo=False);self.addCleanup(service.boards.shutdown)
        entered=threading.Event();release=threading.Event()
        def delayed(*args):entered.set();release.wait(3);return parse_source(snapshot(),'hackernews','jobs-0')
        with patch('board_workspace.fetch_source',side_effect=delayed):
            item=service.boards.start('hackernews','jobs-0',True);entry=service.boards.entry(item['id']);self.assertTrue(entered.wait(3))
            service.boards.close(item['id']);release.set();entry['thread'].join(3)
        self.assertNotEqual(entry['status'],'ready');self.assertNotIn('archive',entry)
        observed=self.observed();observed['at']-=1201
        with self.assertRaises(ValueError):self.imported(observed)

    def test_transport_refuses_short_declared_body_even_when_json_prefix_is_valid(self):
        response=Mock(status=200,length=6);response.getheader.return_value='application/json';response.read1.side_effect=[b'[]',b'']
        connection=Mock();connection.getresponse.return_value=response
        with patch('network_io.http.client.HTTPSConnection',return_value=connection):
            with self.assertRaisesRegex(ValueError,'declared length'):
                request_bytes(hn.HOST,'/v0/jobstories.json')
        connection.close.assert_called_once()
