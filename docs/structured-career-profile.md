# Structured career profile

Career profile -> + Career entry creates a typed, human-authored evidence unit.
Choose experience, volunteering, projects, education, certifications, publications,
references, skills, languages or a custom Additional heading. Plain facts remain.
Edit, remove and move entries within their section. Review the whole entry, keep
it in the draft, then separately confirm and save a new profile version. Editing
an entry clears its review; editing a profile clears its save confirmation.
Switching sections preserves common fields only. A stale active-profile save is
refused transactionally, leaving the browser draft open; copy your edits before
reloading the latest profile. No automatic merge is attempted.

Dates are optional exact YYYY-MM strings; current/ongoing excludes an end month.
End/expiry cannot precede start/issue. No duration, employment, credential validity,
proficiency or eligibility is inferred. Up to200 structured entries fit inside
the existing1MiB profile bound. Claims are optional for structured entries only;
title/organization requirements depend on the chosen section. Generic facts still
require a claim. Source notes are private, required and never printed.

Preview printed content before selecting the reviewed entry for a resume or
letter. Selected entries include their metadata plus accomplishment text in TXT,
HTML and PDF; unselected entries and private source notes are omitted. The entire
entry is the selection unit, not an individual metadata field. Additional entries
can share a custom heading. Section order is fixed; entry order within each section
is editable. Old profile snapshots, plain facts and old preset layouts still replay.
Frozen documents and prior profile versions retain their original content after
later edits/removal. Job evidence reuse freezes full printed metadata with its
source/version identity. Managed workspace recovery preserves these snapshots.

Reference email/phone print **only when you select that reviewed reference entry**.
Structured email/phone fields are excluded from AI request context. This is not
PII detection: any contact details you manually put in accomplishment/context text,
posting or revision instructions can still be sent after payload review and consent.
Selected non-contact metadata is visible in the exact AI payload preview. AI wording
can change only the reviewed accomplishment text, never structured fields. A source
citation and review checkbox do not independently verify any assertion.

## Focused practice (60-90 minutes)

Use a separate synthetic practice workspace. Create a current role starting2025-01
and predict the printed month/Present line. Add a certification with an expiry and
try an end before its start. Edit the role and observe review reset. Add a second
role, move it above the first, save, reload, then remove it in a new version. Select
only the first role for a PDF and letter; predict which dates/source notes appear.
Export/recover the managed workspace and compare the frozen bytes. Do not use real
reference contacts for this exercise. Tradeoff: whole-entry selection is predictable
and source-bound, but removing one metadata field requires a new reviewed profile.
Practice and personal usefulness are not marked complete automatically.

## Runnable verification

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_career_entries.py -v
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_resume_theme.py -v
node tests/browser-workflow.cjs
```

Browser verification requires the documented Playwright environment in
[browser-workspace.md](browser-workspace.md). It exercises real typed controls,
review reset, printed preview, edit/order/removal, version save/reload and narrow
layout on synthetic data. No live model call, account or personal transmission.
No automatic resume structuring, rich-text editor, photo, arbitrary section
reordering, date localization, personal acceptance or Dossier-wide parity claimed.
