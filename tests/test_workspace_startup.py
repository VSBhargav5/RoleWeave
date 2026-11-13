import errno
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from runtime_paths import APP_VERSION
from web_server import find_workspace_host, run_application


class WorkspaceStartupTests(unittest.TestCase):
    def marker(self, **changes):
        return {'app':'roleweave-local-v1','version':APP_VERSION,
                'workspace':hashlib.sha256(str(Path('synthetic.db').resolve()).encode()).hexdigest()} | changes

    def connection(self, payload):
        connection=Mock()
        connection.getresponse.return_value.status=200
        connection.getresponse.return_value.read.return_value=json.dumps(payload).encode()
        return connection

    def test_old_invisible_host_does_not_hide_current_matching_host(self):
        connections=[]
        def create(_host, port, timeout):
            if port==8765:connection=self.connection(self.marker(version='0.17.0'))
            elif port==8766:connection=self.connection({'app':'unrelated'})
            elif port==8767:
                connection=Mock();connection.request.side_effect=ConnectionRefusedError()
            else:connection=self.connection(self.marker())
            connections.append(connection)
            return connection
        with patch('web_server.http.client.HTTPConnection',side_effect=create):
            running, available=find_workspace_host('synthetic.db',8765)
        self.assertEqual(running,8768)
        self.assertEqual(available,[8767])
        for connection in connections:connection.close.assert_called_once()

    def test_other_workspace_malformed_and_unresponsive_hosts_are_left_alone(self):
        for payload in [self.marker(workspace='different'), ['not','a','marker'], None]:
            with patch('web_server.http.client.HTTPConnection',return_value=self.connection(payload)):
                self.assertEqual(find_workspace_host('synthetic.db',10000),(None,[]))
        connection=Mock();connection.request.side_effect=TimeoutError()
        with patch('web_server.http.client.HTTPConnection',return_value=connection):
            self.assertEqual(find_workspace_host('synthetic.db',10000),(None,[10000]))

    def test_current_host_is_reopened_without_opening_database_or_second_server(self):
        with patch('web_server.find_workspace_host',return_value=(8768,[])), \
             patch('web_server.WebService') as service, patch('web_server.LocalServer') as server, \
             patch('web_server.webbrowser.open') as browser:
            self.assertEqual(run_application('synthetic.db'),0)
        browser.assert_called_once_with('http://127.0.0.1:8768')
        service.assert_not_called();server.assert_not_called()

    def test_bind_race_uses_free_port_without_killing_or_replacing_existing_host(self):
        server=Mock(origin='http://127.0.0.1:50000')
        with patch('web_server.find_workspace_host',return_value=(None,[8766])), \
             patch('web_server.WebService'),patch('web_server.LocalServer',side_effect=[OSError(errno.EADDRINUSE,'busy'),server]) as factory, \
             patch('web_server.webbrowser.open') as browser:
            self.assertEqual(run_application('synthetic.db'),0)
        self.assertEqual([c.args[0] for c in factory.call_args_list],[('127.0.0.1',8766),('127.0.0.1',0)])
        browser.assert_called_once_with(server.origin)
        server.server_close.assert_called_once()

    def test_storage_or_permission_errors_are_not_misrepresented_as_port_conflicts(self):
        with patch('web_server.find_workspace_host',return_value=(None,[8766])), \
             patch('web_server.WebService'),patch('web_server.LocalServer',side_effect=PermissionError(errno.EACCES,'denied')) as factory:
            with self.assertRaises(PermissionError):run_application('synthetic.db')
        self.assertEqual(factory.call_count,1)

