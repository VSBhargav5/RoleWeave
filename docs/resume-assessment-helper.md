# Resume, assessment and browser handoff (v0.43)

## Build the resume from reviewed model wording

Choose Tailor with AI, review a proposal and check the fields or fact edits you want
to use. Confirm accuracy and choose Use reviewed wording. This saves a separate
application draft and opens its resume preview. Unaccepted proposals are not used
in a resume. An empty proposal cannot supply new wording.

Build resume, Create resume and subsequent job-level tailoring now reopen the
latest reviewed application draft for that exact saved job. Earlier behavior could
restart Build resume from the master profile and lose the apparent connection to
accepted wording. The preview identifies the application source. Start from master
profile is an explicit separate choice; it does not delete saved application drafts.
Saved PDFs remain immutable; generate a new PDF after accepting different wording.

Continue from the builder for another section. The master career profile is not
automatically activated or overwritten. Names, dates and employers remain factual
source fields. Experience tailoring is now explicitly a writing task: missing
job-specific qualifications belong in questions and should not suppress supported
transferable experience. Provider generation quality still needs a reviewed trial.

## Assessment failures and a smaller request

An OUTPUT-LIMIT response exhausted the generation budget. It does not establish
that the JD exceeded the input context window. Internal reasoning can share that
budget with visible JSON. Selecting fewer roles does not necessarily prevent it.
HTTP 429 is a provider rate limit; shortening a JD does not reset that quota.

The new default assessment requests up to three key quotes with concise reasons,
and reviews an 8192-token output cap rather than 4096. For a long description, copy
an exact Responsibilities or Qualifications section into Optional exact JD excerpt.
The complete saved JD is available below the field. Leaving the excerpt empty uses
the whole saved description. The excerpt must be an unchanged contiguous substring;
generated and accepted quotes must come from that approved scope. No automatic
summarization silently discards requirements.

Assess another excerpt deliberately if needed. Each result is scoped coverage, not
a complete job assessment or hiring probability. Different excerpts have separate
comparison groups. New records use v3; older broad/compact records retain their
original replay contracts. No automatic retries or paid OpenRouter fallback occur.
For 429, stop repeated attempts and inspect the provider quota/capacity before
reviewing a new request. A compatible explicitly chosen free model or an installed
local model is another option; availability is not guaranteed by RoleWeave.

