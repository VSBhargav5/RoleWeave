"""Stable workspace launcher: current versioned package or current browser source."""
from pathlib import Path
import os
import subprocess
import sys

from runtime_paths import APP_VERSION,RESOURCE_ROOT,user_database_path


def launch_plan(root=RESOURCE_ROOT):
    root=Path(root)
    package=root/'out'/('portable-v'+APP_VERSION)/'RoleWeave'/'RoleWeave.exe'
    if package.is_file():return [str(package)],root
    for folder in ('.build-venv','.venv'):
        executable=root/folder/'Scripts'/'pythonw.exe'
        if executable.is_file():return [str(executable),str(root/'desktop.py'),'--db',str(user_database_path())],root
    return [sys.executable,str(root/'desktop.py'),'--db',str(user_database_path())],root


def main():
    command,root=launch_plan()
    subprocess.Popen(command,cwd=root,creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
