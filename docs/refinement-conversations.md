# Retained refinement conversations

In Tailor with AI, opt into **Keep completed conversation turns locally** before
previewing a request. It is off by default. Review the exact provider payload and
consent to each send as before. A completed retained turn saves your instruction,
original request bytes, unaccepted proposal, source profile/job fingerprints and
selected fact IDs. A revision also records the edited previous proposal and parent
turn. Revising an older turn creates a branch; earlier turns remain unchanged.
Failed/cancelled requests do not create proposal turns. Previewing sends nothing
and writes no history. History-write failure leaves a valid proposal usable in the
current session with a warning; a file might exist, so no automatic retry is made.

**Saved conversations** browses20 turns per page for the exact job review, with
conversation/parent/profile IDs and a synthetic-vs-provider marker. Reopen an old
proposal after closing/restarting the app: it verifies source identity and the
parent chain, makes no model call, activates no profile and accepts no wording.
Inspect its original request, edit it, use local Undo/Redo/reset, or request another
revision after a fresh payload preview/consent. Fresh accuracy confirmation is
always required before creating an application-specific reviewed draft. That draft
does not replace the active career profile. The selected original source version
is disclosed; a newer active profile is not silently substituted.

The full request/proposal conversation persists, not every keystroke or transient
Undo state. Local review edits persist in the next retained revision request or in
an explicitly accepted application draft. Closing an unsaved review does not save
those edits; history navigation warns before discarding edited review wording or a
revision instruction. Completed unretained turns cannot be recovered retroactively.
No model-quality, truth, suitability, production acceptance or learning claim.

## Storage, recovery and removal

Records live under the shelf's web-artifacts/refinements directory. They are
unencrypted and included in managed workspace ZIP recovery, alongside their exact
source profiles/reviews. The separate shelf-only JSON backup does not include them.
Credential input fields are never written to these records. This is not secret/PII
scrubbing: text you type into an instruction/claim can contain private data, which
will also be retained when you opt in. Inspect payloads and keep backups private.

Fingerprints and source/parent checks establish consistency, not provider authorship
or the truth of proposals. Untrusted rehashed artifacts can still contain misleading
wording; review before use. Limits:1MiB per turn,256KiB request bytes,1000 history
files,50 turns along any revision path, existing64MiB managed-recovery bound.
Long conversations or unrelated archives can exhaust the recovery bound before the
history-file limit. No truncation, background pruning, hidden retention, automatic
provider retry or implicit send on reopening.

Remove whole conversation requires an explicit confirmation. It removes every local
branch/turn of that conversation, preserving other conversations, accepted drafts,
profiles and documents. Stop an active request first. Validation precedes unlinking;
a filesystem interruption may leave files. Root-last removal allows a retry after
partial deletion. It is not secure erasure and cannot delete previously exported
backups or undo provider processing/charges. Corrupt/unverifiable files are preserved
and reported rather than guessed at or silently deleted.

## Focused practice (60-90 minutes)

Use a separate synthetic practice shelf. Retain a first offline proposal, edit the
summary, then request a shorter revision. Predict which exact previous wording the
second payload contains. Close/reopen the app, browse the two retained turns and
reopen the first: predict zero provider sends and no checked accuracy box. Branch
from that older proposal. Export/recover the managed ZIP and compare the request
and proposal fingerprints. Remove that conversation; predict which accepted draft
and other conversation remain. Tradeoff: durable history helps review/recovery but
increases the amount of unencrypted private text on disk. Practice is not presumed.

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_refinement_history.py -v
node --test tests/review-history.test.mjs
node tests/browser-workflow.cjs
```

Browser prerequisites are in [browser-workspace.md](browser-workspace.md).
Tests cover opt-in/credential exclusion, immutable edited parents, no-send reopen,
fresh acceptance, disk failure, corrupt/missing/cyclic parents, recovered bytes,
explicit and interrupted removal, pagination, bounded paths and late cancellation.
