# Reviewed job-evidence assessments

Open a saved job -> Assess evidence. Choose up to20 reviewed career facts, inspect
the exact provider request/destination and authorize one send. Practice mode uses
fixed synthetic output without a model call. Existing provider/model settings apply;
keys/tokens stay in the one-request input/worker and are not stored or reused.
Main contact fields, private source notes and unselected facts are excluded. Typed
private information inside selected text is not scrubbed. Review payloads first.

The provider proposes an advisory0-100 score, summary, up to30 exact requirement
quotes, selected fact references, evidence statuses/reasons and up to10 questions.
Inspect original facts/source notes, correct the opinion, change evidence links,
remove unhelpful quoted rows and investigate unanswered questions. Supported rows
require selected references; references and your review are not proof of truth.
Editing clears confirmation. Explicit fresh accuracy/limited-meaning confirmation
is required before saving. An empty quoted scope cannot become a reviewed assessment.

Two distinct numbers are disclosed:

- Advisory score: an uncalibrated model opinion, editable by you. It is not a hiring
  probability, verified qualification, eligibility decision or validated fit score.
- Scoped evidence coverage: supported quoted rows divided by included quoted rows,
  using integer floor percent. For2supported of3quoted rows, predict66%. Quotes may
  omit requirements; this is not complete-posting coverage or a skills inventory.
  Not shown means absent from selected evidence, not absent from your abilities.

## Ranking and history

Role assessments compares one latest recorded version per **exact job review** in
one group. A group has the same profile snapshot bytes, selected fact-ID set,
provider/model/configuration and v1rubric. Different groups are never mixed into a
common ranking. Separate India/remote and relocation filters apply before pagination.
Twenty results/page; scores sort descending, with deterministic title/ID tie breaks.
This is a prioritization aid, not a calibrated comparison across different models,
profiles, selection sets, posting scopes or real-world outcomes.

Assessment history inside the job workspace shows every saved version for that
exact review, newest recorded timestamp first,20/page. Reopen read-only, inspect
its original request, selected evidence and source version, or start a new request
from those original sources. Another request needs another preview and consent.
A changed active career profile is never silently substituted. Saving an assessment
does not rewrite career facts, posting reviews, resumes or application stages.
Multiple review versions are not multiple real applications. Recorded time is not
verified event time and cannot establish personal usefulness or learning.

## Persistence and recovery

Explicitly saved records retain original request/proposal and corrected review in
web-artifacts/assessments. They are unencrypted and included in managed ZIP recovery;
shelf-only JSON backup excludes these files. Private text in a selected claim,
posting or your correction may appear there. Original credential input fields are
excluded. There is no automatic model retry, acceptance, background assessment,
application sending or arbitrary response execution.

The v1request replays byte-for-byte from its bound profile/job selection and provider
configuration during listing/recovery, alongside exact quotes/reference validation.
A rehashed request with unrelated candidate context is rejected. Fingerprints still
do not prove provider authorship or proposal truth. Restore only trusted backups.
Changing the v1request serializer/instructions requires a compatible versioned
contract; silently changing it can invalidate old stored assessments.

Exclusive staged file publication preserves existing output. If file publication
succeeds but cleanup fails, retrying the identical reviewed save reuses the frozen
pending ID/bytes; changed wording is refused while pending. After restart, an already
published record is discoverable by listing even if the earlier response was lost.
Limits:1MiB/record,256KiB request,20facts/40000claim characters,30quotes/10questions,
1000assessment files, existing64MiB managed recovery. Individual document/source
limits remain. No automatic pruning, secure erasure, authenticity, remote model
compatibility/quality, production performance, personal acceptance or hiring claim.

## Focused practice (60-90 minutes)

Use a separate synthetic workspace. Predict the disclosed request from two reviewed
facts, mark one uncertain quote supported by an appropriate selected fact, and
explain why a reference does not verify the assertion. Predict2/3 ->66%coverage.
Correct the advisory opinion, save, reopen, filter the two markets and inspect its
original source version. Create another assessment with a different model setting:
predict a different group, not a combined leaderboard. Export/recover and compare
record bytes. Tradeoff: strict source groups reduce misleading comparisons but
fragment your view after profile/model changes. Practice is not presumed complete.

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_job_assessment.py -v
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_model_providers.py -v
node tests/browser-workflow.cjs
```

See [browser prerequisites](browser-workspace.md). Local tests use synthetic data
and mocked providers; no paid call, personal transmission or account link is needed.
