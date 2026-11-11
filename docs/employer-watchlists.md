# Employer watchlist foundation (v0.8.1)

V0.9 completes the selected-board collection workflow; see [current guide](selected-collections.md).

Use Evidence & next steps → Review files → Employer watchlists. Add a provider,
board token, employer label you checked, and your own default market. Update or
clear unapplied board edits before saving/using the watchlist. Duplicate
provider/token pairs are refused. A board's market default is your choice, not
evidence of work authorization or sponsorship; review it per job before importing.

Save as new JSON writes a portable private file and refuses existing filenames.
Open watchlist JSON reads/validates without network access. Included/excluded
phrases and optional description search are local saved filters. Open selected
board transfers those choices into the existing discovery window; explicitly
Fetch after reviewing the employer and market. Watchlists stay separate from
SQLite shelf backups. Preserve these JSON files yourself.

The Windows selected-board collection UI is now available in v0.9.
The completed source CLI can explicitly fetch1-5 chosen boards:
```powershell
python employer_watchlist.py examples/watchlist-synthetic.json
python watchlist_fetch.py YOUR_WATCHLIST.json --boards 0 1 --fetch
```
The first command is offline. Synthetic board tokens are fixtures, not live
employer choices; the second command should use boards you checked yourself.
Each GET uses the fixed supported provider host, no key/profile and no retries.
Source failures are returned explicitly alongside successful observations; they
never close jobs. Cancellation stops subsequent work. Total source bytes are
bounded to16MiB. The UI's task layer has a60-second deadline; the source CLI
checks its observation budget around each bounded provider call, not during an
already-blocked transport operation. No immediate hard60-second CLI guarantee.

Offline regression and source/package self-tests cover configuration validation,
draft preservation, local source reuse, explicit selections, cancellation,
partial failures and byte budgets. Live multi-board compatibility and personal usefulness remain unverified. Collection UI/archives/comparison are covered by the v0.9 synthetic workflow. No account integration, automatic scanning or submission is added.

Continue with the [current collection workflow and exercise](selected-collections.md). The v0.8 letter/dossier/submission/correspondence workflow remains available.
