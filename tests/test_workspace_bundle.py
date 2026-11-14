import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from web_service import WebService,seed_web_demo
from workspace_bundle import export_bundle,inspect_bundle,restore_bundle,recovered_database


class WorkspaceBundleTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.path=self.root/'main/jobs.db';seed_web_demo(self.path)
        self.service=WebService(self.path)
        profile=self.service.profile();self.job=self.service.store.list_jobs()[0]
        self.resume=self.service.resume({'job_id':self.job['id'],'profile_id':profile['id'],
                                         'profile_sha256':profile['snapshot_sha256'],'fact_ids':['project-python'],'confirmed':True},freeze=True)
        self.letter=self.service.letter({'job_id':self.job['id'],'resume_id':self.resume['id'],'fact_ids':['project-python'],
                                        'motivation':'Synthetic introduction.','closing':'Thank you.','confirmed':True})
        self.packet=self.service.packet({'job_id':self.job['id'],'resume_id':self.resume['id'],'letter_id':self.letter['id'],
                                        'formats':['pdf','letter'],'confirmed':True})
        preview=self.service.preview_resume_import({'name':'source.txt','base64':base64.b64encode(b'Synthetic original resume.').decode()})
        self.service.commit_resume_import({'id':preview['id'],'selected':[{'id':'1','section':'Projects'}],'confirmed':True})

    def test_complete_managed_round_trip_into_new_workspace_preserves_active_one(self):
        before=self.path.read_bytes();payload=self.service.workspace_bundle()
        parts,summary=inspect_bundle(payload)
        self.assertEqual(summary['artifacts'],{'letters':1,'packets':1,'resume-imports':1})
        result=restore_bundle(payload,self.root/'recovered')
        recovered=WebService(recovered_database(self.root/'recovered',result['id']))
        self.assertEqual(recovered.get_letter(self.letter['id'])['text'],self.letter['text'])
        self.assertEqual(recovered.download('packet',self.packet['id'])[0],self.service.download('packet',self.packet['id'])[0])
        self.assertEqual(recovered.profile(),self.service.profile())
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(len(recovered.store.list_jobs()),len(self.service.store.list_jobs()))
        again=restore_bundle(payload,self.root/'recovered')
        self.assertNotEqual(again['id'],result['id'])

    @unittest.skipUnless(os.name=='nt','Windows legacy path boundary')
    def test_deep_windows_recovery_fails_before_creating_output(self):
        parent=self.root/('deep-'+90*'x')/'recovered'
        payload=self.service.workspace_bundle()
        with self.assertRaisesRegex(ValueError,'shorter workspace path'):
            restore_bundle(payload,parent)
        self.assertFalse(parent.exists())
        self.assertTrue(self.service.store.list_jobs())

    def test_tampered_and_traversal_bundles_fail_before_persistent_output(self):
        payload=self.service.workspace_bundle()
        for changed in ('shelf.json','../outside','web-artifacts/letters/../../outside'):
            output=BytesIO()
            with zipfile.ZipFile(BytesIO(payload)) as source,zipfile.ZipFile(output,'w') as archive:
                for info in source.infolist():archive.writestr(info.filename,b'tampered' if info.filename==changed else source.read(info))
                if changed!='shelf.json':archive.writestr(changed,b'outside')
            destination=self.root/'must-not-exist'
            with self.assertRaises(ValueError):restore_bundle(output.getvalue(),destination)
            self.assertFalse(destination.exists())

    def test_corrupt_or_unknown_managed_files_are_not_silently_omitted(self):
        path=self.service.artifacts/'resume-imports'/(hashlib.sha256(b'Synthetic original resume.').hexdigest()+'.txt')
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'fingerprint'):self.service.workspace_bundle()
        path.write_bytes(b'Synthetic original resume.')
        (self.service.artifacts/'unexpected.txt').write_bytes(b'preserve me')
        with self.assertRaisesRegex(ValueError,'Unsupported'):self.service.workspace_bundle()
        self.assertTrue((self.service.artifacts/'unexpected.txt').exists())

    def test_changed_database_during_capture_refuses_inconsistent_bundle(self):
        with patch('workspace_bundle.shelf_bytes',side_effect=[b'first',b'second']):
            with self.assertRaisesRegex(ValueError,'changed during backup'):self.service.workspace_bundle()

    def test_interruption_never_publishes_completed_recovery(self):
        from safe_export import publish_bytes
        payload=self.service.workspace_bundle();parent=self.root/'recovered'
        def fail_marker(path,data):
            if Path(path).name=='RECOVERY.json':raise OSError('Synthetic disk failure')
            publish_bytes(path,data)
        with patch('workspace_bundle.publish_bytes',side_effect=fail_marker):
            with self.assertRaises(OSError):restore_bundle(payload,parent)
        self.assertTrue(all(p.name.startswith('.stage-') for p in parent.iterdir()))
        self.assertFalse(list(parent.glob('*/RECOVERY.json')))
        with self.assertRaises(ValueError):recovered_database(parent,'../outside')

    def test_recovery_preview_must_be_confirmed_and_bound_to_the_same_bytes(self):
        payload=self.service.workspace_bundle();preview=self.service.preview_recovery(payload)
        args={'id':preview['id'],'sha256':preview['summary']['sha256'],'confirmed':True}
        for changes in ({'confirmed':False},{'sha256':'wrong'},{'id':'other'}):
            with self.assertRaises(ValueError):self.service.restore_recovery(args|changes)
        result=self.service.restore_recovery(args)
        self.assertTrue(self.service.recovery_database({'id':result['id'],'confirmed':True}).is_file())
        with self.assertRaises(ValueError):self.service.restore_recovery(args)
