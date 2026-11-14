import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from launch_roleweave import launch_plan
from runtime_paths import APP_VERSION,user_database_path


class SingleInterfaceTests(unittest.TestCase):
    def test_normal_practice_and_old_legacy_arguments_all_dispatch_to_browser(self):
        import desktop
        for flags,db,demo,port in (([],None,False,8765),(['--legacy'],None,False,8765),
                                   (['--demo'],None,True,8765),(['--legacy','--db','saved.db','--port','0'],Path('saved.db'),False,0)):
            with self.subTest(flags=flags),patch('sys.argv',['desktop.py',*flags,'--no-browser']),patch('desktop.tk.Tk') as native,patch('web_server.run_application',return_value=0) as browser:
                self.assertEqual(desktop.main(),0);browser.assert_called_once_with(db,demo,port,False);native.assert_not_called()

    def test_both_self_test_names_use_headless_browser_runtime(self):
        import desktop
        for flag in ('--self-test','--web-self-test'):
            with patch('sys.argv',['desktop.py',flag,'new-output']),patch('desktop.tk.Tk') as native,patch('web_selftest.run_web_self_test',return_value=True) as smoke:
                self.assertEqual(desktop.main(),0);smoke.assert_called_once_with(Path('new-output'));native.assert_not_called()

    def test_stable_launcher_ignores_stale_portable_and_uses_canonical_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=root/'out/portable/RoleWeave/RoleWeave.exe';old.parent.mkdir(parents=True);old.touch()
            python=root/'.build-venv/Scripts/pythonw.exe';python.parent.mkdir(parents=True);python.touch()
            with patch.dict(os.environ,{'LOCALAPPDATA':folder}):
                command,_=launch_plan(root)
                self.assertEqual(command,[str(python),str(root/'desktop.py'),'--db',str(user_database_path())])
            current=root/'out'/('portable-v'+APP_VERSION)/'RoleWeave/RoleWeave.exe';current.parent.mkdir(parents=True);current.touch()
            self.assertEqual(launch_plan(root)[0],[str(current)])
            self.assertTrue(old.exists())

    def test_retired_native_route_cannot_spawn_a_process(self):
        from web_server import LocalServer
        from web_service import WebService
        with tempfile.TemporaryDirectory() as folder:
            server=LocalServer(('127.0.0.1',0),WebService(Path(folder)/'jobs.db'));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                with patch('web_server.subprocess.Popen') as spawn:
                    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                    try:
                        connection.request('POST','/api/legacy',body='{"confirmed":true}',headers={'X-RoleWeave-Token':server.token,'Content-Type':'application/json'})
                        response=connection.getresponse();data=json.loads(response.read())
                        self.assertEqual(response.status,410);self.assertIn('retired',data['error']);spawn.assert_not_called()
                    finally:connection.close()
            finally:server.shutdown();server.server_close();worker.join(2)
