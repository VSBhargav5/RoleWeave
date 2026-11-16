# Workspace insights (v0.27)

Open **Insights** in the browser sidebar. Choose all markets, India/remote or
relocation, select a calendar month and refresh. This page reads one consistent
SQLite transaction and never changes a review, stage, reminder, profile or document.
It contacts no provider and has no account integration.

- Current stage: the latest explicitly recorded stage for each exact saved review;
  a review without history starts Saved.
- Ever recorded: each exact review counts once for every stage explicitly present
  in its history, plus its initial Saved state. Later stages do not imply earlier
  ones. Corrections remain historical observations. Bars need not be monotonic:
  this is not a conversion funnel or proof of employer outcomes.
- Weekly chart: first Applied observation per exact review, grouped by the recorded
  timestamp converted to UTC, Monday-inclusive/next-Monday-exclusive. Twelve weeks
  through the current UTC week; future recorded dates do not increase the chart.
  Repeated Applied notes count once. Recorded time is not the real submission date.
- Month calendar: six Monday-first weeks, adjacent dates visibly muted, active
  reminders from the latest record only. Closed/withdrawn reviews are excluded.
  Select a date to inspect reminders and open its exact application. Agendas page
  at20 records. Dates are entered follow-ups, not inferred interviews. Overdue is
  strictly before the UTC today marker, separate from due today.

The market filter applies to every chart, calendar and overdue count. Existing
Overview totals remain global. Multiple immutable snapshots may represent one real
vacancy; these counts are saved reviews, not unique vacancies or independently
verified application counts. No learning, hiring or productivity outcome is inferred.

The month selector supports1900–2100. Insights refuse more than10000 reviews or
50000 history observations rather than showing partial counts. Invalid histories
are refused; this page is not a repair or source-authenticity tool. Private notes,
posting text and profile content are excluded from the response. No cached derived
state is persisted; refresh after changes in another tab. The latest host UTC date
is captured for each read; dates are not converted into an external calendar.

## Runnable verification and practice

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_workflow_insights.py -v
```

Tests cover first observations/corrections/repeated updates, timezone boundaries,
market separation, leap-month grids, latest reminders/closures, read-only behavior,
invalid history/query and a real10000-review capacity boundary. Browser verification
checks actual SVG bar dimensions under the existing restrictive security policy,
market/month filters,42day cells/leap day and responsive layout. No inline style or
third-party chart dependency is required. No personal acceptance is claimed.

In a separate synthetic practice shelf (60–90minutes), predict the count after
Applied→Interview→Saved on one review. Record those observations, compare Current
with Ever recorded, then add a reminder and close the review. Predict which calendar
entry disappears and why the weekly first-Applied count stays. Switch markets;
open a reminder and verify exact review identity. Tradeoff: immutable review counts
retain evidence and corrections, but need interpretation instead of claiming a
clean count of real-world applications. Practice is not marked complete for you.
