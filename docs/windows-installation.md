# Windows installation

The CI Windows artifact includes an unsigned per-user setup executable alongside
the existing portable ZIP. Extract the setup artifact, close RoleWeave and run
the setup executable. Windows may show publisher/reputation warnings because
code signing has not been established. Install only an artifact you trust.

Setup defaults to LOCALAPPDATA/Programs/RoleWeave, adds a Start-menu shortcut and
an Installed apps uninstall entry. It requests no administrator rights and does
not automatically launch the app or submit anything. Run RoleWeave from Start.

The installed app uses LOCALAPPDATA/RoleWeave/jobs.db, the same location as the
portable frozen app. Source launchers use the repository private/jobs.db instead.
Back up the source shelf and explicitly restore it in the installed app if needed;
installation does not migrate, overwrite or merge that separate source database.

To upgrade, back up the shelf, close the app, and run the newer setup. The stable
application ID lets Inno Setup update the same installation. Downgrade and
interrupted-upgrade recovery are not established; retain backups and the portable
ZIP. Use Installed apps to uninstall. Application-managed databases, practice
shelves and user exports are deliberately retained; uninstall does not erase
private data. File exports in other directories remain wherever you saved them.

## Reproduce delivery verification

Build on Windows x64 with the existing build requirements:
```powershell
python build_windows.py
python build_installer.py --compiler "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

The compiler is a separate build tool; these commands do not install it or alter
global credentials/settings. Official contract references:
[non-administrative installation](https://jrsoftware.org/ishelp/topic_admininstallmode.htm)
and [PrivilegesRequired](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm).

Windows CI compiles setup, silently installs into an isolated runner directory,
runs the installed synthetic self-test, reinstalls as an upgrade smoke, and
uninstalls. It checks that a synthetic marker at the standard data path survives.
This establishes that tested delivery path, not manual wizard acceptance,
code-signing reputation, interrupted upgrades or live AI usefulness.
