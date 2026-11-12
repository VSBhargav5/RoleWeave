# RoleWeave

A personal Python job-search workspace for Data Engineering and applied AI roles.
Two separate markets: India/remote-from-India and international relocation.
Original implementation inspired by existing tools, with no upstream source,
assets or history imported. Local Windows workspace for posting review, selected
evidence, manual application tracking, follow-ups and preparation packs.

See [v0.6 readiness tools and recovery](docs/readiness-workflow.md) for search,
ordering, private exports, evidence rehearsal and safer build/export publication.

## Release status

V0.14 is an unsigned Windows x64 **controlled beta**, not a verified production
release. The local workflows are implemented and offline tested; personal
acceptance, unusual display scaling, signing and optional live account/model
behavior remain gates. See [release acceptance](docs/release-acceptance.md) for
what must be verified before recommending general use.

## Start on Windows

[What is ready and what remains](docs/personal-readiness.md):8/8 core local workflow groups are implemented/offline tested; personal acceptance and optional live integrations have separate gates. Getting started now explains the current workflow and your actual data path.


Version0.14.0 includes reviewed cover letters, exact private application dossiers,
recipient-only document exports, manual submission receipts and local email
excerpt review. Source-bound records and conflict-safe tracking preserve prior
evidence. [Application delivery guide](docs/application-delivery.md).

Core features run locally. Optional AI requires your own session key and
per-request consent. Live quality, personal usefulness and connected-account
integrations remain unverified.

For the portable build, extract the **whole** `RoleWeave-0.14.0-windows-x64.zip`
and open `RoleWeave/RoleWeave.exe`. Keep its `_internal` directory beside it.
The build is unsigned. A per-user setup artifact is available; automatic updates are not provided.
The CI run's `RoleWeave-0.14.0-windows-x64` artifact contains this ZIP.

For source use, install Python 3.11+ with Tcl/Tk, run
`Setup-RoleWeave.cmd` once to install pinned dependencies in `.venv`, then open
`Launch-RoleWeave.cmd` in File Explorer. The launcher preserves the project's
existing `private/jobs.db`, including when a local portable build is present.
PDF export uses ReportLab; HTML and the other local workflows remain available
when that optional import is absent.

From PowerShell:

```powershell
python -m pip install -r requirements.txt
python desktop.py --demo
python desktop.py
python roleweave.py examples/synthetic.json
```

**Getting started** explains the workflow and opens a separate synthetic
practice workspace. `--demo` does the same without touching your real shelf.
Source mode defaults to `private/jobs.db`; a standalone portable executable
defaults to `%LOCALAPPDATA%/RoleWeave/jobs.db`. Use the full-shelf backup/restore
buttons when moving between them. `--db PATH` explicitly selects a database.

## Your first complete workflow

1. Open **Career profile**. Enter your contact details/summary and add facts
   with sources and a section (Experience, Projects, Education, Skills or
   Additional). Check review only for facts you have checked. Save a new version.
2. Choose **Add a job**, enter title/company/market in **Job details**, paste
   the description in **Job posting**, and save it. In **Review evidence**, copy
   reviewed career facts and explicitly link relevant ones to exact posting
   quotes. Copying alone never links or qualifies you.
3. Choose **Resume studio**. Select relevant reviewed claims, preview
   the exact text, confirm you reviewed it, then save a frozen version. No
   dates, employers, credentials, metrics or new wording are invented.
4. Under **Saved versions / export**, export to a new HTML/PDF filename and
   inspect it. Earlier resumes retain their exact bytes after profile edits.
   Source notes and unselected claims are excluded from the document. The
   private database/backup retains the source profile for traceability.
5. Record your application stage/notes and follow-up date manually. Export a
   preparation pack for the saved review. Back up the full shelf and rehearse
   restoring in a separate practice database.

Built-in PDFs use one text layout and bundled Vera fonts. Unsupported characters
fail explicitly: choose HTML-only and use your browser's print-to-PDF if suitable.
This is not a universal-script typesetting engine or an ATS compatibility claim.
Preview exports before sending them yourself. The app never submits applications.

## Save and reopen a job

1. Enter the job title, company, source URL if available, and choose its market.
2. Paste permitted posting text and choose **Save posting only**.
3. Select a saved job on the left to reopen it. Filter India/remote and
   relocation separately. Neither label verifies work authorization or sponsorship.
4. To import the existing evidence format, enter title/company first, then choose
   **Import review JSON**. The JSON's market is retained. Select the saved job to
   see requirement quotes and selected evidence alongside the posting.
5. Export a selected job's original JSON to a new filename. Existing files are
   refused. This exports review bytes, not title/company/URL or the whole shelf.

Storage defaults to ignored `private/jobs.db`; `python desktop.py --db PATH`
chooses another SQLite file. Close the app before copying this database as a
backup. For a portable full copy, use **Back up workspace** and **Restore shelf
backup**. These preserve job metadata as well as original review bytes. A synthetic
full restore including tracking history and repeat restore are covered by tests; personal recovery remains
unverified.

