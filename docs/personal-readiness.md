# Personal-use readiness - v0.18.0

Current incremental workflow: [saved documents, search pages and safe follow-ups](continuing-applications.md).


Current default: [v0.18 browser workspace and reviewed filling](browser-workspace.md).
The older native workflows below remain under Settings → Open advanced tools.
Browser UI, role/location discovery and contact filling are implemented and
synthetically tested. Real helper installation, employer-form compatibility and
personal acceptance remain separate, unverified gates.


**The local MVP has 8/8 core workflow groups implemented and offline tested.**
That is implementation/verification scope, not an overall project percentage or
personal acceptance. You can start a controlled personal trial now. A fully
connected job-search assistant is not complete: optional live paths and account
integrations have separate gates below. More commits cannot complete those gates.

| Core workflow group | Implemented evidence | Remaining personal check |
| --- | --- | --- |
| Windows delivery | Portable and installed runtime plus install/reinstall/uninstall CI | Open the refreshed build; check dialogs/scaling on your display |
| Job review and separate markets | Immutable postings, exact requirement/evidence references, India/remote vs relocation filters | Review one permitted posting and confirm no eligibility inference |
| Career profiles | Reviewed sourced facts, reusable versions and deliberate transfer | Proofread every claim; distinguish project work from employment |
| Resume and letter preparation | Frozen HTML/PDF/TXT and reviewed letters | Visually proofread your own final exported documents |
| Application files | Private dossiers, verification and recipient-only documents | Inspect exactly what you will share; keep private sources/history private |
| Manual tracking | Stages, decisions, follow-ups, receipts and local mail excerpts | Record real observations yourself; no automatic sending/mailbox access |
| Rehearsal | Frozen source questions, answer/reflection drafts, local timer, packs, comparison | Practice and verify explanations; text/time changes do not prove learning |
| Recovery and integrity | V3 backup/restore, backup inspection, read-only shelf audit | Restore a copy into a separate practice shelf; preserve separate artifact files |

## What is only partly validated?

| Area | Current evidence | Remaining gate |
| --- | --- | --- |
| Public job discovery | Four provider subsets; live example results below | Board-dependent compatibility, unusual records and coverage |
| Optional AI quote proposals | Implemented; offline contract, consent/cancellation tests | One explicitly authorized synthetic live request using a key entered only in the app, then human quality review; API charges may apply |
| Calendar integration | Local `.ics` export plus explicit Google one-way follow-up sync implemented/offline tested | Desktop OAuth setup, scope consent and a synthetic live trial; see [Google Calendar guide](google-calendar.md) |
| Other connected accounts | Mailbox/general two-way account synchronization not implemented | Optional Google follow-up sync is the chosen narrow integration; no live account has been linked |

Global cross-site job search, automatic applications, employer outreach and
background account synchronization are not implemented. Manual source selection,
preparation and tracking are usable without them. No new account permissions,
personal transmission or paid model call was performed for this release.

## Live public-board evidence (11 November 2026)

One bounded, unauthenticated GET per documented example board using the app's
actual transport/parser, with no retries. [Metadata/hashes](evidence/public-boards-2026-11-11.json)
record the evidence without publishing employer posting bodies:

- Greenhouse `greenhouse`: parsed 19 observed postings.
- Lever global `lever`: parsed an empty list. This verifies the empty-response path, not populated global-record compatibility.
- Lever EU `lever`: parsed 6 observed postings.
- Ashby `Ashby`: 76 listed records were observed, but three descriptions were about357000 characters. The 50000-character posting contract rejected the whole board. No subset was imported or called complete. The improved error identifies the source row/length and suggests choosing another board or manually reviewing a permitted posting.

These are historical observations, not current job recommendations or complete-
board guarantees. Other employers can differ. The fail-closed limit protects
review/export bounds; broadening it or adding explicitly disclosed partial-board
support needs a separate design rather than silently dropping records.

Official contracts inspected for this check:
[Lever](https://github.com/lever/postings-api),
[Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api).
Existing source integrity and absence-is-not-closure limitations still apply.

## Start with the refreshed app

Extract the complete `RoleWeave-0.18.0-windows-x64.zip` and open
`RoleWeave/RoleWeave.exe`, keeping `_internal` beside it. The build is unsigned.
Choose **Getting started**, which now has scrollable First use, Readiness and
Data tabs. Opening it sends nothing and changes no shelf records. Its footer
stays visible at the supported minimum size. Use **Open separate synthetic
practice workspace** before entering personal information.

Source alternative, from this checkout with dependencies installed:

```powershell
python desktop.py --demo
python -m unittest discover -s tests -v
python desktop.py --self-test out/new-personal-readiness-smoke
```

Self-test output must use a new folder. Source and portable defaults use different
shelves; the guide shows the actual current database path. Back up and explicitly
restore if migrating. Full-shelf backups exclude separate journal, dossier,
letter, source-archive and exported files; keep private copies separately.

For one60-90minute acceptance session, use [the rehearsal workflow](rehearsal-workflow.md)
inside a separate synthetic shelf, then prepare one permitted posting/profile/
resume/application-history workflow and restore a backup into another separate
shelf. Record what failed or was confusing. Do not send a real application or
personal AI payload just to test the application. Learning/usefulness cannot be
marked complete without your trial.
