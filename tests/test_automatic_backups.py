from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from automatic_backups import AutomaticBackups, cycle, KEY, KEEP
from web_service import WebService, seed_web_demo
from workspace_bundle import inspect_bundle, restore_bundle, recovered_database

NOW = datetime(2026, 11, 17, 2, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))


class AutomaticBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'jobs.db'
        seed_web_demo(self.path)
        self.service = WebService(self.path, demo=True)
        self.manager = self.service.automatic_backups
        def stop_manager():
            self.manager.shutdown()
            if self.manager.thread:self.manager.thread.join(5)
        self.addCleanup(stop_manager)

    def enable(self, enabled=True):
        return self.manager.configure(dict(enabled=enabled, expected_revision=self.manager.state()['revision'], confirmed=True))

    def test_disabled_default_does_not_create_files_or_change_shelf(self):
        before = self.path.read_bytes()
        self.assertFalse(self.manager.perform(NOW, scheduled=True))
        self.assertFalse(self.manager.directory.exists())
        self.assertEqual(before, self.path.read_bytes())
        self.assertFalse(self.service.bootstrap()['automatic_backups']['enabled'])

    def test_consent_exact_schema_and_stale_preference_guards(self):
        for data in ({'enabled':True,'expected_revision':0,'confirmed':False}, {'enabled':1,'expected_revision':0,'confirmed':True}, {'enabled':True,'expected_revision':0,'confirmed':True,'path':'elsewhere'}):
            with self.assertRaises(ValueError): self.manager.configure(data)
        self.enable()
        with self.assertRaisesRegex(ValueError,'changed'): self.manager.configure(dict(enabled=False,expected_revision=0,confirmed=True))
        self.assertTrue(self.manager.state()['enabled'])

    def test_local_two_am_cycle_boundary_catchup_and_restart_idempotency(self):
        self.enable()
        self.assertEqual(cycle(NOW-timedelta(seconds=1)), '2026-11-16')
        self.assertEqual(cycle(NOW), '2026-11-17')
        self.assertTrue(self.manager.perform(NOW-timedelta(seconds=1), scheduled=True))
        restarted = AutomaticBackups(self.service.store,self.service.artifacts)
        self.assertFalse(restarted.perform(NOW-timedelta(seconds=1), scheduled=True))
        # The previous catch-up is within the failure/admission cooldown; next run follows later.
        self.assertFalse(restarted.perform(NOW,scheduled=True))
        self.assertTrue(restarted.perform(NOW+timedelta(minutes=15),scheduled=True))
        self.assertEqual(len(restarted.files()),2)
        self.assertFalse(restarted.perform(NOW+timedelta(hours=8),scheduled=True))
        self.assertTrue(restarted.perform(NOW+timedelta(days=3,hours=10),scheduled=True))
        self.assertEqual(len(restarted.files()),3, 'No burst of one snapshot per missed day')
        with self.assertRaises(ValueError):cycle(datetime(2026,11,17))

    def test_complete_snapshot_preview_restore_preserves_original_and_disables_restored_policy(self):
        self.enable(); self.assertTrue(self.manager.perform(NOW))
        item = self.manager.files()[0]; payload=self.manager.payload(item['id'])
        self.assertEqual(hashlib.sha256(payload).hexdigest(),item['sha256'])
        preview=self.service.preview_automatic_backup({'id':item['id']})
        before=self.path.read_bytes()
        result=self.service.restore_recovery({'id':preview['id'],'sha256':preview['summary']['sha256'],'confirmed':True})
        restored=WebService(recovered_database(self.path.parent/'recovered',result['id']))
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(restored.profile(),self.service.profile())
        self.assertEqual(len(restored.store.list_jobs()),len(self.service.store.list_jobs()))
        self.assertFalse(restored.automatic_backups.state()['enabled'])
        parts,_=inspect_bundle(payload)
        self.assertFalse(any('automatic-backups' in name for name in parts), 'No recursive backup archive')

    def test_retention_keeps_seven_only_after_verified_new_publication(self):
        self.enable()
        for day in range(10):self.assertTrue(self.manager.perform(NOW+timedelta(days=day)))
        files=self.manager.files();self.assertEqual(len(files),KEEP)
        self.assertEqual({f['cycle'] for f in files},{(NOW+timedelta(days=d)).date().isoformat() for d in range(3,10)})
        for item in files:self.manager.payload(item['id'])
        self.enable(False);self.assertFalse(self.manager.perform(NOW+timedelta(days=11)))
        self.assertEqual(files,self.manager.files())

    def test_failure_keeps_prior_snapshots_and_waits_fifteen_minutes(self):
        self.enable();self.assertTrue(self.manager.perform(NOW));before=self.manager.files()
        with patch('automatic_backups.export_bundle',side_effect=ValueError('private detail')) as capture:
            self.assertFalse(self.manager.perform(NOW+timedelta(days=1),scheduled=True))
            self.assertFalse(self.manager.perform(NOW+timedelta(days=1,minutes=14),scheduled=True))
            self.assertEqual(capture.call_count,1)
        self.assertEqual(before,self.manager.files())
        self.assertNotIn('private detail',str(self.manager.status()))
        self.assertEqual(self.manager.state()['last_error'],'capture_failed')
        self.assertTrue(self.manager.perform(NOW+timedelta(days=1,minutes=15),scheduled=True))

    def test_failed_publication_or_readback_never_prunes_old_backups(self):
        self.enable()
        for day in range(KEEP):self.assertTrue(self.manager.perform(NOW+timedelta(days=day)))
        before=self.manager.files()
        with patch('automatic_backups.publish_bytes',side_effect=OSError('disk full')):
            self.assertFalse(self.manager.perform(NOW+timedelta(days=KEEP)))
        self.assertEqual(before,self.manager.files())
        self.assertEqual(self.manager.state()['last_error'],'storage_failed')
        real=self.manager.payload
        with patch.object(self.manager,'payload',side_effect=lambda name: real(name) if name in {r['id'] for r in before} else (_ for _ in ()).throw(ValueError('bad readback'))):
            self.assertFalse(self.manager.perform(NOW+timedelta(days=KEEP)))
        self.assertTrue(all((self.manager.directory/r['id']).exists() for r in before))
        self.assertEqual(len(self.manager.files()),KEEP+1)

    def test_corrupt_or_unexpected_files_and_traversal_fail_without_deleting(self):
        self.enable();self.assertTrue(self.manager.perform(NOW));item=self.manager.files()[0]
        path=self.manager.directory/item['id'];path.write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError,'fingerprint'):self.manager.payload(item['id'])
        self.assertFalse(self.manager.perform(NOW+timedelta(days=1)))
        self.assertEqual(path.read_bytes(),b'bad')
        with self.assertRaises(ValueError):self.manager.payload('../jobs.db')
        marker=self.manager.directory/'personal.txt';marker.write_text('keep')
        self.assertTrue(self.manager.status()['storage_error'])
        self.assertFalse(self.manager.perform(NOW+timedelta(days=2)))
        self.enable(False)
        self.assertFalse(self.manager.state()['enabled'])
        self.assertEqual(marker.read_text(),'keep')

    def test_disable_and_shutdown_during_capture_drop_unpublished_snapshot(self):
        from automatic_backups import export_bundle
        for shutdown in (False,True):
            self.enable();entered=threading.Event();release=threading.Event()
            def capture(*args):
                entered.set();self.assertTrue(release.wait(3));return export_bundle(*args)
            with patch('automatic_backups.export_bundle',side_effect=capture):
                thread=threading.Thread(target=self.manager.perform,args=(NOW,));thread.start();self.assertTrue(entered.wait(3))
                self.assertFalse(self.manager.perform(NOW))
                if shutdown:self.manager.shutdown()
                else:self.enable(False)
                release.set();thread.join(5);self.assertFalse(thread.is_alive())
            self.assertFalse(self.manager.running);self.assertEqual(self.manager.files(),[])

    def test_corrupt_policy_does_not_hide_main_workspace_or_get_repaired_silently(self):
        with closing(sqlite3.connect(self.path)) as db, db:db.execute('INSERT INTO app_settings VALUES (?,?)',(KEY,'{"invalid":true}'))
        self.assertFalse(self.service.bootstrap()['automatic_backups']['available'])
        self.assertTrue(self.service.store.list_jobs())
        self.assertFalse(self.manager.perform(NOW))
        with self.assertRaises(ValueError):self.manager.configure(dict(enabled=True,expected_revision=0,confirmed=True))
        with closing(sqlite3.connect(self.path)) as db, db:self.assertEqual(db.execute('SELECT value FROM app_settings WHERE key=?',(KEY,)).fetchone()[0],'{"invalid":true}')

    def test_clock_rollback_manual_snapshot_is_retained_without_regressing_cycle(self):
        self.enable()
        for day in range(KEEP):self.assertTrue(self.manager.perform(NOW+timedelta(days=day)))
        self.assertTrue(self.manager.perform(NOW-timedelta(days=1)))
        self.assertEqual(len(self.manager.files()),KEEP)
        self.assertIn('2026-11-16',{f['cycle'] for f in self.manager.files()})
        self.assertEqual(self.manager.state()['last_cycle'],'2026-11-23')

    def test_scheduler_wakes_and_stops_without_an_operating_system_task(self):
        self.enable();self.manager.start()
        deadline=time.monotonic()+5
        while not self.manager.files() and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(self.manager.files());self.manager.shutdown();self.manager.thread.join(3)
        self.assertFalse(self.manager.thread.is_alive())

    def test_manual_request_is_explicit_and_asynchronous(self):
        with self.assertRaises(ValueError):self.manager.request({'confirmed':True})
        self.enable()
        with self.assertRaises(ValueError):self.manager.request({'confirmed':False})
        with self.assertRaises(ValueError):self.manager.request({'confirmed':1})
        self.manager.request({'confirmed':True})
        deadline=time.monotonic()+5
        while self.manager.running and time.monotonic()<deadline:time.sleep(.02)
        self.assertFalse(self.manager.running);self.assertEqual(len(self.manager.files()),1)

    def test_retention_failure_keeps_new_verified_snapshot_and_does_not_retry_same_cycle(self):
        self.enable()
        for day in range(KEEP):self.assertTrue(self.manager.perform(NOW+timedelta(days=day)))
        real=Path.unlink
        old={self.manager.directory/r['id'] for r in self.manager.files()}
        def locked(path,*args,**kwargs):
            if path in old:raise PermissionError('synthetic locked older snapshot')
            return real(path,*args,**kwargs)
        with patch.object(Path,'unlink',locked):
            self.assertFalse(self.manager.perform(NOW+timedelta(days=KEEP)))
        self.assertEqual(self.manager.state()['last_error'],'retention_failed')
        self.assertEqual(self.manager.state()['last_cycle'],'2026-11-24')
        self.assertFalse(self.manager.perform(NOW+timedelta(days=KEEP,hours=1),scheduled=True))
        self.assertEqual(len(self.manager.files()),KEEP+1)
        for item in self.manager.files():self.manager.payload(item['id'])

    def test_authenticated_download_preserves_exact_snapshot_and_rejects_extra_or_invalid_paths(self):
        import http.client
        from web_server import LocalServer
        self.enable();self.assertTrue(self.manager.perform(NOW));item=self.manager.files()[0]
        server=LocalServer(('127.0.0.1',0),self.service)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            def get(query, authorized=True):
                connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                try:
                    headers={'X-RoleWeave-Token':server.token} if authorized else {}
                    connection.request('GET','/api/automatic-backups/download?'+query,headers=headers)
                    response=connection.getresponse();return response.status,response.read()
                finally:connection.close()
            status,payload=get('id='+item['id']);self.assertEqual(status,200);self.assertEqual(payload,self.manager.payload(item['id']))
            self.assertEqual(get('id='+item['id'],False)[0],401)
            self.assertEqual(get('id=../jobs.db')[0],400)
            self.assertEqual(get('id='+item['id']+'&extra=1')[0],400)
        finally:
            server.shutdown();server.server_close();worker.join(3)

    def test_status_waits_for_publication_instead_of_treating_staging_as_corrupt_storage(self):
        from safe_export import publish_bytes
        self.enable();entered=threading.Event();release=threading.Event();seen=threading.Event();observed=[]
        def staged(destination,payload):
            marker=destination.parent/'.roleweave-synthetic-stage'
            marker.write_bytes(b'in progress');entered.set()
            try:
                if not release.wait(5):raise TimeoutError('synthetic interleaving timeout')
            finally:marker.unlink()
            publish_bytes(destination,payload)
        with patch('automatic_backups.publish_bytes',side_effect=staged):
            writer=threading.Thread(target=self.manager.perform,args=(NOW,));writer.start()
            try:
                self.assertTrue(entered.wait(5))
                def status():observed.append(self.manager.status());seen.set()
                reader=threading.Thread(target=status);reader.start()
                self.assertFalse(seen.wait(.05),'Status must not expose an in-progress temporary file')
            finally:release.set();writer.join(5)
            reader.join(5)
        self.assertTrue(seen.is_set());self.assertFalse(observed[0]['storage_error']);self.assertEqual(len(observed[0]['items']),1)
