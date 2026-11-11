"""Build the portable Windows x64 app using an isolated, pinned build environment."""
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

from runtime_paths import APP_VERSION, RESOURCE_ROOT

BUNDLED_DISTRIBUTIONS = ("reportlab", "Pillow", "charset-normalizer", "google-auth-oauthlib", "google-auth",
                         "requests-oauthlib", "oauthlib", "requests", "urllib3", "certifi", "idna",
                         "cryptography", "cffi", "pycparser", "pyasn1", "pyasn1-modules")


def promote_package(staged, live):
    """Retain the previous complete app; roll back a failed promotion."""
    previous = live.parent / ("previous-" + uuid4().hex)
    existed = live.exists()
    if existed:
        os.replace(live, previous)
    try:
        os.replace(staged, live)
    except OSError:
        if existed:
            os.replace(previous, live)
        raise


def main():
    if sys.platform != "win32" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Build this Windows x64 package on an x64 Windows Python installation.")
    root = RESOURCE_ROOT
    output = root / "out"
    target = output / "portable"
    for path in (output, target, target / "RoleWeave"):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise SystemExit("Refusing linked build output directories")
        if not path.resolve().is_relative_to(root):
            raise SystemExit("Build output must remain inside this project")
    environment = os.environ.copy()
    output.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="build-", dir=output))
    environment["PYINSTALLER_CONFIG_DIR"] = str(output / "pyinstaller-cache")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--noupx",
               "--name", "RoleWeave", "--distpath", str(staging), "--workpath", str(output / "pyinstaller-work"),
               "--specpath", str(output / "pyinstaller-spec"), "--collect-data", "reportlab",
               "--collect-submodules", "reportlab.pdfbase", "--collect-data", "certifi",
               "--add-data", str(root / "examples") + os.pathsep + "examples", str(root / "desktop.py")]
    for distribution in BUNDLED_DISTRIBUTIONS:
        command.extend(["--copy-metadata", distribution])
    subprocess.run(command, cwd=root, env=environment, check=True)
    package = staging / "RoleWeave"
    for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(root / name, package / name)
    licenses = package / "licenses"
    licenses.mkdir(exist_ok=True)
    for name in BUNDLED_DISTRIBUTIONS:
        distribution = importlib.metadata.distribution(name)
        for item in distribution.files or []:
            if "license" in str(item).lower() or "copying" in str(item).lower():
                source = distribution.locate_file(item)
                if source.is_file():
                    shutil.copy2(source, licenses / (name + "-" + source.name))
    for relative in ("LICENSE.txt", "tcl/tcl8.6/license.terms", "tcl/tk8.6/license.terms"):
        source = Path(sys.base_prefix) / relative
        if source.is_file():
            shutil.copy2(source, licenses / (source.parent.name + "-" + source.name))
    staged_archive = shutil.make_archive(str(staging / "portable"), "zip", root_dir=staging, base_dir="RoleWeave")
    archive = output / f"RoleWeave-{APP_VERSION}-windows-x64.zip"
    os.replace(staged_archive, archive)
    target.mkdir(exist_ok=True)
    try:
        promote_package(package, target / "RoleWeave")
    except OSError as exc:
        raise SystemExit(f"Complete ZIP available at {archive}. Close the running app before promoting it; previous app preserved.") from exc
    print(f"Built {target / 'RoleWeave' / 'RoleWeave.exe'}")
    print(f"Portable ZIP: {archive}")


if __name__ == "__main__":
    main()
