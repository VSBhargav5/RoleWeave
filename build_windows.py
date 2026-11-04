"""Build the portable Windows x64 app using an isolated, pinned build environment."""
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from runtime_paths import APP_VERSION, RESOURCE_ROOT


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
    environment["PYINSTALLER_CONFIG_DIR"] = str(output / "pyinstaller-cache")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--noupx",
               "--name", "RoleWeave", "--distpath", str(target), "--workpath", str(output / "pyinstaller-work"),
               "--specpath", str(output / "pyinstaller-spec"), "--collect-data", "reportlab",
               "--collect-submodules", "reportlab.pdfbase", "--copy-metadata", "reportlab",
               "--copy-metadata", "Pillow", "--copy-metadata", "charset-normalizer",
               "--add-data", str(root / "examples") + os.pathsep + "examples", str(root / "desktop.py")]
    subprocess.run(command, cwd=root, env=environment, check=True)
    package = target / "RoleWeave"
    for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(root / name, package / name)
    licenses = package / "licenses"
    licenses.mkdir(exist_ok=True)
    for name in ("reportlab", "Pillow", "charset-normalizer"):
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
    archive = shutil.make_archive(str(output / f"RoleWeave-{APP_VERSION}-windows-x64"), "zip", root_dir=target, base_dir="RoleWeave")
    print(f"Built {package / 'RoleWeave.exe'}")
    print(f"Portable ZIP: {archive}")


if __name__ == "__main__":
    main()
