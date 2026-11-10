"""Compile the existing portable package with an explicitly supplied Inno Setup."""
import argparse
from pathlib import Path
import subprocess

from runtime_paths import APP_VERSION, RESOURCE_ROOT


def build_installer(compiler):
    compiler = Path(compiler)
    if not compiler.is_file():
        raise ValueError("Inno Setup compiler not found; supply its ISCC.exe path")
    package = RESOURCE_ROOT / "out" / "portable" / "RoleWeave"
    if not (package / "RoleWeave.exe").is_file():
        raise ValueError("Build the complete portable package with build_windows.py first")
    for required in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "_internal"):
        if not (package / required).exists():
            raise ValueError("Portable package is incomplete: " + required)
    output = RESOURCE_ROOT / "out" / f"RoleWeave-{APP_VERSION}-windows-x64-setup.exe"
    subprocess.run([str(compiler.resolve()), "/DAppVersion=" + APP_VERSION,
                    str(RESOURCE_ROOT / "installer.iss")], cwd=RESOURCE_ROOT, check=True)
    if not output.is_file():
        raise ValueError("Compiler completed without producing the expected installer")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", required=True, help="Explicit path to Inno Setup 6 ISCC.exe")
    options = parser.parse_args()
    print(build_installer(options.compiler))
