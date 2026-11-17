# Startup notices from Hacker News (v0.36)

Startup jobs is a keyless source alongside role/location search and selected
employer boards. Hacker News describes its jobs page as jobs at YC startups;
RoleWeave does not independently verify YC membership or employer identity.
This is the HN-listed startup subset, not the complete YC directory, Who is hiring
comment threads, verified eligibility or automatic applications.

## Observe, filter, review, save

Open Startup jobs, choose index positions and explicitly authorize observation.
One batch makes at most11 unauthenticated GETs: the public jobs index and up to10
numeric item reads. No profile, resume, local filters, account, cookies or key is
sent. No employer URL is fetched. New batches recapture the index, so positions
may shift, repeat or disappear. Index order is preserved, not treated as a stable
cursor or complete market search. At most200 indexed IDs are accepted.

Browse the observed batch. Title/location filters and optional description search
run locally against that batch only. Unsupported, unavailable, removed, wrong-kind
or oversized notices are counted explicitly; they do not establish closure. Some
source items contain only a title and destination: a notice is not represented as
a full description. Locations, remote eligibility, salary and sponsorship are not
inferred. The source time is item creation, not verified vacancy publication.

Review posting shows the exact normalized notice and its original HN permalink.
Enter an employer label you checked and choose India/remote or relocation, then
confirm. This saves a review; it does not apply or open an employer form. Continue
with the existing application workspace, reviewed documents and browser helper.
Unknown/non-HTTPS destination labels remain plain text; only the HN permalink is
the saved navigation source. No silent URL rewriting or automatic link following.

Repeated exact notice/title/company/market observations reuse a review. Changed
posting text or destination creates a fresh review without inherited Applied state;
different markets remain separate. Mutable votes/unrelated added API fields do not
manufacture new posting revisions.

## Evidence, replay and recovery

The bounded composite source snapshot contains the original index bytes and each
requested item's original response bytes, base64 encoded with individual SHA256
fingerprints. Requested item order/identity must match the exact captured index
slice. The composite and the existing discovery archive have their own byte hashes;
these are not the hash of a single provider HTTP response. The posting's relevant-
fields hash is normalized JSON over selected source fields, not raw-response proof.

Existing observation sessions, cancellation, local filters, archive download/replay,
comparison, import receipts, derived-review receipt inheritance and managed recovery
are reused. Replay automatically opens the appropriate source view. Imported notices
retain exact source archives/receipts; recovery replays and verifies their relation
to the saved posting. Missing or changed evidence fails closed. Backups therefore
include imported startup evidence. Hashes establish consistency, not authenticity.

A shared maximum of3 observations,20-minute expiry and one active fetch applies
across startup notices/employer boards. Close an old observation before another
batch if needed. Archive replay and returning to a retained observation make no
provider request. Archives/recovery are unencrypted. No background subscriptions,
automatic next batch, retries or complete-source/absence inference. A90-second batch
budget is checked before connection and between reads, with5-second socket timeouts;
it is not a hard real-time cancellation promise. Original index is limited to4KiB,
each item128KiB, composite2MiB, and normalized posting50000characters without
truncation. A response ending before its declared length is refused even if its JSON prefix
parses. A failed item GET rejects the new batch instead of accepting a partial
network traversal; known invalid item records may be counted/excluded.

## Current primary contracts and limited live check

Inspected17November2026:
- [Official HN API](https://github.com/HackerNews/API): v0 jobstories (up to200),
  numeric items, type=job, optional/dead/deleted records and HTML text.
- [Official HN jobs page](https://news.ycombinator.com/jobs): HN's YC-startup label,
  not a RoleWeave membership verification or full-directory claim.

One permitted public batch was read without profile/query data or employer fetches:
31 index entries,10 requested notices,10 accepted,0 excluded. Only metadata and a
composite fingerprint are recorded in [the sample evidence](evidence/hn-jobs-2026-11-17.json);
no real notice text is committed as a fixture. This checks that observation's
transport/shape, not current availability, usefulness or universal compatibility.
No personal data, paid call, account linking or application submission.

## Focused practice (60–90 minutes)

Use Offline practice. Predict the ten notices in positions1–10, then observe with
consent. Search Python in titles only (zero matches in this fixture); enable
Search descriptions too (ten matches). Enter a checked employer label, select
relocation and save one notice. Download/replay its archive with no new source
request, then observe positions11–20. Explain why index positions are not stable
page identities and why a short notice cannot prove a full requirement set. Restore
a separate managed backup and compare the original source receipt. Practice and
personal usefulness are not presumed completed.

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_startup_source.py -v
```
