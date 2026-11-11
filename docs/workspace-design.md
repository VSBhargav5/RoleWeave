# The Windows workspace

Version0.12 refreshes the existing Tkinter/SQLite interface with an indigo accent,
midnight navigation rail, pastel metric cards, white bordered work surfaces and
stronger Segoe UI typography. Primary review actions, secondary buttons, active
tabs, stage badges and evidence/source text have distinct treatment. No web
server, browser shell, theme dependency or database migration is introduced.

The left rail holds **Job workspace**, **Discover jobs**, **Career profile** and
**Resume studio**. Backups, restore and the synthetic practice guide live below.
The summary cards show global saved-review snapshots, active follow-ups through
today and frozen resume versions. These are stored observations, not verified
applications or hiring outcomes; filters do not change the global counts.

The opportunity library uses two-line role/company rows with a separate manual
stage column. Rows carry actual immutable review IDs, so sorting/filtering cannot
redirect an action through a changed row index. Selecting a row reveals the full
review; long library labels can still clip in the compact pane, with original
values available in Job details. Active follow-ups through today use an amber
row treatment and retain their stated date; closed/withdrawn rows are muted.
No color or stage is a hiring/eligibility claim.

Search and **Go** remain visible. **Filters +** reveals market, stage, due-only
and full-posting options, keeping the default library uncluttered. Collapsing
filters preserves their values; a visible summary discloses the current scope.
Empty searches explain no matches without clearing the opened review or draft.
Global summary values remain independent of the filtered library.

For the selected review:

- **Job posting** gives the description a full reading/editing area.
- **Evidence & next steps** shows human-readable linked/open evidence. Application
  tracking and the **Review files** export/import menu are here.
- **Job details** edits title, company, source URL and the explicit market.

Choose **Add a job** to start in Job details, then paste the description in Job
posting. **Save posting only** creates an unlinked snapshot; use **Review evidence**
to preserve/edit reviewed requirements and facts. Save a reviewed snapshot to
return to the evidence tab. Earlier versions remain intact. Navigation between
tabs never saves or discards edits. Existing unsaved-change guards still apply.

The selected header shows its manual stage; the evidence tab reports requirement/linked/open counts without a match score. Linked/open headings retain explicit text labels with green/amber emphasis; source notes use a quieter type treatment.

Profile, resume, discovery, AI and tracking dialogs use the same palette, fields
and primary-action treatment. Packed dialogs reserve space for actions/status
before expandable reading areas; the career-fact tab separates its library from
the fact editor. The main workspace supports a minimum 1040×700
logical pixels; the evidence editor requires 800×700 so its Save action cannot
be resized off the bottom. Other dialogs retain their existing minimum sizes.
The initial window now fits within Tk's reported screen dimensions with explicit
space/position for chrome and taskbar, rather than letting a cascaded large
window hide its footer. The synthetic preview was visually inspected on the
available Windows display; this caught footer wrapping, heavy tab borders and
taskbar overlap that were corrected. Fresh user authorization limited computer
inspection to newly created synthetic previews. Some preview windows closed
between observations and GUI input reported no foreground process ID; no
personal window was controlled and no input-interaction acceptance is claimed.
Native regression tests separately verify navigation/layout/draft behaviors.
Very small displays or unusual text/display scaling still need acceptance.

Existing private databases and v1/v2/v3 backups remain supported. No data migration
or provider behavior change is introduced. The local launcher opens the refreshed
portable executable when present. Close older app instances and reopen the
refreshed package to see this design; an already running process retains its
loaded UI code. Extract the complete portable folder when
moving it; the build is unsigned and has no automatic updater.

## Verify the workflow

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python desktop.py --demo
python desktop.py --self-test out/new-design-check
```

Use a fresh output folder. Native tests cover unchanged workflow behavior,
global counts versus filters, draft-preserving tabs, resume-count refresh and
current-page actions staying visible, full-height and within supported window
sizes, including every dialog tab. Packaged smoke uses synthetic
discovery/AI results and makes no paid/provider call.

For a focused 60–90 minute practice session, open the separate synthetic shelf.
Predict which values remain global when filtering to one market. Edit a posting,
switch tabs and confirm the draft survives. Record a due follow-up and check the
card, then save a reviewed resume and check its count. Finally restore a backup
into another practice shelf. Explain why “saved reviews” cannot be relabeled
“applications sent.” Practice/personal usefulness remain unverified until you try.
