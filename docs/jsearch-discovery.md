# One reviewed JSearch observation (v0.34)

FreeHire remains the default. Discover jobs now has an optional **JSearch ·
experimental** source. Select an explicit country, review the public URL, enter
one masked API key and authorize one page. Only search terms/filters are sent;
no profile, resume or application history. Do not put private material in terms.

The key is passed to a worker for one request and is not saved, reused, logged or
read from files/environment. This is not a memory-erasure guarantee. The fixed
HTTPS destination is api.openwebninja.com, x-api-key header, GET
/jsearch/search-v2, num_pages=1, country and work_from_home. No redirect, retry or
automatic next page. Your own provider plan/credits/terms apply; RoleWeave does
not subscribe, configure billing or promise a free request. This app has made no
live JSearch call. Account access, coverage, quality and response compatibility
remain unverified. FreeHire saved searches still use FreeHire only.

## Current contract and narrow parser

Inspected17November2026:
- [Official JSearch product/reference](https://www.openwebninja.com/api/jsearch)
- [Official RapidAPI reference](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch/playground/Job%20Search)
- [Official generated input manifest, pinned](https://github.com/OpenWeb-Ninja/openwebninja-mcp/blob/d0a8462e14b6e0a0bee345ed9c0ef8d0e969a5b8/src/generated/manifest.ts)

Current documented input uses cursor pagination. This adapter accepts only
status OK with data.jobs (up to10) and data.cursor (string/null). That response
envelope is a narrow synthetic contract, awaiting an authorized live check;
unsupported responses fail without saving rather than being reinterpreted.
A page has a60-second local read deadline,4MiB raw cap, five temporary
observations and ten-minute lifetime. No credential in result/status/error;
known literal/JSON/URL-decoded key echoes are refused, not arbitrary transforms.

Every row requires identity, employer/title/description, HTTPS application URL
and country label matching the requested country. Remote-only searches require
a true provider remote label. Unsupported rows are counted and excluded without
truncation. Country/remote labels are not eligibility or sponsorship evidence.
Provider IDs are hashed into bounded internal IDs; the original is preserved in
the raw response. Canonical posting text includes location/work-mode labels.
Changed title, company or posting creates a new review without Applied inheritance.
No complete-board, direct-employer destination, freshness or closure claim.

Original byte responses are retained base64 in a versioned snapshot with exact
filters, observed time and raw fingerprint. The wrapper has its own fingerprint.
On import, that wrapper joins unencrypted managed recovery; restore checks both
fingerprints and replays this parser. Hashes prove consistency, not provider
identity or truth. Up to five observed pages are kept in browser memory; returning
to a cached page makes no provider request. Expired sources require a new reviewed
request before saving. Closing/cancelling drops late results locally; it cannot
undo remote processing or charges. No automatic application or tracking mutation.

## Focused synthetic exercise (60–90 minutes)

Open offline practice, choose JSearch, type Python and choose India. Predict what
happens with no consent, then run the local fixture: two observations, not live
jobs. Next page opens another preview and does not send. Close it: the old page
remains. Run that page explicitly, return to the previous observation without
another send, then save one posting and inspect its source labels.

Trace filters → public URL → consent → worker → original bytes → normalized
posting → reviewed import. Explain why a fingerprint is not authenticity and why
reusing an observed page is cheaper but may be stale. Do not treat this exercise
as completed until you actually practice and explain it.

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_jsearch.py -v
```

The normal browser workflow also covers no-consent/no-send, explicit country,
cancellation preserving old results, two fixture pages, cached return, import,
small-screen overflow and the existing FreeHire/application/recovery flows.