Every Save appends a snapshot. Exact duplicates with the same job details are
rejected. Editing a saved posting creates a new snapshot with no requirements or
evidence links; the original imported review is preserved. Use **Review evidence**
instead to edit quotes and links while keeping original snapshots.
Hash checks detect changed source bytes on reopen; they do not prove
truth, eligibility, completeness or authenticity against a malicious database edit.
The database and exports are plain text/SQLite without encryption: keep them
private and outside public Git. The core shelf is local. Only explicit discovery
and AI actions use the network; the app never submits applications.

The synthetic example links a Python requirement to a reviewed project claim
and leaves production Spark experience as an open review item. It never converts
a project's tests into employment experience. Edit a requirement quote: a quote
absent from the posting is rejected. Change `market` to `relocation`: that review
stays separate from the India market.

Inputs contain a posting, manually extracted requirements, career facts and
human-selected links. Output checks exact quotes, IDs and reviewed flags, and
includes byte-snapshot and posting hashes. A reviewed flag is a user's assertion,
not independent verification. A link does not prove relevance or qualification.
Unlinked requirements need review; they are not automatically missing skills.
No score, ATS prediction, hiring probability, automatic extraction or tailoring.

Keep private career files under ignored `private/`, outside public Git history.
The CLI only reads your explicit input and prints JSON to your terminal;
redirecting output can store private data. It makes no network/model calls and
does not submit applications or contact anyone. Input is bounded to 1 MiB.

See [the redesigned workspace guide](docs/workspace-design.md) and [research and phased plan](docs/research-and-plan.md). The next useful slice
is a user trial of saved postings and their reviewed evidence.
See [discovery, AI and calendar use](docs/connected-workflow.md). AI rewording,
email/account linking and automatic submissions are outside this release.
Calendar integration is a local file export, not synchronized account access.
No superiority claim is made.

## Review requirements and evidence

Select a saved job (or enter a new posting and job details), then choose
**Review evidence**. In the review window:

1. Select exact text in the posting and choose **Use selected posting text**,
   or paste an exact quote into the quote field.
2. Add a career/project claim and its source. Mark it reviewed only after checking
   it yourself. This checkbox is your assertion, not external verification.
3. Select the facts that relate to a requirement, then **Add requirement**, or
   select an existing requirement and **Update selected**. Unreviewed facts cannot
   be linked; leave a requirement unlinked when the evidence is still unknown.
4. **Save reviewed snapshot** appends a validated review. **Cancel** discards the
   draft. Quotes absent from the posting, unresolved form edits and invalid links
   block saving. Earlier snapshots and their original exports remain available.

To correct a fact, select exactly one in the fact list and choose **Load one fact**.
Review starts unchecked. Edit its claim/source, explicitly check review when
appropriate, then **Update loaded fact**. A changed claim/source or revoked review
removes all existing links to that fact; review and link it to requirements again.
Unchanged, still-reviewed facts retain their links. **Remove one fact** refuses
facts still referenced by requirements. Unlink them first. **Clear fact fields**
discards unapplied form edits; **Cancel** discards the whole draft. Changes only
reach the database through **Save reviewed snapshot**; originals remain intact.
No model inference, eligibility score or qualification claim is produced.

## Back up and recover the shelf

Choose **Back up workspace** on the left and use a new JSON filename. This
contains every snapshot, title, company, source URL, market, capture time and
application observation, career-profile versions, active profile and frozen resume
versions/documents. New backups use `roleweave-backup-v3`. Older v1/v2 backups
still restore without erasing newer data. Older app versions cannot read v3
backups. Restore into an existing shelf preserves its selected active profile;
an empty shelf adopts the backup's selection. Profile/resume ID conflicts roll
back the whole restore.
Keep it private: it is not encrypted. Single-review export remains separate and
does not contain job metadata.

Choose **Restore backup** in an empty or existing shelf. Source hashes,
review contracts, metadata, format version and timezone-aware timestamps are
checked before insertion. Existing identical jobs are skipped; an ID conflict
or divergent application-history revision rolls back the entire restore. Compatible
history extends existing records; earlier observations are never overwritten.
Existing jobs are never replaced. Backup/restore
inputs are limited to 64 MiB; each original review keeps its 1 MiB limit.
Review hashes do not authenticate metadata or prove that a backup is trustworthy.
Only restore files you intended to save. A failed backup write may leave a partial
file: discard it and retry with a new filename. Restore rejects malformed files.

Recovery exercise: save/import the synthetic review, back up the shelf, launch
`python desktop.py --db private/recovery-test.db`, restore and compare the job
details, market and exported original bytes. Restore twice and check that no
duplicate snapshots are added. Do not overwrite your working database to practise.

## Track decisions and follow-ups

