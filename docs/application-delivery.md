# Application delivery workflow (v0.8)

Start with a saved review and a reviewed career profile. Save or discard job edits
before opening tools under Evidence & next steps → Review files.

## Prepare a cover letter

Choose Prepare reviewed cover letter. Select reviewed career claims, write your
own introduction and closing, and preview the exact letter. Claims are copied
without rewriting; your own text is not independently verified. Confirm review,
then export a letter TXT or private source-version JSON.

A private letter version embeds the full profile and job snapshot, including
unselected/private source evidence. Keep it for your own records. Open frozen
letter version replays it and exports its original text after confirmation.
Editing the profile later does not rewrite an older letter. Unsaved input is
guarded; editing after preview requires a new preview.

## Prepare a private dossier and recipient documents

Create a resume frozen for the exact saved review. Open Private application
dossier and choose that resume. General or other-review resumes are excluded.

Letter → Prepare letter from matching profile uses the resume's frozen profile.
Save that letter as a private JSON version, then choose Attach saved matching
letter. A letter must use the same exact review and profile version as the
resume. Removing/changing it clears prior preview/confirmation.

Preview the private manifest, frozen resume text and optional letter text.
Confirm before exporting. The private dossier ZIP includes the original review,
full frozen resume source record, history, preparation notes, document bytes and
optional full letter source. **Keep this whole dossier private.**

Use Export recipient files and choose txt, html, pdf and/or letter. A separate
ZIP contains only chosen resume documents and cover-letter.txt; private source
records, history and notes are excluded. Choose only available formats and review
them before manually sending. RoleWeave neither sends nor marks an application.

Verify private dossier checks bounded members without extracting paths, rejects
duplicates, unsupported compression and fingerprints, and replays documents from
frozen evidence. PDF replay uses the installed deterministic renderer; a PDF from
another renderer/build can fail strict replay. Keep its original and matching
source build. Older resume exports still remain available. Integrity/source
replay does not establish source truth, relevance or submission.

Outputs use new filenames and atomic no-overwrite publication on supported
hard-link filesystems. Dossiers are limited to64MiB; private letters4MiB and
letter text64KiB. Archive/member traversal, malformed documents and stale source
identity fail closed.

## Record a submission you made yourself

Choose Record my manual submission, load the matching private dossier, enter your
observed date/channel/reference/note, and explicitly confirm. This appends a
user-reported applied revision, preserving the current follow-up and earlier
history. The dossier fingerprint links prepared evidence; it does not prove
which files were actually sent. Identical observations are refused. No email,
form filling or account service is invoked.

## Review a local reply

Choose Review local email correspondence and select a permitted .eml file.
The2MiB reader handles bounded inline plaintext MIME, preferring no HTML fallback;
HTML-only/unsupported messages fail. Attachments and attached messages are
ignored and never opened or copied to the shelf. No remote images are requested.

Read the plaintext, select an exact excerpt, add your own observation and confirm.
Only the excerpt, bounded header labels, original byte hash and your note enter
application history. Sender/header identity is not authenticated. Original email
and attachments stay outside shelf backups; preserve your original if needed.
Stage/follow-up are retained. No interview/rejection/offer is inferred from words.

Tracking now checks expected revisions. If another window saved first, stale
edits are refused. Your draft is retained; explicitly reload saved tracking after
deciding to discard it, then review the new state.

## Reproduce and practise

With the existing test requirements installed:
```powershell
python -m unittest discover -s tests -v
python desktop.py --self-test out/new-delivery-smoke
python application_dossier.py --verify PRIVATE_DOSSIER.zip
python mail_observation.py examples/reply-synthetic.eml
```

Use a new self-test directory. Letter versions, dossiers, recipient ZIPs and
original email files are separate private files, excluded from shelf backups.
Recorded submission/correspondence notes use existing append-only history and
are covered by v3 backup/restore. No schema migration or new dependency is added.

For one60–90minute session, use a separate synthetic shelf: prepare a matching
letter/dossier, inspect recipient-only ZIP members, change one exported text byte
and predict verification failure, then record a synthetic submission and reply.
Open two tracker windows and predict the stale-write rejection. Explain why source
integrity and manual observations do not prove a real application was sent.
User practice, live provider quality, manual dialogs/scaling, calendar-client use,
connected accounts and real hiring outcomes remain unverified.
