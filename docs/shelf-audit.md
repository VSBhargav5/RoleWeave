# Read-only shelf audit (v0.10.1)

SQLite's quick_check detects storage-structure problems. A structurally valid
file can still contain changed source bytes, stale profile pointers, orphaned
application events or resume references to the wrong review. The separate
**Evidence & next steps > Review files > Audit saved sources and references**
action validates those stored contracts in one read-only transaction.

The audit checks all saved review fingerprints/market/metadata, profile and
resume source fingerprints and payload contracts, resume-to-profile and exact
resume-to-job references, active profile availability, and contiguous valid
application history. It never repairs, migrates, creates a missing database,
changes a stage, generates a backup, or contacts a service. Full source texts,
claims and notes are excluded from the optional private JSON report; IDs and
issue codes remain private. Existing output filenames are refused.

The read budget is 10000 total rows and 64 MiB of stored field bytes, including
all settings. Bigger shelves fail closed before payloads are loaded. An audit
can occupy the UI briefly; large-shelf performance is not measured. Close other
workflows before auditing for a clearer operational review, although the read
transaction itself checks a single consistent SQLite snapshot.

```powershell
python shelf_audit.py C:\private\practice\jobs.db
python shelf_audit.py C:\private\practice\jobs.db --output C:\private\audit.json --confirm
python -m unittest discover -s tests -p test_shelf_audit.py -v
```

Exit 0 means these stored checks passed; exit 2 means issues were found. A format,
structure or budget error fails without a report. Preserve an affected database
and use a separately verified backup/recovery workflow; the audit does not repair
or establish recoverability. Do not modify a personal shelf to test corruption;
regression tests deliberately change only disposable synthetic databases.

Passing fingerprints do not authenticate claims or source history. The audit
checks stored PDF bytes/hash contracts, not renderer replay or visual layout.
Separate dossiers, journals, watchlists, archives and exported recipient files
are outside the shelf and outside this check. No completeness, ATS, hiring or
learning claim follows from a pass.
