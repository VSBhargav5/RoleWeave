# Personal readiness workflow (v0.6)

This release adds local operational tools without connecting accounts, sending
applications or making paid calls. Existing snapshots and v3 backups remain.

## Find, organize and prepare

- Enable **Search posting text too** when a skill appears only in a description.
  Metadata-only search remains the default. **Order** sorts by age, title,
  company or follow-up date; undated reviews sort last in follow-up order.
- Use Ctrl+F for search, Ctrl+N for a new job and Ctrl+E for evidence review.
  New-job navigation keeps the existing unsaved-change confirmation.
- In **Career profile**, filter facts by claim/source/section. Load/update/remove
  acts on the original fact ID, not its filtered position. Import/export private
  profile JSON from the footer. Import clears every fact's review assertion and
  remains a guarded unsaved draft; it does not replace an existing saved version.
- **Resume studio** can restrict saved versions to the exact selected review.
  Uncheck the filter for general/other-review resumes. HTML, PDF and UTF-8 plain
  text exports use frozen selections; text does not include private source notes.
- **Review files → Open saved source posting** opens only a deliberately selected
  HTTPS URL, without embedded credentials. It does not verify the employer or
  submit anything. Unsaved source edits must be saved/discarded first.
- **Compare related saved versions** shows a JSON diff for exact source-URL
  matches, or title/company matches when URL is blank. Histories are never merged
  and later evidence does not inherit applied state.
- **Practise linked interview evidence** gives exact requirement cards, with
  deliberate reveal of linked claims/sources. Open requirements stay open; no
  claim generation, grading or learning-completion assertion occurs.

## Export and recover deliberately

Under **Evidence & next steps → Review files**:

- **Export this filtered review list** writes displayed metadata rows to CSV,
  excluding notes, career facts and resumes. Formula-like cells get an apostrophe
  prefix for spreadsheet safety. It is not a submitted-application count.
- **Export filtered active follow-ups** writes one ICS with the current dated,
  nonclosed observations for displayed review IDs. Import manually in a calendar;
  later date/stage changes do not synchronize with or remove existing events.
- **Inspect backup without restoring** validates the file in an isolated temporary
  shelf and reports review/profile/resume/history counts. The current DB is not
  modified. This validates contracts/hashes, not authenticity or external truth.
- **Check local database storage** opens SQLite read-only, runs quick_check and
  reports table counts. It does not validate every source hash or guarantee that
  a file can be recovered. Missing files are never created by this check.

AI's **Export request JSON** writes the exact posting-only request locally, with
no API key/authorization header. It never sends a request. Keep that file private.
Per-request review/consent and live-provider boundaries remain unchanged.

Exports stage complete bytes in the destination directory, flush, then publish
with an exclusive hard link. Existing files are never replaced. NTFS/POSIX hard
link support is required; unsupported filesystems fail closed. This prevents an
interrupted write from leaving a misleading completed export, but is not a
power-loss durability or encrypted-storage guarantee.

Portable builds now stage a fresh complete app and ZIP before promoting the app.
A failed promotion restores the prior complete app; a locked running app can
still block promotion. Close it and retry, or use the completed ZIP separately.
Previous build directories are retained under out/portable/previous-* for manual
recovery and can consume disk space. Do not delete your private database.

## One focused practice session

In a separate synthetic shelf (Getting started), spend 60–90 minutes searching a
posting-only keyword, changing ordering, importing a profile, reviewing a fact,
exporting a frozen text resume, comparing two review versions and rehearsing one
evidence card. Inspect a backup before restoring it elsewhere. Predict the
filtered CSV/calendar rows before opening the exports. Explain why these tools
preserve evidence history without proving that an application was sent.

Run `python -m unittest discover -s tests -v` and
`python desktop.py --self-test out/new-readiness-smoke` for offline verification.
Use a new output folder. Personal usefulness, live AI, calendar-client import,
remote account integrations, installer and unusual-display acceptance remain
unverified/pending. No learning, hiring, demand or revenue claim follows from
shipping this release.