Select a saved review and choose **Application notes / follow-up**. Record a
stage (`saved`, `shortlisted`, `applied`, `interview`, `offer`, `closed`, `withdrawn`),
a decision/observation note (up to 4000 characters), and an optional `YYYY-MM-DD`
follow-up date. Blank clears a previously set follow-up. Every record appends a
history revision; correcting a stage does not erase earlier observations. Any
stage may be recorded manually; the app does not verify or submit applications.

Tracking belongs to that exact saved snapshot. A later evidence revision starts
at `saved`, with separate history. It does not inherit `applied` or imply the
revised claims were submitted. Grouping versions into a single application is a
later design decision; do not double-count these snapshots as unique applications.

Use the left-side market and stage filters together. Search title, company,
source URL or the latest decision note (Unicode case-insensitive, literal text).
Search does not inspect full posting text or older notes. **Follow-ups due today
or earlier** uses the computer's local calendar date, sorts oldest dates first,
and excludes `closed` and `withdrawn`. No email/calendar linking or background
notifications are implemented.

## Prepare an application or interview

Choose **Export preparation pack** for a saved review. The UTF-8 `.txt` file
includes job metadata, exact requirement quotes, linked reviewed claims copied
without rewriting, open review questions, source hashes, and manual history at
its stated revision. Unselected facts are excluded. It is a preparation record,
not a generated resume, cover letter, submitted application or eligibility claim.
Keep it private: it contains any recorded notes and is not encrypted. Existing
filenames are refused, and pack size is limited to 8 MiB before file creation.

Posting edits must be saved or discarded before tracking/exporting a saved
review. Switching jobs, New posting and closing the app guard unsaved posting
changes. **Reload saved review** discards form changes only after confirmation.
Closing the evidence or tracker window also warns about pending edits; the
explicit Cancel/discard action still discards its draft. Full-shelf backups only
include saved data, not unsaved form edits.

Follow [the resume and recovery exercise](docs/resume-first-principles.md).
Manual posting capture, evidence review, tracking, preparation packs, reusable
profile versions, reviewed HTML/PDF resumes and v3 recovery are implemented.
One public source adapter, optional AI requirement-quote assistance and calendar
file export are available. Broader source coverage, email/account integrations and
manual installer acceptance remain pending. Personal usefulness, live AI quality, real outcomes
and complete manual file-dialog coverage remain unverified.

## Reproduce the checks / build

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python desktop.py --self-test out/source-smoke
```

The self-test requires a new output directory and uses only synthetic data.
On Windows x64, install `requirements-build.txt` in a separate Python 3.12
environment, then run `python build_windows.py`. Build output stays under `out/`.
CI tests Python 3.11/3.12 on Windows/Linux (native UI checks run on Windows),
builds the portable app and runs its synthetic profile/resume/recovery self-test.
Neither tests nor a package build establish personal usefulness or ATS behavior.

Windows per-user setup and uninstall: [installation guide](docs/windows-installation.md).

V0.7 expands discovery to Lever global/EU and Ashby, with local filters and verified offline observation archives. [Discovery guide and exercise](docs/discovery-workflow.md).

See [application delivery and local correspondence](docs/application-delivery.md) for exact private dossiers and recipient-only files.

[Employer watchlists](docs/employer-watchlists.md) save explicit board choices and local filters. [Selected-board collections](docs/selected-collections.md) now provide deliberate Windows preview/import, private offline archives/comparisons, shortlist CSV and failed-source-only retries.

[V0.9 selected-collection workflow](docs/selected-collections.md) covers partial-source failures, retained observation ages and scoped comparisons.

[V0.10 private rehearsal journals](docs/rehearsal-workflow.md) add source-bound answer/reflection drafts, explicit local time, selected evidence packs and exact-source version differences without scoring learning.

[Read-only shelf audit](docs/shelf-audit.md) checks saved source fingerprints and cross-references beyond SQLite structure, without changing the shelf.

[Google Calendar follow-up sync](docs/google-calendar.md) is an optional, explicitly reviewed one-way integration with app-created-calendar scope and session-only browser consent. It is offline tested; your Desktop OAuth setup and synthetic live acceptance are still required.

[V0.12 workspace design](docs/workspace-design.md): richer role/company rows, manual-stage badges, collapsible filters, stronger review/evidence hierarchy and a shared indigo visual theme. Existing workflows, draft guards and private data contracts remain supported.

### Dark workspace in v0.13

Near-black surfaces, violet/cyan accents, rounded controls, gradient weave artwork
and structured evidence cards replace the previous light presentation. Large
reviews use 20-card pages and explicitly copy the complete review text. See
[workspace design](docs/workspace-design.md) for behavior and verification.

### Safer startup in v0.14

Startup recognizes the supported shelf format before initializing tables. Known
legacy shelves are adopted in one transaction; foreign, altered or newer schemas
are refused. Existing compatible shelves are reopened without header rewrites.
Do not edit schema markers to bypass refusal or replace the original database.
Unexpected UI callback failures display a private, non-persistent error code;
review saved state before repeating an interrupted action.
