import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_installer import build_installer


class InstallerBuildTests(unittest.TestCase):
    def test_missing_compiler_never_dispatches(self):
        with tempfile.TemporaryDirectory() as name, patch("build_installer.subprocess.run") as run:
            with self.assertRaisesRegex(ValueError, "compiler not found"):
                build_installer(Path(name) / "ISCC.exe")
            run.assert_not_called()

    def test_incomplete_package_never_dispatches(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            compiler = root / "ISCC.exe"
            compiler.touch()
            with patch("build_installer.RESOURCE_ROOT", root), patch("build_installer.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "complete portable"):
                    build_installer(compiler)
                package = root / "out" / "portable" / "RoleWeave"
                package.mkdir(parents=True)
                (package / "RoleWeave.exe").touch()
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    build_installer(compiler)
                run.assert_not_called()
