# Browser follow-ups and correspondence (v0.38)

Open a saved opportunity. The **Follow-up** card now contains the tools that
previously required the retired native window.

## Review a local reply

1. Choose **Review local reply**, then a permitted `.eml` file up to 2 MiB.
2. Read its plaintext and header labels. HTML and attachments are not opened.
   Headers do not authenticate the sender. HTML-only mail is unsupported.
3. Select text in the original body and choose **Use selected body excerpt**, or
   paste an exact excerpt of at most 1400 characters. Add your observation.
4. Review the storage checkbox and choose **Record reviewed excerpt**.

Only the exact excerpt, bounded header labels, source byte hash and your note
enter private application history and its backups. Original mail and attachments
are held only in memory, then discarded on successful save, dialog close or
ten-minute expiry. At most three previews can be held at once. A browser crash
may leave a preview until expiry. This does not guarantee physical memory erasure.

Stage and reminder date are retained. A concurrent tracking update refuses the
save; reopen the original file against refreshed history. An exact duplicate is
refused. Unsaved correspondence prompts before closing the dialog. There is no
mailbox connection, sender verification, automatic stage detection, reply model
call or send. Use the existing application email composer for a separate local
outgoing draft; nothing is sent automatically.

## Export a reminder without an account

Record an active follow-up date, then choose **Export calendar file**. The `.ics`
file includes company, role, date, review ID and history revision, with private
visibility. It excludes decision notes, email excerpts and career facts. Import
it into your calendar yourself. Corrections require a fresh export; duplicate or
update behavior depends on the calendar app. Closed/withdrawn jobs and missing
reminder dates are refused. Export does not change application history.

## Optional Google follow-up

Choose **Google Calendar follow-up → Preview local reminder**. By default the
title is generic; company/role is an explicit opt-in. Inspect the exact local
event. In offline practice this is the last step: no Google request is allowed.

In a regular workspace, follow the [Desktop OAuth setup guide](google-calendar.md)
using your own client. No credential file or environment configuration is read.
Enter client ID/secret, review the narrow app-created-calendar scope, and choose
**Connect in browser**. The fields clear after dispatch. Connection creates no
calendar or reminder. Session credentials remain in host memory for at most ten
minutes, with no automatic refresh or persistent token. Close/disconnect clears
the local session. Google grants and existing events remain until you manage
them in Google.

Paste an app-created secondary calendar ID, or separately confirm **Create
separate calendar**. Each confirmed creation makes a new calendar; inspect Google
after an uncertain result before retrying. Then confirm **Read remote and
prepare**, inspect the target/operation/exact payload, and separately confirm
**Send reviewed follow-up**. Changing the calendar field removes the displayed
plan. The host consumes each trusted plan once before dispatch. Local revisions,
remote ownership and remote ETags retain the existing engine checks. No automatic
retry, invitation, primary-calendar access, deletion or local stage change occurs.

Disconnect during consent/read/write discards late local results. A request
already sent to Google may still complete. Inspect Google before retrying after
cancellation, conflict or a lost response. Only one remote Calendar operation
runs per host at a time, including a cancelled operation still finishing.

## Verification and remaining scope

Focused offline regressions cover bounded uploads, session/origin checks,
excerpt/source/revision binding, duplicates, cleanup, late consent cancellation,
credential privacy, one-shot plans, unchanged events, ETag updates, remote errors,
calendar creation and private `.ics` output. The synthetic browser journey covers
actual local email recording and reminder export/preview; remote Calendar UI uses
mocked responses, while engine/session tests exercise the actual orchestration.

Real Google OAuth/account behavior, calendar-client import behavior and personal
usefulness still need user validation. This is one-way follow-up support; two-way
interview scheduling, Gmail, AI inbox replies, remote hosting/authentication and
external MCP are not implemented by this release.
