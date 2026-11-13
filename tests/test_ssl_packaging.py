from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from build_windows import ssl_runtime_assets


class SSLPackagingTests(unittest.TestCase):
    def test_runtime_policy_sidecar_is_retained_when_present(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('build_windows.ssl.__file__', str(root/'ssl.py')):
                self.assertEqual(ssl_runtime_assets(), [])
                policy=root/'codex-rejected-cas.pem'
                policy.write_bytes(b'Synthetic packaging fixture, not a certificate.')
                self.assertEqual(ssl_runtime_assets(), [policy])

