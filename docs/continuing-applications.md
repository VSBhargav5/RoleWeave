# Continue applications without starting over — v0.18

Current v0.19 flow: [resume import, application use and managed recovery](using-roleweave.md). Older database-only backup limitations below do not describe the new recovery ZIP.


## Return to a prepared application

Open Documents → Cover letters, or the exact saved job → Application kit. Read a
saved letter or download its TXT again, including after restarting RoleWeave.
Export application ZIP lets you select a PDF resume and an optional compatible
letter. Compatibility requires the same exact job review and frozen profile
version. A newer profile does not silently update an earlier letter or resume.
The ZIP contains only `resume.pdf` and, when selected, `cover-letter.txt`.
Private source records, notes and application history stay out.

Saved letter JSON is replayed against its embedded source facts and hashes before
listing or download. An invalid file produces a visible issue and is preserved;
it does not disappear silently or prevent the rest of the workspace opening.
Catalog inspection is bounded to1000directory entries/64MiB, with an explicit
incomplete-inspection notice at the limit. These files still live in private
`web-artifacts/letters` outside shelf backups. Preserve that directory separately
when moving computers. This iteration does not introduce an all-files backup.

## Browse more opportunities deliberately

Search by role/location, then use Previous page or Next page. Each click requests
one20-record page through the same query/filters. The explicit destination market
is retained. Edited search fields take effect only when you click Search jobs;
the result header states the query/country and offset actually used. A failed
request preserves the previous result and shows an error. Concurrent searches
are refused locally, rather than allowing an older response to replace a newer one.

The [FreeHire pagination contract](https://freehire.me/docs/api) uses limit/offset
and caps offset+limit at10000. The parser refuses conflicting reported offsets or
limits. Next-page eligibility uses the observed row count, including explicitly
excluded unsupported records, rather than just accepted records. It is capped at
offset9980. Source totals, ranking and page membership may change between requests;
pages can repeat or omit listings as a live source moves. An absent listing is
not proof it closed, and reaching a page boundary is not exhaustive coverage.

One generic public `data engineer`, country `IN`, offset20 check on13November2026
accepted20records and excluded0. The response reported offset20 and a next page.
SHA256: `af783c0748b260534b8f41672f69c38a0a8bd85016aaca5521e1ffce49189704`.
No personal information, account, paid call or application was sent.

## Keep the next action visible

Applications combines market, text (role/company/latest note/source URL), stage
and Due through today. Closed/withdrawn records are excluded from due filtering.
The matching count describes the current board; dashboard totals remain global.
Clear filters resets all four controls. Filtering does not change stages or data.

Update stage/reminder and Record my submission prefill the existing reminder.
Changing a stage therefore keeps it; clearing the date explicitly removes it.
Each save checks the exact tracking revision. If another window changed the
record, the save refuses and keeps your draft. Reload current tracking displays
the latest revision/stage/reminder/note, retains your input, and clears submission
confirmation. Compare the preserved draft against that latest state before
confirming and saving again. No automatic retry or submission is performed.

## Verification and focused practice

```powershell
python -m unittest discover -s tests -v
python desktop.py --web-self-test out/continued-web-check
python desktop.py --demo
```

Development browser verification (existing pinned Playwright setup):

```powershell
node tests/browser-workflow.cjs
```

The browser test reopens a letter after reload, selects it for a recipient ZIP,
preserves a reminder while changing stage, exercises stale tracking and retained
drafts, combines board filters, and navigates21synthetic results across two pages.
It also retains the earlier PDF/letter/ZIP/contact-filling and no-submit checks.

For60–90minutes of practice in a separate synthetic shelf: build a resume and
letter, reopen Documents, inspect the recipient ZIP's file list, set a reminder,
change only stage, and predict whether the reminder survives. Open two tabs,
change tracking in one and try the older form in the other. Explain why keeping
a draft is useful but applying it still requires reviewing the newer reminder.
This is an offered exercise; learning is not marked complete without practice.

The local workflow remains an unsigned controlled beta. Real installed-helper/
employer compatibility, personal acceptance, unusual scaling/accessibility,
signing/distribution and optional live Google/AI checks remain open. Resume-file
import and richer supported form controls remain possible next workflow work;
they are not represented as shipped here. Uploads, screening answers and final
submission remain explicit user actions.
