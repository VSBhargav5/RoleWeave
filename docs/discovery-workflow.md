# Discovery workflow (v0.7)

Open Public job discovery, choose greenhouse, lever, lever-eu or ashby, and enter
the employer board token and your checked employer label. Alternatively use
Observation tools → Use employer board URL. The URL must identify a supported
board, without a job ID, query, credentials or fragment. Resolution is local;
Fetch is a separate explicit action.

Each fetch is one unauthenticated bounded HTTPS GET to the selected provider.
Your profile, resumes and API key are not sent. No redirect/retry/background scan
is performed. Search titles/locations locally; opt in to description search and
use an optional literal exclusion phrase. Counts describe observed posts only.
Choose the market yourself; a remote/hybrid label does not establish eligibility.

Select and preview one posting before importing it. Imports retain record identity,
provider labels and the normalized record hash. An identical review is refused;
changed records become new immutable snapshots with separate application history.
A feed fetch never changes stages or interprets a missing listing as closure.

## Preserve and compare observations

Observation tools → Save observation stores the original response bytes, provider,
token, observation time and SHA256 in a private JSON archive. Output filenames
must be new. Open saved observation replays it offline after hash/contract checks.
It clears the employer label; confirm the board's identity before importing.
Archives are unencrypted and are separate files, not included in a shelf backup.
Integrity checks do not establish source authenticity or current availability.

Compare observation loads an earlier archive from the same provider and token.
The window lists added, changed, unchanged and not_observed IDs. It neither updates
applications nor claims a disappeared posting closed. Provider time labels differ:
Greenhouse updated_at is not publication date; Ashby publishedAt is last published;
this Lever adapter supplies no date and does not invent one.

## Supported provider contracts

Verified against current official documentation on 10 November 2026:
[Lever Postings API](https://github.com/lever/postings-api) and
[Ashby public Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api).
No upstream implementation code is imported.

Lever global/EU use separate hosts and explicit region selection. descriptionPlain,
extra lists, closing text and salary-description text are preserved. The response
cap is 8 MiB; 1000 or more returned Lever posts are refused as potentially
truncated. Pagination/complete-board coverage is not claimed.
Ashby accepts API version 1 and explicit isListed booleans. Unlisted records are
excluded. Job URL supplies identity because the documented public contract does
not require an ID field. Secondary location labels are retained. Missing/unsupported
required content fails closed. Provider salary numbers are not normalized or scored.
Live new-provider feeds and complete real-employer compatibility remain unverified.

## Offline verification and practice

From the repository, with the existing test requirements installed:
```powershell
python provider_boards.py --provider lever --token synthetic --input examples/lever-synthetic.json
python provider_boards.py --provider ashby --token synthetic --input examples/ashby-synthetic.json
python -m unittest discover -s tests -v
python desktop.py --self-test out/new-discovery-smoke
```

The CLI requires either explicit --fetch or an offline --input. Use a new self-test
folder. A focused 60–90 minute exercise: predict which Ashby fixture is excluded,
find SQL through description search, save/reopen an observation, change one
description in a separate fixture, and compare two saved observations. Explain
why a byte hash detects modification but cannot prove authenticity or eligibility.
Learning and personal usefulness require your practice; shipping does not prove them.
