# Your first application with RoleWeave

RoleWeave helps prepare and track manual applications. It does not submit forms,
auto-fill an employer portal, upload files, read a mailbox or infer that you are
qualified. The complete local path is available through **Apply workspace** on
the selected job. Google/AI are not required.

1. **Save a job.** Use Discover jobs with a supported employer board, or Add
   opportunity and paste the posting. Enter title, company and the saved HTTPS
   posting URL in Job details. Save it. India/remote and relocation stay separate;
   relocation does not imply sponsorship or eligibility.
2. **Open Apply workspace.** It shows the selected job, your recorded stage and
   follow-up, and the ordered actions below. A changed selection or unsaved job
   draft blocks actions until you reopen for the intended saved review.
3. **Review profile.** Enter identity/contact details and add sourced career
   claims. Mark only claims you personally reviewed. Save the profile. This is
   your reusable source, not invented employment experience.
4. **Review evidence.** Select exact requirement quotes from the posting and
   deliberately link relevant profile facts. Save the reviewed snapshot. Original
   snapshots remain; later versions do not inherit an application automatically.
5. **Build/export resume.** Select relevant reviewed claims, preview, approve and
   save the frozen version. Export PDF directly for the employer portal, or
   HTML/TXT if requested. Open/proofread the actual file; check contact details,
   claims, spelling and layout. Exported documents omit private source notes.
6. **Optional letter/bundle.** Prepare a letter if needed. The document-bundle
   window previews a resume frozen for this exact job and exports selected
   recipient files. Extract a recipient ZIP before uploading the chosen PDF/TXT.
   Never upload a private dossier ZIP: it includes source/history information.
   A dossier export is not required to prepare files or track an application.
7. **Open saved job page.** Finish the employer's application steps in your
   browser, reviewing the destination and every field/document yourself. Save
   your confirmation/reference if provided. RoleWeave cannot verify a successful
   submission, current vacancy, applicant eligibility or which files were sent.
8. **Record/follow up.** Return to Apply workspace and choose Record / follow up.
   Select Applied only after you submitted. Record your note/reference and a
   follow-up date; save. Later record replies/interviews/closure as observations.
   A basic record requires no dossier. Optional evidence-linked submission receipts
   remain available under Review files if you want that extra provenance.
9. **Back up.** Back up the shelf and test restore into a separate shelf. Preserve
   separate PDFs, letters, recipient files and other artifacts privately too.

After a step closes, reopen Apply workspace to see current saved prerequisites.
A disabled resume action means no active profile; a disabled file action means
no resume for that exact saved review. A disabled job-page action means the saved
URL is missing/invalid; use Job details to save a valid source or navigate to the
employer independently. If Windows cannot launch the browser, RoleWeave reports
that failure instead of saying the page opened.

## What was verified

A fresh synthetic native Windows UI journey starts with an empty shelf, saves a
posting, creates a reviewed profile, links exact evidence, freezes/exports a PDF,
exports a letter and recipient-only ZIP, exercises a mocked browser handoff,
records an explicit Applied observation/follow-up and restores the full records
into a separate shelf. It checks that source notes stay out of employer-facing
files, that no private dossier was written, and that page opening alone creates
no application history. The PDF text is parsed back for inspection. This proves
the local software flow; it is not a real employer submission or user outcome.

```powershell
python desktop.py --demo
python -m unittest discover -s tests -p test_application_journey.py -v
```

Use synthetic practice before personal data. The browser handoff is mocked in
tests; no employer receives data. Native minimum-size actions, unsaved drafts,
missing URLs and failed browser launches have regression coverage. Unusual
scaling, actual portal behavior and your own document layout need your review.