The increased cap is not a guarantee that a reasoning model will finish. The exact
request, endpoint and provider are still previewed before each send; credentials
remain request-only. Direct paid-provider configurations can incur their normal
charges. See [OpenRouter reasoning budgets](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
and [rate limits](https://openrouter.ai/docs/api_reference/limits).

## Browser helper 0.2.0

The screenshot's No contact sheet loaded means the prepared values had not reached
the extension session. Preparing them in the app does not load the extension on a
different tab. Install/reload the updated helper folder from a fresh downloaded ZIP;
reloading an old extracted 0.1.0 folder does not update its files.

1. In RoleWeave Browser helper, review and Prepare contact sheet.
2. Choose Download contact JSON. This file contains unencrypted contact details.
3. On the employer tab, open the helper and use Import contact JSON to select it.
4. Once loaded, Review this form, inspect the destination/values, consent and fill.
5. Review the filled values, upload documents and submit yourself. Clear the helper
   session and remove the contact file when no longer needed.

The previous direct-load path still works: use Load from RoleWeave tab while the
local helper page is active, then switch to the employer tab. Review is disabled
while no sheet is loaded. Import alone never fills anything. Exact Preferred First
Name and Preferred Last Name labels are now recognized. Pronouns, work authorization,
sponsorship, demographic/legal answers, custom widgets and iframes remain manual.
Existing field values are preserved. No credentials, career facts or history belong
in the contact file; the popup rejects unknown fields and oversized files.

## Interview rehearsal

Open Interview rehearsal on a saved job. If it has no linked requirements, the
panel now offers an exact requirement from the posting (or paste another exact
quote), optional reviewed experience, and Prepare interview question. Confirm the
source to create a new job review and start answering immediately. Add another
requirement prepares a further review; existing drafts, assessments, resumes,
tracking and journals stay on their original review. No AI request is needed.
A requirement can remain an open question without supporting facts. Saving an
advisory assessment remains separate from these source connections.

## Verification limits

Synthetic tests cover legacy/new assessment replay, excerpt validation and budgets,
accepted wording in extracted PDF text, draft reopening and contact-file handoff.
Popup storage/tab APIs are mocked in the browser test; scanning and filling operate
on actual native test inputs, including preferred-name and excluded-sensitive cases.
Installed-extension behavior on the user's live employer page and real provider
generation/rate-limit recovery are not established by these tests.


## v0.45 search and document layout

Choose Role title for job-title relevance; choose Keywords / skills in posting
for a broad skills search. Data Engineer also matches data integration/platform/
warehouse/analytics engineers, analytics engineers and ETL engineer/developer
variants. Other roles use the query words in the title. No semantic ranking or
complete-market coverage is implied. A narrow title can be broadened deliberately.

The count describes matches from observed provider pages, not every job in a city.
Load more matches appends one FreeHire page per click, deduplicates source IDs,
and keeps each result bound to its own observed source for saving. Up to five
pages can be accumulated; Next page continues after that. Failed requests preserve
the existing results. JSearch retains its separate per-page key/consent flow.
Named searches still observe the first page only. Unstated experience/residency
requirements remain hidden unless Include unstated / unclear is selected.
New version-two filters recognize Markdown around Experience labels. Existing
version-one run replay and recovery retain the original classifier.

New resume previews default to Jake-inspired: serif type, centered contact details,
black section rules, role/date and organization/location headings, separate bullets,
and Letter paper with half-inch margins. It uses native HTML and ReportLab; no
Overleaf account or LaTeX installation is required. Layout inspiration:
[Jake Gutierrez's MIT-licensed resume](https://github.com/jakegut/resume) and
[Overleaf template](https://www.overleaf.com/latex/templates/jakes-resume/syzfjbzwjncs).
No sample career content is imported. Long resumes continue across pages without
removing selected content. Classic, Slate, Editorial and custom layouts remain.

## Update the installed helper to v0.3.0

The popup must show v0.3.0 and Import contact JSON. If it only shows Load contact
sheet, it is the older installed extension. Download the new helper ZIP, extract
to a stable folder, then open edge://extensions or chrome://extensions. Remove the
older RoleWeave extension and Load unpacked from the new RoleWeave-helper folder.
Downloading a ZIP or starting a newer RoleWeave app does not update an unpacked
extension. Reloading only helps if its original folder contains the updated files.

Prepare the contact sheet in RoleWeave, download contact JSON, and import it in the
new popup on the employer tab. Review the destination and proposed empty fields,
consent, then fill. Location (City), First/Last Name and Preferred First/Last Name
are supported exact labels. Sensitive screening questions remain manual. Importing
a file alone does not fill a form. Clear the helper session after use.

## v0.47 contact preparation and refined layout

A bare domain in Portfolio or LinkedIn is normalized to HTTPS in the prepared
contact sheet. The saved profile is unchanged. Unsafe schemes, embedded
credentials and malformed links remain rejected with a field-specific message.
Download stays disabled until preparation succeeds for the current profile; the
inline status shows success or the field to correct. No extension update beyond
v0.4.0 is required for this app-side fix.

New Jake-inspired previews use a versioned refined renderer: normal summary flow,
dates aligned inside the section rules, explicit achievement spacing, and cleaner
plain imported sections. Exact repeated structured headings and known bracketed
source IDs are removed only from printed wording. Other content is preserved. Old
Jake/Classic/Slate/Editorial rendering remains byte-compatible with v0.46.
