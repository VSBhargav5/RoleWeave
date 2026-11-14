# Use RoleWeave from an existing resume — v0.21

## The local application workflow

1. Open the complete Windows package. It opens a local browser workspace and
   handles an occupied port automatically; keep `_internal` beside the executable.
2. Career profile → Import existing resume. Choose a selectable-text PDF, DOCX or
   UTF-8 TXT file. Read the extracted text. Select accurate excerpts, choose each
   excerpt's section, confirm, and then save the profile draft. Enter your actual
   identity/contact fields explicitly; the importer does not guess them.
3. Discover jobs by role/location/country/remote preference. Read a description,
   choose India/remote or relocation, and save it. Search pages are observations,
   not exhaustive coverage, eligibility or sponsorship proof.
4. Open the saved job, review requirements and optionally connect exact quotes
   to your sourced facts. A changed review is a new identity; applications do not
   automatically move to that revision.
5. Optionally use [Tailor with AI](ai-tailoring.md) for reviewed application wording
   in a separate draft. Build a resume in the [visual studio](application-studio.md): choose a layout,
   select/order reviewed facts, inspect the preview, confirm and
   download the frozen PDF. Optionally write/review a PDF cover letter. Documents and
   the application kit reopen earlier versions; recipient ZIPs contain only the
   selected resume and compatible letter, not private evidence/history.
6. Open the employer application. The optional Chrome/Edge helper can preview and
   fill supported empty native contact fields after explicit consent. Upload your
   PDF, answer screening questions and submit yourself. Installation and limits:
   [browser helper](browser-workspace.md).
7. Record your own submission and reminder. Use combined board filters for the
   next action. Stale forms refuse overwrites; explicit reload retains your draft
   for comparison with newer tracking. Opening/filling a page is not submission.

## Resume import contracts

Extraction stays on this computer in an owned child process with a 20-second
deadline. Input is capped at 4 MiB, PDFs at 20 pages and extracted text at 100,000 characters/
500 blocks. Select up to 100 blocks per reviewed import. Scanned PDFs have no OCR
here; use an externally prepared text copy. Encrypted PDFs and unsupported files
fail explicitly. PDF reading order and line breaks may differ from the original;
check selected excerpts and correct the draft before saving. This is text import,
not layout reproduction or verification of employment/education/metrics.

No employer, date, qualification or contact value is inferred. Imported excerpts
carry original-file SHA256 and extraction-block references. Original bytes are
retained only after confirmed selection under managed `web-artifacts/resume-imports`.
Importing adds to a draft; it never silently replaces your profile or existing
facts. Saving creates a new version. The parser does not execute document macros,
scripts or instructions; it is not an OS sandbox or an OCR system.

The pinned [pypdf documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
describes text extraction and scanned/layout limitations. No live AI is used by
this flow. Optional native AI/Calendar tools retain their existing separate setup
and consent; they are not prerequisites for the local application journey.

## Back up the workspace, not just its database

Settings → Download recovery ZIP captures the current database plus **all managed
web artifacts**: saved letter versions, recipient ZIPs, original imported resumes
and retained provider-response bytes. Database consistency and managed-file
inventory are checked across capture. A concurrent change, unsupported/in-progress
file, corruption or size limit refuses export instead of claiming a partial backup.

The bundle is unencrypted and capped at 64 MiB/1,000 managed files. Keep it private.
Arbitrary files exported elsewhere, native journals/dossiers saved outside the
managed directory, other workspaces, browser-helper session memory, credentials
and unsaved drafts are not included. Database-only JSON backup remains available
for the older compatible merge workflow; it does not include managed artifacts.

To recover: Settings → Choose recovery ZIP. Review validated counts and explicitly
confirm. RoleWeave checks paths, sizes, hashes and the database before creating a
**new independent workspace**. It never merges this ZIP into the active database
or overwrites its files. Writes are staged, and a completion marker is published
only after closed writes. An interruption can leave an unlisted staging directory;
it is not presented as a completed recovery. Hard-link-capable storage is required. Windows recovery uses explicit extended paths to support deep workspace folders
without changing system settings.

Open the recovered copy from the confirmation or Settings → Recovered workspaces.
It opens separately and is labelled in the header. You can still use the original.
Completed recoveries remain listed after reopening; listing is bounded with an
explicit notice. Each workspace needs its own future backup. Restore your own
trusted bundle: fingerprints verify byte consistency, not authorship or the truth
of reviewed claims. This is managed-workspace recovery, not whole-computer backup.

## Verify and practice

```powershell
python -m unittest discover -s tests -v
python desktop.py --web-self-test out/import-recovery-smoke
python desktop.py --demo
```

With the development Playwright setup, `node tests/browser-workflow.cjs` tests
import → explicit profile save → document preparation → recovery ZIP → reviewed
separate recovery, together with prior search/filter/tracking/helper checks.
The Windows frozen self-test actually runs its bundled PDF parser child and
managed recovery; source-only success is not packaged proof.

For a 60–90 minute exercise, use a separate synthetic shelf. Predict which two
excerpts will become draft facts, import them and save a version. Freeze a resume,
save a letter, export a recovery ZIP, restore it separately and compare originals,
profile identity and recipient file lists. Explain why hashes do not establish
truth and why restoring into a new workspace protects current work. Practice is
not recorded as completed learning until you demonstrate it.

The local workflow is implemented and synthetically verified, with an unsigned
Windows controlled-beta package. General production readiness is not established.
Personal end-to-end acceptance, real installed-helper/employer compatibility,
unusual scaling/accessibility, signing/distribution, interrupted installer upgrades
and optional live AI/Google acceptance remain explicit gates. No application,
personal external transmission, account link or paid call is performed for you.
