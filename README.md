# RoleWeave

The stable repository entry point is **Launch-RoleWeave.cmd** in this folder.
It selects the current versioned build. Save work and use Settings → Quit in an
older workspace before reopening; an already open tab keeps its running version.
[Launcher paths and build publication](docs/single-interface.md#publishing-local-builds-and-github-changes).

## Retained assessments and answer capture (v0.50)

Saved assessments from before the OpenRouter transport-option change reopen
without rewriting their requests. Compatibility recognizes that exact older
wire format; source bindings, fingerprints, schema and reviewed evidence remain
verified. Assessment and tailoring share a local route cooldown after HTTP 429,
respect Retry-After (60 seconds when absent), and require a fresh authorized send.
Provider quotas still apply; there is no automatic retry or paid fallback.

Helper v0.7 opens a focused answer editor with save controls and acknowledgement
visible in a short companion window. **Save and next** advances detected questions
without rescanning, or opens a blank question after the queue ends. **Done** returns
to the form review. Re-scan after saving to propose answers for filling. Duplicate
questions in the same scope are directed to the existing library entry. Answers
remain local and can be exported as JSON; saving never fills the employer form.

## Embedded application forms (v0.49)

Helper v0.6 discovers visible application frames and requests optional access to
the exact embedded site. It binds field reviews to their actual document/frame,
preflights selected fields before writing and verifies values are retained. It
supports open shadow roots and excludes unrelated region controls from question
capture. Suggestion dropdowns are identified for manual option selection.

Validation now includes a real MV3 extension in full Chromium, rather than only
mocked scripting APIs: cross-origin filling, denied access, changed values, iframe
and document reloads, scoped answers and post-input retention checks. A read-only
scan of the actual Samsara Greenhouse embed detected seven contact fields; no live
employer fields were filled. [Design, source references and limits](docs/browser-helper-frames.md).

## Helper download filename correction (v0.48.1)

The helper ZIP filename now comes from its bundled manifest, matching the v0.5.0
contents. Older v0.48 downloads were incorrectly named v0.4.0 even though they
contained v0.5.0. The download regression checks every bundled helper file and
the filename against the manifest.

## Reusable application answers and visible field selection (v0.48)

Helper v0.5 adds an explicit local question/answer library with approved aliases,
page/site/all-site scope, edit/delete and JSON import/export. It proposes saved
professional answers for labelled text, textarea, numeric and native select
controls. Answers start unchecked; nothing is captured in the background.
Contact JSON stays compatible. Empty previews disable filling and explain
embedded-form/manual-control limitations; ARIA-labelled contact inputs work too.
The library lives in extension storage, separately from workspace recovery.
See [helper workflow and storage](browser-helper/README.md). Reload the existing
unpacked helper folder to v0.5.0; restarting RoleWeave alone does not update it.

## Contact handoff and refined resume layout (v0.47)

Contact preparation accepts bare domain links such as `github.com/name`, creates
a validated HTTPS contact-sheet value, and leaves the saved profile unchanged.
The helper page shows preparation status and enables JSON download only for a
prepared current profile. Helper v0.4.0 remains the installed companion.

New Jake-inspired previews join imported line wraps, align dates within section
rules, and remove exact duplicate structured headings and known internal source
markers from printable wording. Older saved layouts keep their original rendering.
AI section requests tolerate empty unused canonical fields, allow a 1200-character
summary and distinguish shape, reference and length failures. Claims still require
review; neither provider availability nor live output quality is guaranteed.

## Free AI requests and persistent browser companion (v0.46)

Section tailoring now previews an8192-token output budget, minimal reasoning and
OpenRouter's free JSON response-healing plugin. Provider429 delays are surfaced,
and immediate same-route tailoring sends are held locally during the cooldown.
Malformed JSON has a separate diagnostic; truncated or invalid-source drafts stay
unaccepted. Free provider capacity and quality remain outside the app's control.

Helper v0.4.0 opens a persistent window bound to the originating application tab,
so native file selection does not depend on a transient toolbar popup. On employer
pages, import the contact JSON downloaded from RoleWeave; Load prepared sheet is
for the local RoleWeave tab only. No additional host permissions. See
[AI diagnostics](docs/ai-request-failures.md) and [helper usage](browser-helper/README.md).

## Search coverage, Jake-inspired resumes and rehearsal setup (v0.45)

Role-title matching now separates relevant titles from body-keyword/skill searches.
Discover jobs labels counts as page matches and can load another FreeHire page
without discarding previous matches (up to five pages, then Next page continues).
Markdown experience labels such as `*Experience:* 5 Years` are recognized in new
searches; v1 observation replay stays unchanged. Provider coverage remains finite.

The resume studio defaults to a Jake-inspired serif layout with aligned dates,
structured role headings and individual achievement bullets. Previous saved layouts
remain readable. Rehearsal can prepare an exact requirement directly in its panel;
no prior manual evidence link or model call is needed. Helper v0.3.0 shows its
version, imports contact JSON and recognizes Location (City). **An older installed
extension must be updated separately**; downloading the new app does not update it.
See [workflow and upgrade steps](docs/resume-assessment-helper.md).

## Advertised experience and remote residence (v0.44)

Discover jobs, named searches and the review queue now have 0-2 / 3-5 / 6+
advertised-experience bands and a separate remote-residence country. Known foreign
remote restrictions are excluded; unclear requirements are hidden by default and
can be shown for review. Source bytes and prior decisions remain intact. All v0.43
features are included for the combined trial. [Usage and limitations](docs/experience-location-filters.md).

## Reviewed drafts, focused assessment and helper handoff (v0.43)

Build resume and Create resume now reopen the latest reviewed application draft,
with an automatic preview of its wording. A separate Start from master profile
option starts fresh. Tailoring also continues from the latest application version.
Assessment defaults to three key requirements, optionally using an exact JD excerpt,
with a reviewed 8192-token output cap. Older records remain readable. Helper 0.2.0
can import a prepared contact JSON on the employer tab and recognizes exact Preferred
First/Last Name labels. See [the workflow guide](docs/resume-assessment-helper.md).

## About-only experience and empty proposals (v0.42.1)

Section tailoring now explicitly treats reviewed About text as source evidence even
when the separate accomplishment claim is blank. Accepted About-only experience
wording replaces the About text in the application copy, avoiding duplicate output.
Identity fields and the master profile stay unchanged. An empty model proposal now
shows **No wording proposed** with source-review actions instead of a blank editor.

## Section-by-section AI tailoring (v0.42)

AI now drafts a headline/summary, experience wording, or cover-letter wording in
separate bounded requests. Continue from the resume builder to add another section
to the same application draft. Accepted sections persist; a failed later request
does not erase them. Assessment uses up to six key requirements and six selected
facts. PDFs are assembled locally, with the master profile unchanged.

See [the workflow and limits](docs/section-tailoring.md). Free-only routing, source
validation and one-request credential handling remain enforced. Real provider
availability and generation quality are not established by offline tests.

## Useful AI failures and bounded waits (v0.41)

OpenRouter generation now uses the remaining 60-second request budget after
connection. Safe HTTP/error categories survive worker failures, including error
bodies returned with HTTP 200. Failed requests stop the loading screen and show
a useful terminal message; stalled local calls and generation waits are bounded.
New attempts require a fresh preview, key and consent. No automatic retry,
paid fallback, raw provider diagnostics or relaxed source checks.
[Error codes, recovery and verification limits](docs/ai-request-failures.md).

## Optional private notes and discoverable AI (v0.40)

Career entries can be saved without a private source note. Printed description/
accomplishment fields are clearly labelled, private notes stay excluded, and an
explicit copy action helps recover achievements entered in the wrong field.
Settings now launches all three AI workflows, the resume studio links directly
to AI tailoring, and request previews keep masked API-key fields visible.
[Field mapping and exact API-key steps](docs/private-notes-and-ai-start.md).

## Organized resume import and free AI (v0.39)

Resume import now suggests grouped career entries and separate contact/summary
fields, with optional source-ID-only AI organization. New workspaces default to
OpenRouter free routes; saved preferences are preserved. Settings explains keys
and hides local-port controls for cloud providers. Employer boards accept supported
board URLs, Documents shows original imports plus a guided creation workflow, and
empty assessments offer clear next actions.
[Workflow, free-model setup and limitations](docs/resume-import-and-free-models.md).

## Browser follow-ups and reply review (v0.38)

Saved opportunities now offer local `.eml` excerpt review, private `.ics` reminder
downloads and the existing optional Google follow-up workflow in the browser.
Correspondence requires exact-source review and current history. Google uses
session-only consent, separately confirmed operations and one-shot plans with
existing ownership/revision/ETag checks. Offline practice never connects to Google.
[Workflow, setup and remaining limits](docs/browser-follow-ups.md).

## Reviewed document languages (v0.37)

Choose document labels and structured month dates in the browser resume/letter
studio: English (original/UK/US), German, Spanish, French, Italian, Brazilian
Portuguese and Dutch. Your claims and writing are unchanged. Preview, freeze,
recipient exports and managed recovery bind the selected language.
[Workflow, compatibility and limits](docs/document-localization.md).

## Startup notices (v0.36)

Browse Hacker News startup job notices with no company URL, account or API key.
Explicit bounded batches, local filters, employer/market review and exact source
archives join the existing application/recovery workflow. Notices may be short;
this is not the full YC directory or verified eligibility.
[Workflow, live sample and limits](docs/startup-discovery.md).

## Automatic local recovery (v0.35)

Opt in from Settings & backup: nightly snapshots while the local host runs,
catch-up on next open, seven-snapshot retention, and verified inspection/restore
into a separate workspace. Existing manual exports remain available. Backups are
unencrypted and same-device; no OS task or cloud account.
[Workflow, safety limits and practice](docs/automatic-backups.md).

## Optional reviewed JSearch discovery (v0.34)

The browser now offers a separate experimental JSearch source alongside FreeHire.
Review the exact public request, enter a one-request key and consent to one cursor
page. Provider credits may apply. Cached previous pages need no new request.
Original response bytes and filters join managed recovery on import. No live API
call was performed; compatibility remains an explicit gate.
[Workflow, synthetic exercise and limits](docs/jsearch-discovery.md).

Reviewed assessments/rankings shipped in [v0.33](docs/job-assessment.md); structured
career profiles and retained refinement conversations are also implemented.

## Review edits with undo (v0.30)

AI wording review now has local Undo/Redo for wording and selected suggestions,
plus per-field Reset to proposal. These controls reset accuracy consent and make
no model request. Each new proposal starts a fresh bounded history; accepted drafts
keep existing source/provenance guards. [Guide and checks](docs/review-undo.md).
Full request/proposal refinement history shipped in v0.32; see [the retained conversation guide](docs/refinement-conversations.md).


## Employer boards in the browser (v0.29)

The optional Employer boards page brings Greenhouse, Lever global/Europe and Ashby
observations into the supported browser UI: explicit fetch, local paged filters,
reviewed imports, exact archive download/replay and comparison. Repeated unchanged
postings reuse a review; required source receipts join managed recovery. The normal
role/location search still needs no board URL. No application or account access.
[Workflow, evidence and limits](docs/browser-employer-boards.md).


## Resume theme builder (v0.28)

Build a bounded custom resume style alongside the three existing presets: dark
accent, typography size, margins, Sans/Serif and A4/Letter. Share styling-only JSON,
review a fresh preview after changes, and freeze the exact configuration and bytes.
Old preset rendering and saved documents remain compatible.
[Guide, font limits and runnable checks](docs/resume-theme-builder.md).


## Workspace insights (v0.27)

The new Insights page adds current/ever-recorded stage bars, twelve UTC weeks of
first Applied observations, and a market-filtered follow-up month calendar with
exact-review agendas. Read-only, no provider/account access. Counts are saved
reviews and manual observations, not verified submissions or conversion rates.
[Guide, limits and runnable checks](docs/workspace-insights.md).


## Provider/model preferences (v0.26)

Settings now supports OpenAI, Anthropic, Mistral and numeric-loopback Ollama / LM
Studio-compatible drafting servers. Save only model/kind/port; no credentials or
provider request on save. Every send retains exact preview, destination binding,
one-request key, consent and human review. Preferences and provider provenance
survive managed recovery; existing drafts/bundles remain compatible.
[Setup, limits and offline verification](docs/model-providers.md). Live provider
compatibility and quality remain unverified; no model server is started/downloaded.


A personal Python job-search workspace for Data Engineering and applied AI roles.
Two separate markets: India/remote-from-India and international relocation.
Original implementation inspired by existing tools, with no upstream source,
assets or history imported. Local Windows workspace for posting review, selected
evidence, manual application tracking, follow-ups and preparation packs.

See [v0.6 readiness tools and recovery](docs/readiness-workflow.md) for search,
ordering, private exports, evidence rehearsal and safer build/export publication.

## Saved discovery searches and a review queue

Save named filters without a request. **Saved searches → Run now** explicitly reads
one page, retains source evidence, deduplicates exact observations and preserves
keep/dismiss/save decisions. Reviewed imports create application records, never
submission events. Failed/empty runs preserve the queue. Managed recovery includes
configuration, queue, run history and original-byte evidence.
[Saved discovery guide and limits](docs/saved-discovery.md).

Existing-resume import now accepts UTF-8 Markdown (`.md`/`.markdown`) as literal
text for human-selected excerpts, alongside text PDF/DOCX/TXT. Markup is never
executed or remotely fetched; original bytes join managed recovery after confirmation.
No OCR or inferred employment/profile write is added.

## Dossier comparison and application email

[Current 25-area parity checklist](docs/dossier-parity.md): v0.28 has 12 implemented,
6 partial and 7 missing areas. These are scoped workflow counts, not an overall
completion percentage or production acceptance. Live accounts, employer forms and
personal usefulness remain separate gates.

Saved job → **Prepare application email**: choose a frozen PDF resume and optional
matching PDF letter, enter sender/recipient/message, preview exact attachments,
then confirm a local draft. Save/reopen, copy the message or download an EML for
your mail client. No email is sent and tracking remains unchanged. Managed recovery
includes saved drafts. [Email handoff and limits](docs/application-email.md).

## Interview rehearsal in the browser

Saved job → **Interview rehearsal**: choose exact requirement questions, reveal
linked evidence, write your own answers/reflections and confirm a new private
version. Reopen versions or download their original private JSON. Workspace
recovery includes managed journals and checks their exact saved-review identity.
No generated answers, grading or learning-completion claim.
[Rehearsal guide](docs/browser-rehearsal.md).

## One interface: the browser workspace

Use **Launch-RoleWeave.cmd** in this repository or the complete v0.22 portable
package. The launcher chooses the current versioned package, ignoring stale
`out/portable` builds. Normal launch, offline practice and old `--legacy`
shortcuts all open the browser interface. Native-only tools are pending migration;
there is no advanced-tools fallback. Existing data is preserved, never merged
automatically. [Launch and workspace guide](docs/single-interface.md).

## Reviewed AI drafts in the browser

Saved job → **Tailor with AI** previews an exact posting/selected-facts request.
Review and revise proposals, then approve only accurate wording for a separate
application draft. Your main profile stays unchanged. Saved drafts reopen with
their letter wording, feed the visual resume studio and join managed recovery.
Offline practice uses a clearly labelled fixed fixture without any model call.

[AI tailoring and privacy guide](docs/ai-tailoring.md). Source references are not
factual verification. Live provider quality/account compatibility is unverified.
The dashboard also uses compact next-step onboarding and aligned section spacing.

## Application documents, with a visual studio

Open a saved job → Build resume. Choose one of three layouts, select and order
reviewed facts, preview the document and download the exact preview PDF. A changed
selection/layout requires another review before freezing. New cover letters export
as PDF or TXT, and application ZIPs can contain both recipient PDFs.

[Application studio guide](docs/application-studio.md). Existing frozen documents
and backups remain supported. Single-request AI drafting/refinement is now available; multi-provider/full chat
and universal application filling remain missing. This is not full Dossier parity.

## Start with your resume and keep your workspace recoverable

Career profile → **Import existing resume** accepts local text PDFs, DOCX and
UTF-8 TXT. Preview the extracted text, choose accurate excerpts and sections,
confirm, then save your profile draft. No qualifications or contact details are
inferred. Original source bytes and hashes stay local.

Settings → **Download recovery ZIP** includes the database and managed letters,
recipient files, original imports and provider snapshots. Preview/validate a
bundle before restoring it into a separate workspace; the current one stays
intact. Legacy database-only JSON backup remains available.

[Complete first-use and recovery guide](docs/using-roleweave.md).

## Reliable startup and HTTPS

The original local Windows build omitted a required SSL policy sidecar from its
Python runtime, so source searches passed while packaged first searches failed.
The patch bundles that runtime asset without disabling certificate verification.
The web runtime smoke now constructs a verified HTTPS context offline, and an
explicit `--search-check out/search-check` can verify the generic public
`data engineer` / `london` query from the actual packaged runtime. It reads no
saved jobs or credentials. Search errors remain visible below the search box.

Double-click the complete updated package. Startup reuses a matching current
workspace or selects a free local port; hidden older/unrelated servers are left
untouched. Closing a browser tab still leaves its host running; Settings → Quit
stops it, but finding an older host is no longer required to open the new app.

## Release status

V0.25 is an unsigned Windows x64 **controlled beta**, not a verified production
release. The local workflows are implemented and offline tested; personal
acceptance, unusual display scaling, signing and optional live account/model
behavior are recorded separately. The agreed v1 scope is the local Windows
workflows; Google/AI remain optional previews outside local-v1 acceptance. See [release acceptance](docs/release-acceptance.md) for
what must be verified before recommending general use.

## Continue an application in v0.18

Saved cover letters now reopen under Documents and the exact job's application
kit. Read/download them later and choose a compatible letter alongside the resume
PDF in a recipient ZIP. Wrong-job/profile combinations are refused. Invalid
saved letter files are reported without deletion.

Discover jobs has explicit Previous/Next pages with validated offsets and retained
market choice. Applications combines market, text, stage and due-through-today
filters. Stage/submission forms preserve existing reminders; a stale form can
reload current tracking while keeping its draft and requiring renewed submission
confirmation. [Continuing-workflow guide](docs/continuing-applications.md).

## Apply for a job with RoleWeave

Open the browser workspace, create a reviewed career profile, then **Discover
jobs** by role/location. Save to India/remote or relocation, review the job, build
and download a PDF resume, and optionally prepare a reviewed cover letter.

Install the small Chrome/Edge **Browser helper** once. Prepare a contact sheet in
RoleWeave, load it with the toolbar icon, then review and fill supported empty
contact fields on the employer's form. Upload your documents, answer screening
questions and submit yourself. Record your observed submission and follow-up.
No company-board URL is required for this discovery path.

[Browser workspace, helper setup and complete walkthrough](docs/browser-workspace.md).

The new default uses browser-rendered CSS/SVG and the existing Python/SQLite core.
The native interface is retired; employer boards, Calendar follow-ups, local reply
review and interview rehearsal now have browser workflows. Audits and additional
rehearsal tools remain unmigrated. Original shelf paths and
immutable document/history contracts remain.
The helper does not submit, upload, overwrite existing values or answer sensitive
questions. Custom widgets and iframes remain manual; real ATS acceptance is pending.

## Start on Windows

[What is ready and what remains](docs/personal-readiness.md):8/8 core local workflow groups are implemented/offline tested; personal acceptance and optional live integrations have separate gates. Getting started now explains the current workflow and your actual data path.


Version0.19.0 includes reviewed cover letters, exact private application dossiers,
recipient-only document exports, manual submission receipts and local email
excerpt review. Source-bound records and conflict-safe tracking preserve prior
evidence. [Application delivery guide](docs/application-delivery.md).

Core features run locally. Optional AI requires your own session key and
per-request consent. Live quality, personal usefulness and connected-account
integrations remain unverified.

For the portable build, extract the **whole** `RoleWeave-0.19.0-windows-x64.zip`
and open `RoleWeave/RoleWeave.exe`. Keep its `_internal` directory beside it.
The build is unsigned. A per-user setup artifact is available; automatic updates are not provided.
The CI run's `RoleWeave-0.19.0-windows-x64` artifact contains this ZIP.

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
builds the portable app and runs its headless browser profile/resume/recovery self-test.
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

### Structured career entries (v0.31)

Ten typed career sections now feed reviewed documents and evidence, with immutable
profile versions and stale-editor protection. See [workflow and checks](docs/structured-career-profile.md).
Reference contacts require explicit entry selection to print; structured reference
email/phone are excluded from AI context. Whole-entry review remains your assertion,
not independent verification. Other partial/missing parity areas remain open.

### Retained refinement conversations (v0.32)

Opt into unencrypted local request/proposal history, reopen an earlier proposal
without a model call, branch revisions and recover or remove a whole conversation.
[Workflow, limits and practice](docs/refinement-conversations.md). Credential fields
are excluded; manually typed private text is not scrubbed. Fresh review/consent
remain required. Other partial/missing parity areas stay open.

### Reviewed job-evidence assessments (v0.33)

Inspect and correct model opinions against exact posting quotes and selected facts.
Compare same-source/model groups, filter markets and reopen per-job review versions.
[Workflow, limits and practice](docs/job-assessment.md). Scores are uncalibrated
opinions; coverage concerns quoted rows only. No eligibility or hiring claim.
Managed recovery replays the exact request from its bound sources.
