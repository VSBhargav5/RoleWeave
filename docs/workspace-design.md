# The Windows workspace

Version 0.5 keeps the existing Tkinter/SQLite application and introduces a shared
visual language: a navy navigation rail, teal primary actions, pale canvas, white
cards and Segoe UI typography. No web server, browser shell, theme package or
new runtime dependency is needed.

The left rail holds **Job workspace**, **Discover jobs**, **Career profile** and
**Resume studio**. Backups, restore and the synthetic practice guide live below.
The summary cards show global saved-review snapshots, active follow-ups through
today and frozen resume versions. These are stored observations, not verified
applications or hiring outcomes; filters do not change the global counts.

The opportunity list searches/filter results separately and puts job titles
first. Scrollbars expose long rows and lists. An empty search explains that no
reviews match; it does not erase the currently opened review or its unsaved draft.

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

Profile, resume, discovery, AI and tracking dialogs use the same palette, fields
and primary-action treatment. The main workspace supports a minimum 1040×700
logical pixels; the evidence editor requires 800×700 so its Save action cannot
be resized off the bottom. Other dialogs retain their existing minimum sizes.
Logical pixels are scaled by Windows display settings. Very small displays or
unusual text/display scaling still need user acceptance testing.

Existing private databases and v1/v2/v3 backups remain supported. No data migration
or provider behavior change is introduced. The local launcher opens the refreshed
portable executable when present. Extract the complete portable folder when
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
primary actions fitting supported window sizes. Packaged smoke uses synthetic
discovery/AI results and makes no paid/provider call.

For a focused 60–90 minute practice session, open the separate synthetic shelf.
Predict which values remain global when filtering to one market. Edit a posting,
switch tabs and confirm the draft survives. Record a due follow-up and check the
card, then save a reviewed resume and check its count. Finally restore a backup
into another practice shelf. Explain why “saved reviews” cannot be relabeled
“applications sent.” Practice/personal usefulness remain unverified until you try.
