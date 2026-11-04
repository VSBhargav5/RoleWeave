# Discover, review, and follow up

## Public discovery

Choose **Discover jobs** from the shelf. Enter the employer's Greenhouse
board token (the slug from its public job-board URL) and an employer label you
checked. For a public example, token `greenhouse` refers to Greenhouse's own board.
Press **Fetch public board**: this sends one unauthenticated HTTPS GET to
`https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs?content=true`. Your profile,
career facts and notes are not sent. The provider receives the token and normal
connection metadata, including your IP. Nothing is fetched at app startup.

Filter titles/locations locally, select a post and inspect its plain-text preview.
Choose India/remote or relocation yourself, then import. The location label does
not establish permission to work there or sponsorship. Prospect/general-interest
posts are excluded. The adapter uses the post ID, not internal requisition ID.

Identical imported snapshots are refused; a changed source record creates a new
snapshot. Existing evidence/application history remains attached to its original
review. No missing post or failed fetch closes a saved job. A fetch is an
observation, not proof that an employer still accepts applications. `updated_at`
is the provider's update time, not a publication date.

HTML becomes plain text; no embedded content is opened or executed. Imported
posting text retains board/post identity, source URL, update/location labels and
a hash of normalized source-record JSON. The raw response hash/time are shown
for the current fetch but the complete raw response is not stored in the shelf.
This is traceability, not authentication or a full source archive. The adapter
rejects incomplete/malformed/oversized responses rather than importing a subset
silently. One board per explicit fetch, 8 MiB response cap; no cross-site scraping,
automatic polling, global search or bulk applications.

## Optional AI quote proposals

Open a posting's **Review evidence → AI: propose exact requirement quotes**.
Review the **exact JSON request** first. Only this posting is included; your
career profile, resumes and application notes are excluded. Enter your own key
in the masked session field and authorize this one request. Press **Send reviewed
request** to contact OpenAI Responses using `gpt-4.1-mini`, a 2048-output-token cap
and structured quote JSON. No tools, redirects, automatic retries or execution.
The key is used in the authorization header, never written to the database,
settings or logs, and cleared when the dialog closes. It is not a secure-memory
erasure guarantee. The application never obtains a key from files or environment.

API charges may apply; a ChatGPT subscription does not establish API access.
`store=false` requests no response storage for later API retrieval; it does not
promise zero provider retention. Cancel/close discards local results and requests
cooperative cancellation. It cannot undo provider processing or charges. The UI
has a 60-second local deadline and bounded responses; underlying DNS/OS I/O can
outlive cancellation. Never send employer-confidential or unauthorized material.

Proposals must be exact contiguous substrings of the posting. Invented wording,
duplicate quotes, malformed JSON, refusals, tool calls and incomplete results
are rejected. **Exact does not mean relevant**: a posting can contain malicious
instructions or unrelated prose. Inspect each selected quote and check review
before adding it to the unsaved evidence draft. No fact links, qualification
scores, resume changes or database writes occur automatically. Save the reviewed
snapshot yourself; original snapshots remain preserved. AI quality and account
access are unverified until an authorized live trial.

## Calendar files without account linking

Record an active follow-up date in **Application notes / follow-up**. Then choose
**Export saved follow-up to calendar (.ics)** and a new filename. Pending edits
must be recorded/discarded first. It exports one private all-day event with job
title/company, date, saved-review ID, stage and history revision. Application
notes, profile, resume and source URL are excluded. The file is unencrypted.

Import the file yourself in a calendar you choose. RoleWeave does not link an
account, upload the file, send invitations, set alarms or modify a remote event.
Re-export after a date change: UID stays stable for the same saved review and
SEQUENCE increases with history revision. Calendar apps differ in update/duplicate
handling; a later import is not guaranteed to replace the earlier event. Closed,
withdrawn or undated follow-ups are not exported. Previously imported calendar
events are not removed when a stage/date changes in RoleWeave.

## Verification and first principles

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python desktop.py --self-test out/connected-smoke
```

Use a new self-test folder. The runtime smoke uses synthetic discovery and AI
proposals; it never makes a provider call. On 4 November 2026 one separate public
GET through the adapter returned 20 Greenhouse vacancy posts. No candidate data
was sent. This is evidence for that response only, not all employer boards.

For your 60–90 minute exercise, use a synthetic practice shelf. Predict what gets
sent to each provider; explain why an exact quote could still be irrelevant.
Inspect the request preview without sending. Save a follow-up, export an ICS,
change the date, export another and compare UID/SEQUENCE/DTSTART. Finally restore
a backup into a different shelf. Tradeoff: explicit requests and human review
take more effort than automation, but keep source selection and candidate claims
under your control. Learning is not complete until you practise it.

Contracts checked against official sources:

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board): public GETs,
  content inclusion, post/internal IDs and prospect posts.
- [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs),
  [Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create)
  and [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
- [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545): UTF-8 folding, escaping,
  all-day exclusive end dates, UID and sequence.
