# Selected employer collections (v0.9)

Open Employer watchlists, select1-5 board rows (Ctrl-click for multiple), and
choose Review selected boards. Opening the window never fetches. Explicitly
Fetch selected boards after reviewing the scope. Each successful source keeps
its original response bytes, fingerprint and observation time; failures are
shown separately. A failed source is not an empty board and never closes jobs.

Search included/excluded literal phrases locally, optionally across descriptions.
Select one observed posting, read its source preview and check the visible market
choice before importing. The saved board default is your earlier choice, not
an eligibility result. Each import creates an unreviewed immutable snapshot;
identical imports are refused. No batch applications or stage changes occur.

Observation tools → Retry failed sources only issues explicit GETs just for failed
boards. Successful observations are retained byte-for-byte with their older times.
The resulting collection can therefore mix observation ages. Read individual
source times; it is not a synchronized complete-board snapshot. Cancel discards
late task results. Errors/budget failure preserve the prior collection.

## Preserve, reopen and compare

Save private collection observation writes original source bytes, outcomes,
watchlist choices and current local view filters into a new JSON archive.
Open saved collection observation replays offline. The main Review files menu
also opens a saved collection without a watchlist editor. No API call occurs.
Archives are private/unencrypted and separate from SQLite shelf backups.

Compare with earlier saved collection compares all source observations, including
rows hidden by local filters. Sources are identified by provider and board token,
not your employer label or a bare job ID. Scope-added/unselected sources and
failed sources are not comparable. Only two successful observations can produce
added/changed/unchanged/not_observed posting results. Not observed does not
establish closure. Save comparison JSON preserves per-source fingerprints.

Export filtered observed shortlist CSV includes only matching metadata rows,
source fingerprints/times and selected/observed/failed-source counts. Full
posting text, career facts and application notes are excluded. Formula-like
prefixes are escaped; spreadsheet-client behavior is not separately verified.
No matching rows produces no file. A CSV is not a complete vacancy inventory.

All output paths must be new. Source responses are capped at8MiB each and16MiB
per collection; archives24MiB, comparisons/CSV8MiB. The UI has a60-second task
deadline. The source CLI checks its budget before/after bounded provider calls;
it cannot interrupt an already blocked transport immediately. No retries are
automatic. Hashes and replay detect modification, not provider authenticity,
source truth, eligibility, completeness or actual availability.

## Offline verification and one practice session

With the existing test requirements installed:
```powershell
python -m unittest discover -s tests -v
python desktop.py --self-test out/new-collection-smoke
python collection_archive.py out/new-collection-smoke/synthetic-collection.json
```

The self-test uses only synthetic data and needs a new output directory. Open its
synthetic collection through Review files for an offline Windows practice.
For60-90minutes, predict visible rows, change filters, export/reopen the archive,
inspect CSV members and compare a separate modified synthetic observation:
```python
import copy, json
from datetime import datetime, timezone
from collection_archive import read_collection_archive, archive_collection
from provider_boards import parse_source

old = read_collection_archive("out/new-collection-smoke/synthetic-collection.json")
new = copy.deepcopy(old)
record = json.loads(new["feeds"][0]["feed"]["source_snapshot"])
record[0]["text"] = "Changed synthetic title"
new["feeds"][0]["feed"] = parse_source(json.dumps(record).encode(), "lever", "synthetic")
new["finished_at"] = datetime.now(timezone.utc).isoformat()
archive_collection(new, "private/practice-changed-collection.json")
```
Create private/ if needed and choose a new filename. Then compare with:
```powershell
python collection_compare.py out/new-collection-smoke/synthetic-collection.json private/practice-changed-collection.json
```

Explain why a failed source cannot produce a closure finding, why retry preserves
different source ages, and why an archive hash is not an authenticity guarantee.
No learning completion is claimed until you practise. Live multi-board feeds,
manual dialogs/scaling, connected accounts, AI quality and usefulness remain
unverified. No paid call or personal transmission is used in implementation tests.
