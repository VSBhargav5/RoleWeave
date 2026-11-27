# Employer-board discovery in the browser (v0.29)

Discover jobs remains the primary role/location search; no employer board URL is
required there. The optional Employer boards page now serves the existing direct
Greenhouse, Lever global, Lever Europe and Ashby contracts in the same browser UI.
It never opens the retired native window.

V0.39 accepts a supported public board homepage URL and detects the provider, or
a short employer board name with an explicit provider. The old word "token" meant
the public URL name, never a credential. The form now includes URL examples.
Explicitly confirm Fetch selected board. One bounded unauthenticated GET goes to the existing fixed host.
No profile/resume/API key/account is sent. No arbitrary URL, redirect, retry, scan,
submission or live model call. Practice uses clearly labelled local fixtures for
all four providers and never silently substitutes them in normal mode.

At most three ephemeral observations per host,20-minute API expiry; only one fetch
may run at once. Cancel stops accepting its result, but cannot undo a sent request.
Expired observations can be closed; new fetch/replay clears expired inactive slots.
Credentials are not involved. Closing the host discards unsaved observations; the
expiry is checked on API access/reservation, not a promise of timed memory erasure.

Browse one observation with20-row pages. Title/location filtering is local; opt in
to descriptions and optionally exclude a literal phrase. It does not refetch.
Review posting shows exact normalized source text. Supply the employer label you
have checked and choose India/remote or relocation, then confirm Save. Editing
those fields clears confirmation. A saved review has no Applied event. The app
does not verify employer identity, location eligibility, sponsorship or availability.

## Original evidence and repeat imports

Each import saves the exact observation archive and a receipt binding its saved
review/input fingerprint to the original provider row and archive hash. Unchanged
posting/title/employer/market imports reuse the same immutable review even when a
new observation has a different time. The first receipt/evidence stays authoritative;
a later archive can remain as additional managed evidence. Changed posting metadata
or a different market becomes a separate review, without inherited application history.
Evidence-link/fact-review revisions inherit the same original source binding in a
new exact-review receipt. Their own application history stays independent. Failed
derived-receipt writes can be retried without duplicating that review.

Archive and SQLite writes are separate, not a distributed transaction. A receipt
write failure can leave a saved review; an identical confirmed retry repairs the
missing receipt without another review. Existing conflicting files are refused,
never overwritten. Do not delete receipts or source files to force an export.

Managed recovery includes board-observations and board-imports, validates every
archive and replays reserved board-import posting bindings before reserving a
persistent recovered workspace. Missing/wrong receipts and changed source rows fail
even after a rehashed ZIP manifest. Reserved posting prefix RoleWeave board
observation v1 identifies this protocol. Database-only record backup omits these
artifacts and is not a complete board-source recovery; use the managed ZIP.
Archives/receipts are unencrypted, included in the existing1000file/64MiB bundle
limits. Receipts are at most16KiB; provider responses8MiB, observation archive12MiB.

Download observation JSON preserves its exact bytes. Replay validates a selected
trusted JSON locally, with no fetch. The provider/token/time/byte fingerprint is
retained, but the employer label and market must be reviewed again on import.
Compare two observations from the same provider/token: added/changed/unchanged/
not_observed. Comparison never changes saved applications. Not observed is not closed;
source hashes establish integrity, not authenticity or current availability.

## Supported contracts and limits

The existing parsers remain authoritative. Greenhouse requires returned count/meta
agreement and excludes prospect records; updated_at is not publication time. Lever
global/Europe use distinct fixed hosts, preserve description lists and refuse1000
or more posts as potentially truncated. Ashby requires apiVersion1/isListed and
excludes unlisted records. Unsupported/oversized individual descriptions refuse the
whole observation. No truncation, automatic pagination, complete-board or salary
normalization claim. Current official contracts rechecked16November2026:

- [Greenhouse public GET API](https://docs.greenhouse.io/job-board.html).
- [Lever Postings API](https://github.com/lever/postings-api).
- [Ashby public Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api).

No new live board request was made for this browser iteration. Earlier limited
public samples are historical evidence, not compatibility for all employers.
JSearch/Adzuna, startup sources and scheduled/AI-scored agent behavior remain absent.

## Reproducible check and focused practice

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_board_workspace.py -v
```

Sixteen targeted regressions cover all four offline practice providers, no-fetch
local replay/filtering, one explicit GET, cancellation/late results, bounded slots/
expiry, source/hash guards, unchanged/time-only repeats, independent markets,
changed records, partial-write retry, absence semantics and managed source recovery.
Actual browser verification exercises fetch/filter/review/save/download/replay/
comparison alongside existing Applications filters. A form-ID collision caught by
that journey was corrected; the two filters use separate identifiers.

In a separate synthetic shelf for60–90minutes, fetch the synthetic Lever board,
filter for SQL with/without descriptions and predict the results. Save once in each
market, download/replay the archive and predict which import reuses a review.
Compare observations and explain why absence does not establish closure. Recover
into a separate workspace. Tradeoff: explicit per-employer observations preserve
inspectable source boundaries, but are not an exhaustive cross-market search.
No learning or personal usefulness is claimed without your practice.
