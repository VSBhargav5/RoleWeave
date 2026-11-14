# Application document studio — v0.20

## Prepare documents for one saved job

1. Save your career profile and the job. Open its Application kit → Build resume.
2. Choose Classic, Slate or Editorial. Select reviewed facts. Use the arrows to
   reorder facts **within a section**; section order remains fixed. Unselected
   facts and private source notes are excluded from the document.
3. Preview resume. The read-only paper preview shows the HTML layout; its screen
   width and pagination are not a promise about the PDF. Download preview PDF to
   inspect the exact PDF bytes before saving. Nothing has been frozen yet.
4. If you change selection, order, layout or version label, preview again.
   Confirm the current document and Save & download PDF. The server checks the
   exact preview fingerprint before saving a themed version. No claim is rewritten.
5. Choose Cover letter next to that resume. Write your own introduction and closing,
   select reviewed examples, preview and confirm. PDF is the default; TXT remains
   available when the bundled font cannot represent your characters. No AI call
   or automatic qualification inference is involved.
6. Saved letters reopen in Documents or the exact job's kit. Download the frozen
   PDF or TXT. Export application ZIP with a matching letter to receive resume.pdf
   and cover-letter.pdf; older TXT-only letters produce cover-letter.txt instead.
   Private profile snapshots, source notes and history are excluded.
7. Proofread, open the employer application, use supported reviewed contact filling,
   upload documents, answer screening and submit yourself. Record your submission
   and follow-up in RoleWeave. An exported kit is not a submitted application.

## Versions and compatibility

Classic preserves the previous v1 resume renderer. New colored layouts are v2
resume records with a validated theme. New PDF letters are v2 records containing
frozen PDF bytes and hashes; replay checks the PDF against reviewed text. Old
TXT-only letters remain v1, reopen normally and are never presented as frozen PDFs.
Private dossiers with PDF letters use v3; earlier v1/v2 dossiers still verify.
Recipient export explicitly selects document formats. Backup/restore supports
both old and new versions. Preserved original bytes are authoritative; never
regenerate or overwrite a prior version to pretend it was updated.

Windows recovered workspaces now use explicit extended paths for file operations,
so deep practice/recovery folders can preserve original source filenames without
changing registry or system policy. Link checks, staging, exclusive publication
and completion markers remain. This is not a guarantee for every filesystem.

## Verify and practice

```powershell
python -m unittest discover -s tests -p test_document_studio.py -v
python desktop.py --web-self-test out/new-studio-runtime-check
python desktop.py --demo
```

The complete synthetic browser test changes a layout, moves a selected fact,
checks styled preview rendering, downloads a resume and letter PDF, exports a kit,
records a manual observation and restores a separate workspace. Frozen CI runs
that same journey against the actual Windows executable.

For a focused 60–90 minute exercise, use synthetic data: predict which selected
claim appears first, move it, inspect two layouts and confirm that changing the
selection invalidates review. Compare the downloaded preview with the saved PDF,
inspect recipient ZIP members, then recover separately. Explain why a layout
choice changes presentation but cannot establish qualification or ATS acceptance.
Learning remains unverified until you practice.

## What this does not complete

[v0.21 browser tailoring](ai-tailoring.md) adds reviewed AI proposals and explicit
revisions, with separate saved drafts. It does not add multi-provider/full chat,
scheduled discovery, Gmail, broad calendar synchronization, universal employer
form filling, automatic uploads/submission, signing or verified personal acceptance.
The helper still handles its documented native contact-field subset. Optional
native AI quote extraction and narrow Google follow-up sync retain their own
explicit setup/consent and unverified live-quality gates. The app is an unsigned
controlled beta, with no claim of Dossier feature parity or hiring outcomes.
