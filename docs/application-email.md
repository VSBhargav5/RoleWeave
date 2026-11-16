# Reviewed application email — v0.24

Start with a saved job, frozen PDF resume and optional matching PDF cover letter.
Choose **Prepare application email** on the job page or Application kit. Select the
resume, then a letter from the same exact review and frozen profile. Older TXT-only
letters cannot be attached here; create a matching PDF letter or choose no letter.

Enter one plain sender address and one recipient address, subject and your message.
The sender starts from the selected frozen resume's profile. Changing resume resets
the sender to that profile; proofread it. The recipient is deliberately entered by
you, not guessed or verified. No credentials or mailbox are used.

**Preview email & attachments** shows exact message fields, PDF names, sizes and
SHA256 fingerprints. Recheck the recipient and any personal text. Only those PDFs
become EML attachments; private profile sources, reviews, journals and tracking are
excluded. Their assertions can still be wrong; review the PDFs themselves.

Editing any field or selection invalidates preview and clears confirmation. Confirm
only after reviewing, then **Save & download email draft**. This saves an immutable
local version and downloads `application-draft.eml`. It does not send, contact an
employer, change tracking or prove that you applied. Previous drafts reopen on the
same exact saved review; revised saves create new versions. Copy message uses your
browser clipboard permission; if unavailable, select/copy the text manually.

## Mail-client compatibility

The draft is plain-text MIME with original frozen PDF attachments and an X-Unsent
hint. Some clients open EML as a received message or require importing it to Drafts;
physical Outlook/Thunderbird/other-client acceptance is not verified. No Date or
Message-ID is assigned by RoleWeave; your client prepares send-time metadata. If
import is inconvenient, copy the message and use the existing PDF/recipient ZIP
downloads to attach documents yourself. Review To/From/subject/body/attachments in
your mail client before you choose to send. Then record your observed submission
manually. Opening or downloading a draft is never recorded as submission.

No AI email drafting/refinement, Gmail, SMTP, send button, send scheduling, CC/BCC,
automatic recipient extraction or authentication is implemented in this workflow.
It closes the local composer/document handoff gap, not the connected-mail gap.

## Persistence and recovery

Saved draft records are private and unencrypted. They retain fields, exact frozen
resume fingerprint, selected letter snapshot and resulting EML fingerprint.
Managed workspace ZIP recovery includes them and checks source identities and the
reconstructed original message; even rehashed wrong-source records fail. PDF bytes
come from original frozen documents, not a fresh renderer run. Old workspaces
without email drafts still work. DB-only JSON backup excludes managed draft files.
External downloaded EMLs and clipboard contents are outside workspace recovery.

A draft record is bounded to 8 MiB, letter snapshot to 4 MiB, EML to 16 MiB, subject
to 200 characters and message to 10000. The email collection is bounded to 1000 files
and 64 MiB; new writes refuse overflow. The overall recovery bundle has its own
64 MiB/1000-file limit. Hashes preserve consistency, not authorship or truth.

## Verify and practise

```powershell
python -m unittest discover -s tests -p test_application_email.py -v
```

Use a separate offline practice workspace for a 60–90 minute exercise. Predict the
PDF attachments, inspect preview, change the recipient and observe confirmation
reset. Save/reopen/download and verify tracking did not change. Recover a separate
workspace and compare the EML bytes. Explain why preparing a message is different
from observing a sent application. No learning or personal acceptance is claimed
on your behalf. Use synthetic addresses and avoid sending practice mail.
