# Printed career content, optional notes and AI entry points (v0.40)

## The private note is optional

The structured career form previously required **Private source / evidence**, and
the profile validator also rejected blank notes. That prevented saving an entry
even after its actual role, description and accomplishments were filled in.

It is now **Private note or evidence link (optional — never printed)**. Leave it
blank when you do not need a private reference. The review checkbox confirms your
resume content; it does not require a separate proof document. A self-reported
claim is still your assertion, not independent verification.

Content maps as follows:

| Field | Where it is used |
| --- | --- |
| Role, organization, location, dates, skills | Printed when the entry is selected |
| Description / responsibilities | Printed when the entry is selected |
| Achievements / bullet points | Printed when the entry is selected |
| Private note / evidence link | Private review context; excluded from resume and AI drafting requests |

If you put achievements in the old private-source field, open that entry and
choose **Copy note into printed accomplishments**. This is an explicit copy for
you to inspect; the original note remains private. Review the fields, keep the
entry in your draft, then save the career profile. Reopen the resume builder and
preview again. Existing frozen documents do not change.

The app does not automatically publish old private notes. Empty notes remain empty
in the saved profile and recovery. When reusing a note-free entry as job evidence,
the source label states that it is self-reported and binds the profile/fact IDs.
Existing nonempty private notes are preserved. Older app versions that required a
note may reject new blank-note profiles; use v0.40 or newer for these workspaces.

## Where to use AI and enter your API key

Open **Settings & backup → AI tools & model setup**. Provider/model controls save
non-secret preferences. The **Use AI — and where to enter your key** section has
direct buttons for all three tools. Starting a tool saves the currently selected
provider/model locally when changed, without making a model request.

1. **Start resume organization:** choose a resume file, then **Review AI
   organization request**. Inspect the text/destination, enter the one-request
   OpenRouter key, confirm and run. The model groups source lines only.
2. **Start AI tailoring:** choose a saved job, select reviewed facts, then
   **Review provider request**. The masked **OpenRouter API key for this request
   only** field is on that screen. Approve and send, then check the proposal.
3. **Start job assessment:** choose a saved job and facts, then **Review assessment
   request**. The masked API-key field appears before you approve the request.

The resume builder also has **Tailor this resume with AI**. It starts from your
saved career profile. Closing an edited layout asks about discarding its unsaved
changes before opening AI. Simply selecting a layout or clicking Preview resume
does not call AI.

Request JSON is expandable instead of taking the whole screen above the key field.
Exact request fingerprints and the separate send-consent checkbox are unchanged.
Opening a tool or typing a key does not send it. Keys clear on send/close and are
not saved in Settings or backups. Offline practice uses synthetic responses and
has no real API-key field. Local servers use their optional request token field.

For free routes choose **OpenRouter (free models only)** and `openrouter/free` or a
specific `:free` model ID. Free-only request previews explain the disabled paid
fallback. Existing [routing and setup limits](resume-import-and-free-models.md)
apply. Availability and real output quality remain unverified by the agent.

## Verification

Focused regressions check blank-note save/reuse/recovery, printed description and
accomplishments in TXT/HTML/PDF, and exclusion of private notes. The synthetic
browser journey covers saving a blank note, explicitly copying a misplaced note,
all three Settings shortcuts, the studio shortcut and a visible masked key field
using a simulated main-workspace request preview. No real key/model request or
personal resume transmission is performed.
