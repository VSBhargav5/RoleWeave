# One RoleWeave interface — v0.22

The supported app interface is the browser workspace. Double-click
`Launch-RoleWeave.cmd` in the source repository, or `RoleWeave.exe` inside the
complete `out/portable-v0.48.0/RoleWeave` folder. Keep the whole package together.
The repository launcher selects the exact current versioned build, never a stale
`out/portable` copy; without that build it starts current browser source.

The old interface could reappear from the advanced-tools button, an older
launcher, or native regression tests. The button is removed, its endpoint refuses
launch with HTTP 410, and even the historical `--legacy` argument opens the
browser. Startup failures show an error rather than falling back to native UI.
Both runtime smoke commands now exercise the browser API without a native window.

Already-running old windows and old executables cannot change themselves. Save
any drafts and close those windows once. Replace shortcuts that point to an old
version with the stable repository launcher or the current complete package.
No process is killed and no stored workspace is deleted by this change.

## Where your data stays

The stable launcher and Windows package use `%LOCALAPPDATA%/RoleWeave/jobs.db`.
Direct developer use of `python desktop.py` retains `private/jobs.db`; explicit
`--db` paths, offline practice and recovered workspaces remain supported. Existing
databases are neither moved nor merged automatically. To open an older source
workspace in the browser, use `python desktop.py --db private/jobs.db`. Check
Settings for the actual workspace location before importing or restoring data.

V0.23 adds [browser interview rehearsal](browser-rehearsal.md): selected source
questions, private answer versions and managed recovery. Earlier rehearsal
comparison/import/timer/pack screens remain unmigrated.

The browser supports discovery, saved applications, profile/import, documents,
reviewed AI drafts, contact helper and recovery. Employer boards and interview
rehearsal were subsequently migrated. V0.38 adds browser local correspondence
review, calendar-file export and optional Google follow-ups; see the
[current workflow](browser-follow-ups.md). Audits and additional rehearsal tools
remain unmigrated. Existing records and backups remain intact.

## Reproduce the checks

```powershell
python -m unittest discover -s tests -p test_single_interface.py -v
python -m unittest discover -s tests -p test_desktop_errors.py -v
python desktop.py --self-test out/new-browser-smoke
```

Use a fresh output directory. Checks use synthetic data and no external account.
The default test suite skips archived native GUI tests. CI explicitly enables
`ROLEWEAVE_TEST_NATIVE_ARCHIVE=1` on its isolated runners to retain historical
regression coverage; do not enable that flag during ordinary local development.
Browser end-to-end checks remain part of the normal release verification.

Tradeoff: retiring the fallback gives one consistent interface, while native-only
capabilities need migration before they can be offered again. It preserves the
existing backend and data rather than silently rewriting or copying workspaces.


## Publishing local builds and GitHub changes

The repository root `Launch-RoleWeave.cmd` resolves the current version from
`runtime_paths.APP_VERSION`. Rebuilding does not change already open browser tabs
or old host processes: save work, use Settings -> Quit in that workspace, then
reopen the root launcher to enter the current host.

`build_windows.py --versioned` stages a separately named build for testing. After
validation, `build_windows.py` also refreshes the historical stable
`out/portable/RoleWeave/RoleWeave.exe` path, retaining the previous complete folder.
Do not copy only an EXE into an older package; bundled assets must update with it.
The CI upload, installer and hash paths read APP_VERSION rather than hardcoding
an older release. Local builds are not Git commits or published GitHub releases;
source changes need a pushed branch/PR, while packaged artifacts are produced by
CI. A PR does not update main until it is merged.
