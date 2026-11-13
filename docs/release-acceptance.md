# Release acceptance — v0.18 controlled beta

v0.18.1 fixes the locally built Windows runtime's missing SSL policy asset.
Source-only public-search checks did not establish packaged search functionality.
The offline frozen web smoke now creates a hostname-verified, certificate-required
HTTPS context; explicit live packaged search is separately available with
`--search-check NEW_OUTPUT_FOLDER`. No TLS validation is disabled.


Current incremental workflow: [saved documents, search pages and safe follow-ups](continuing-applications.md).


Current default: [v0.18 browser workspace and reviewed filling](browser-workspace.md).
The older native workflows below remain under Settings → Open advanced tools.
Browser UI, role/location discovery and contact filling are implemented and
synthetically tested. Real helper installation, employer-form compatibility and
personal acceptance remain separate, unverified gates.


RoleWeave is a local Windows x64 application. Its implemented workflows are not
proof of production reliability, personal usefulness, hiring outcomes or live
integration compatibility. This release is unsigned and suitable for a controlled
trial with synthetic data before private use. No automatic update service exists.

## Agreed v1 scope

On 12 November the owner chose **local Windows v1 first**. V1 covers the eight
local workflow groups in personal-readiness.md. Google Calendar and AI remain
optional preview integrations; their live trials are not local-v1 blockers and
they must not be advertised as production-validated. Global discovery, automatic
applications and general account synchronization are outside this release scope.

Local v1 acceptance focuses on first launch, reviewed local records/documents,
manual tracking, explicit exports and recovery. Signing/distribution and
interrupted-upgrade confidence are tracked separately below. The beta label
remains until the agreed local acceptance evidence exists.

## Verified release gates

- Offline tests cover exact evidence, documents, tracking, guarded exports,
  recovery and provider/Google/AI contracts.
- CI exercises Python 3.11/3.12 on Windows/Linux; native UI runs on Windows.
- Portable and installed runtime smoke tests use separate synthetic shelves.
  Installer lifecycle checks repeat installation and preserve a data marker on
  uninstall. These are automated checks, not a human wizard/scaling trial.
- Startup supports the documented unversioned legacy declarations and the
  current marked format. A database with unknown tables/views/triggers/custom
  indexes, altered constraints or a newer/foreign marker is refused before DDL.
  This intentionally rejects custom schemas; it does not repair corruption.
- Legacy adoption is transactional. Current marked shelves require all five
  known tables; opening them does not rewrite schema markers.
- Unexpected Tk callback failures show RW-UI-001 without exception text,
  tracebacks, automatic retry, logging or transmission. Some work may already
  have committed: inspect saved state before repeating an action. Startup errors
  exit nonzero. This is not recovery from process termination or power loss.

## Acceptance still required

| Gate | Verification | State |
| --- | --- | --- |
| Clean Windows first use | Extract complete package or install as ordinary user; check launch, text, menus, keyboard and dialogs at your scaling | Pending human trial |
| Private workflow | Use a permitted profile/posting, proofread exact resume/letter, review recipient-only files and manual tracking | Pending human trial |
| Recovery drill | Back up; restore into a separate shelf; compare profiles, resumes and history; separately preserve journals/archives/exports | Automated synthetic checks; human drill pending |
| Signing and distribution | Choose signing identity, verify signed installer/package on clean Windows, publish a deliberate versioned release | Unsigned; no signing identity configured |
| Google follow-ups | User-owned Desktop OAuth setup, consent and synthetic create/read/update/ETag conflict trial | Optional preview, excluded from local v1; no live account linked |
| Optional AI | One explicitly consented synthetic request, human quote-quality review and error/cancel observation | Optional preview, excluded from local v1; paid trial not authorized |
| Wider provider compatibility | Test permitted boards and large/unusual records without silent partial import | Limited historical samples only |
| Interrupted upgrade | Terminate/restart installer in an isolated Windows test environment and verify old data/build recovery | Pending; ordinary lifecycle CI is not this test |

No account linking, Cloud project/billing changes, personal transmission, paid
calls, application submission or third-party outreach is part of release testing
without the required user authorization. Missing live credentials must not be
obtained from files, environment variables or another app connection.

## Safe first-use drill

1. Extract the entire ZIP, keeping `_internal` beside the executable. Source
   users can run `python desktop.py --demo`. Start in the separate synthetic
   practice workspace and confirm the title identifies it.
2. Inspect both markets, exact quotes and their sources. Filter/collapse/reset;
   make a draft and confirm navigation guards preserve it.
3. Freeze synthetic documents, inspect recipient-only files and manually record
   a stage/follow-up. Nothing should be submitted or sent automatically.
4. Export a backup and restore into a separate shelf. Keep separate artifact
   files privately; a shelf backup excludes them.
5. Only after the drill, deliberately choose the personal shelf. Source/portable
   defaults differ; Getting started/Data shows the actual current path. Never
   rename/overwrite the only copy of an incompatible or damaged database.

Run verification from the repository using installed dependencies:

```powershell
python -m unittest discover -s tests -v
python desktop.py --self-test out/new-release-smoke
python build_windows.py
```

Self-test output must be a new directory. CI supplies the installer compiler;
local builds require the explicitly selected Inno Setup compiler. No live
integration calls belong in the offline suite.

## Support and rollback

Record the application version, fixed error code and synthetic reproduction
steps. Remove private filenames, job/profile contents, keys, tokens and accounts
before sharing anything. There is no automatic telemetry or crash upload.
For database refusal, preserve the file and use the matching app version or
restore a verified backup into a separate shelf. Header identity is a format
marker, not authenticity or protection against an attacker editing the file.
Before an upgrade, back up the shelf and preserve separate exports; do not assume
older builds will support future formats. A previous build directory retained by
the local builder is not a database backup. Do not delete private data to repair
installation. Uninstall preserves local user data.

SQLite references for the implementation:
[application and version pragmas](https://www.sqlite.org/pragma.html),
[transaction behavior](https://www.sqlite.org/lang_transaction.html).

## Verify a downloaded build

Download the portable/setup artifact and release-evidence artifact from the
same successful CI run. Compare the relevant file hash with SHA256SUMS.txt:

```powershell
Get-FileHash -LiteralPath .\RoleWeave-0.18.1-windows-x64.zip -Algorithm SHA256
```

A matching hash detects a changed download relative to that run. It does not
replace code signing, authenticate an arbitrary copied checksum file or establish
that software is safe. Do not mix versions or different CI runs. A mismatch
means do not open the download; obtain it again from the intended successful run.
