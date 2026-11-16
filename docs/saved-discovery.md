# Saved searches and review queue — v0.25

Open **Saved searches**. Create a named query with location, optional two-letter
country code, remote filter and an explicit India/remote or relocation market.
Saving/editing filters makes no provider request. Archive a search without deleting
its observations. Three named searches can be active; twenty retained configurations
are supported. Earlier runs retain their original filter/revision snapshots.

## Explicit run and review

**Run now** confirms the displayed filters, then reads only the first page (up to
20 observations). This is manual: no scheduler, AI score, auto-drafting or application
sending. Three run attempts per rolling24hours are allowed across saved searches,
including failed or cached attempts. This is a conservative local guard, not a claim
about the provider's quota; ordinary manual search remains a separate workflow.
A single run may be active. No automatic redirects/retries are added.

A repeated exact posting/URL/title/company/location/work-mode/post-date/source/market
retains its queue decision.
The same result found through another search records attribution. Changed posting
content, location/work-mode/post-date or a different market becomes a separate observation to review. Queue
states are pending, kept, dismissed and saved. Use **Keep for review**, **Dismiss**,
**Return to pending**, or **Review & save application**. Saving requires explicit
review of the exact posting/market and creates no submission event. When you choose Save, an existing matching canonical posting review is recognized
without duplicating it. New observations stay pending even if the description was
saved before; changed location metadata must not inherit acceptance. The canonical
application stores original description/title/company/URL/market; additional provider
metadata remains in the queue/source evidence.

Queue filters and20-card pages keep decisions readable. **Remove cached observation**
is available only for saved/dismissed entries. It preserves applications but forgets
that queue decision; a later run may show a dismissed posting again. A matching
saved application is recognized when you explicitly save the returned observation. This removal requires confirmation.

Failed/empty/partial results never close a job or erase prior decisions. Run history
shows observed/new/repeated/excluded counts and whether more source pages exist.
A successful first page is not complete coverage or proof of eligibility/sponsorship.
Provider-ignored filters/values fail closed. Lower-bound source totals do not hide
an available next page in ordinary manual search.

If the process stops during a run, its running record remains. Refresh and explicitly
**Mark interrupted** when appropriate. This does not undo provider processing. Late
results from that run cannot update the queue. There is no automatic resume/request.
A stale search/decision form is refused; refresh and review again before changing it.

## Storage and recovery

A companion `<shelf-name>.discovery.db` stores bounded transactional state separately
from the existing shelf schema: at most200 retained observations,100 recent runs,
20 configurations/3active and16MiB snapshot bytes. Capacity errors roll back the full
run, mark it failed and preserve prior decisions. Resolve/remove cached observations
explicitly to make space. Run history is bounded, not an unlimited audit archive.

Saving a candidate touches the shelf and companion separately. If the companion
commit fails after the shelf save, the application can already exist. Refresh/retry
recognizes that exact saved observation instead of creating another application.
This is idempotent recovery, not a distributed transaction. No submitted-stage claim.

Managed workspace ZIP includes `discovery.json` plus original provider-byte sources.
Recovery validates state, hashes, normalized postings/run summaries against source
bytes, and saved-application references before reserving persistent output. Old
bundles without discovery remain supported; old app versions cannot restore this
new optional member. Database-only JSON backups exclude companion discovery state.
The companion is private/unencrypted, included in managed recovery, not a cloud
account. Source hashes establish integrity, not source authenticity or truth.

## Provider scope

Reviewed16November2026: [FreeHire API](https://freehire.me/docs/api),
[personal/commercial use](https://freehire.me/jobs-api), [terms](https://freehire.me/terms).
Use the documented read API for your own personal/non-commercial workflow.
Offering its postings to other users requires the provider's plan; no paid plan,
authentication or billing is configured here. This implementation does not scrape
employer pages or bypass provider limits. Real saved-run compatibility and complete
coverage are not established by synthetic tests.

Offline practice has two clearly labelled fixed discovery observations; filters
are retained but do not simulate real search coverage. No provider/account/model
request occurs in that mode. Normal mode never silently substitutes fixtures.

## Practise and verify

```powershell
python -m unittest discover -s tests -p test_saved_discovery.py -v
```

Use a separate offline practice workspace for60–90minutes. Predict which fields
will be transmitted in normal mode, save filters, run, keep/dismiss/save one exact
observation and repeat. Predict which decisions survive. Recover a separate ZIP
and compare filters/decisions/source evidence. Explain why no match or failed fetch
does not prove closure. No learning/usefulness completion claimed on your behalf.
