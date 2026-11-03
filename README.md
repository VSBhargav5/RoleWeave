# RoleWeave

A personal Python job-search workspace for Data Engineering and applied AI roles.
Two separate markets: India/remote-from-India and international relocation.
Original implementation inspired by existing tools, with no upstream source,
assets or history imported. Local Windows workspace for posting review, selected
evidence, manual application tracking, follow-ups and preparation packs.

## Run today

Python 3.11+; no dependencies, API keys or server:

```powershell
python desktop.py
python roleweave.py examples/synthetic.json
python -m unittest discover -s tests -v
```

On Windows, open `Launch-RoleWeave.cmd` in File Explorer. Python 3.11+ with
Tkinter is required; no extra packages or credentials. If Tk is absent, enable
Tcl/Tk in your Python installation. The launcher keeps its console on failure.

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
backup. For a portable full copy, use **Back up full shelf** and **Restore shelf
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
private and outside public Git. The app makes no network calls or submissions.

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

See [research and phased plan](docs/research-and-plan.md). The next useful slice
is a user trial of saved postings and their reviewed evidence.
This is not yet a usable full job-search application or evidence of superiority.

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

Choose **Back up full shelf** on the left and use a new JSON filename. This
contains every snapshot, title, company, source URL, market, capture time and
application observation. New backups use `roleweave-backup-v2`. Older v1 backups
still restore without erasing newer tracking history. Older app versions cannot
read v2 backups.
Keep it private: it is not encrypted. Single-review export remains separate and
does not contain job metadata.

Choose **Restore shelf backup** in an empty or existing shelf. Source hashes,
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

Follow [the focused workflow exercise](docs/application-first-principles.md).
Manual posting capture, review, tracking, pack export and recovery are implemented.
A shared career profile, resume/PDF generation, permitted live source discovery,
AI assistance, external integrations and an installer remain pending. Personal
usefulness, manual dialog/layout interaction and real job-search outcomes remain
unverified. No feature count establishes superiority to another product.
