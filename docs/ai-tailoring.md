# Reviewed browser AI tailoring — v0.21

## One job, one separate application draft

Open a saved job and choose **Tailor with AI**. Choose up to 20 reviewed facts and
write a direction. **Review provider request** shows the exact JSON before any
provider call: destination, model, selected claims, posting and revision content.
Contact fields and private source notes are not added, but facts/postings or your
own edits can themselves contain personal material. Read the full payload.

In normal mode, enter a key in the masked one-request field and explicitly
consent. The key is cleared from that field when sent; the app never saves it,
reads it from files/environment, reuses it, or adds it to draft history/backups.
Browser/password-manager behavior is outside that application guarantee.
Charges may apply. store=false is not a zero-retention guarantee. Cancel stops
local adoption; it cannot undo remote processing or charges.

The request uses OpenAI Responses, gpt-4.1-mini, a strict JSON schema and a
4096-token output cap. It has no tools, retries, redirects or automatic next turn.
The existing transport bounds response bytes and enforces a local deadline.
References must name supplied reviewed facts, and output fields/lengths are
validated. Refused, incomplete, oversized or unsupported output is not adopted.

## Review, revise and adopt

Compare each original fact and proposal. Inspect the cited source references,
correct the wording, and check only the fields/claims you want to keep. **Valid
citations do not prove truth.** The validator cannot establish ownership of an
accomplishment, metrics, dates, credentials, eligibility or relevance. The model
may still invent or misinterpret a claim. Human accuracy review is essential.
Questions are model suggestions to investigate, not verified gaps or decisions.

To refine, edit the current proposal if needed, describe the revision and choose
**Review revision request**. Current edited wording is included as untrusted
previous draft content. Inspect and authorize the new exact request separately.
This is a bounded revision workflow, not an automatic conversational agent.
Changing wording or selected approvals clears the final accuracy confirmation.

**Use reviewed wording** saves a private draft for this exact job. Approved
resume changes create an inactive profile version; your main profile stays
unchanged. Approved letter text stays with the job draft. The resume studio opens
with those sources and selections. Review/preview and freeze the PDF as usual.
No model output automatically becomes a resume or an application submission.

Reopen **Application kit → Reviewed application drafts → Open draft** after
refreshing/restarting. The exact profile version and letter wording are restored.
The matching cover-letter editor also loads saved introduction/closing wording.
Frozen earlier documents never change when the main profile or later draft changes.

## Storage, bounds and recovery

Unaccepted proposals and exact request bodies are in local process memory only,
expire after ten minutes and are bounded to five sessions, with one request at a
time. Closing the panel cancels/discards its pending local result. Accepted draft
records keep exact job/profile references, source/request/result fingerprints,
selected facts and reviewed letter wording under managed web artifacts. They do
not contain API keys or raw provider response history. Hashes are integrity aids,
not authenticity or proof of truth. Accepted profile versions remain in SQLite.

Managed recovery ZIPs include the draft files and their profile/job sources.
Validation checks their references before export and restore. A failed disk save
can leave an inactive profile version; retrying the same reviewed wording reuses
it and publishes one completed draft. A repeated successful acceptance returns
the same saved result. Your main profile and prior documents are preserved.
Files/bundles are unencrypted; the existing aggregate backup limits still apply.

## Practice without an account or charges

```powershell
python desktop.py --demo
python -m unittest discover -s tests -p test_ai_tailoring.py -v
python desktop.py --web-self-test out/new-tailoring-runtime-check
```

Use **Settings & backup → Open offline practice** to start a separate seeded
workspace without using a terminal. It is visibly labelled. **Run offline
practice** uses fixed synthetic wording and never calls a model, even if networking
is available. It exercises consent, revision, review, persistence and document
handoff. Synthetic success does not demonstrate live model/account compatibility,
quality, usefulness or factual reliability. Normal mode never silently falls back
to synthetic output after a provider failure.

For a 60–90 minute exercise: predict the transmitted fields, verify that contact
fields/source notes are absent, edit a proposal and observe accuracy confirmation
reset, save selected wording, reload the job draft and compare the main profile,
then recover separately. Explain why a source ID is not a factual verifier. No
learning completion is claimed until you practice.

## Current limits

One provider/model and explicit single-request revisions; no multi-provider
settings, automatic drafting agent, Gmail, general two-way calendar sync,
universal employer widgets, automatic uploads or submission. Native advanced
Google/AI tools keep their previous boundaries. Actual live AI quality, real
employer/helper and personal acceptance, unusual scaling, signing/distribution
and interrupted upgrades remain unverified. This is an unsigned controlled beta.

Official contracts reviewed for implementation:
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create),
[GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
