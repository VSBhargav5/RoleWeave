# Google Calendar follow-up sync (v0.11)

Optional, explicit and one-way: one saved review's active follow-up becomes one
all-day reminder in a secondary calendar created by this OAuth app. There is
no background sweep, primary-calendar access, invitation, automatic deletion,
mailbox access, application submission or two-way local history change.

## Implementation and evidence

The engine uses a deterministic base32hex-compatible ID derived from the exact
saved review ID, so date corrections update the same reminder. Private ownership
properties bind it to the source fingerprint and history revision. Local state
is checked immediately before sending. Remote updates use PATCH plus the GET
ETag in If-Match; a conflict fails and requires another preview. A create conflict
also requires re-preview, not an automatic retry. This is not an atomic transaction
across SQLite and Google; local state can change while a remote write is in flight.

Default payload: generic `RoleWeave follow-up` title, all-day start/exclusive-end,
private visibility, transparent availability, no default reminders and source
hash/revision properties. Company/role title is an explicit opt-in. No career
facts, resume, posting, application note or email excerpt is sent. Private
visibility is not encryption. No attendees are created; existing invited,
recurring, cancelled, foreign or special events are refused.

Browser consent uses Google's maintained OAuth library, state validation and
PKCE, with a loopback callback bound to127.0.0.1 and45second consent wait. The
token exchange has a5second request timeout. Credentials stay in memory for this
window and are not automatically refreshed. Reconnect on expiry. No token,
refresh credential or client config is read from files/environment or saved to
the shelf. Closing/disconnecting locally does not revoke Google's grant, erase
remote events or guarantee memory erasure. Revoke in Google account settings
if desired. A cancelled consent can still finish remotely; no result is adopted
locally. A sent Calendar write may complete after cancellation or a lost response.
Inspect Google/re-preview before retrying, especially before creating a calendar.

Offline engine/native UI tests cover consent gates, payload privacy, stable IDs,
exact dates, stale local revisions, source ownership, remote ETags, malformed/
oversized responses, conflict/redirect refusal, one-shot sends and readable
minimum-size actions. Source/frozen self-tests exercise local preview only.
No real OAuth account, calendar creation or event write has been exercised yet.

## Set up your own Desktop OAuth client

A personal Google account or the chat's connected Calendar plugin does not supply
OAuth credentials to this desktop application. This is a separate application.
We have not created a Google Cloud project or linked an account for you.

Following Google's [Desktop OAuth instructions](https://developers.google.com/identity/protocols/oauth2/native-app):

1. In your own Google Cloud project, enable Calendar API and configure the OAuth
   consent screen. If the app is in Testing, add your Google account as a test user.
   Choose the **Desktop app** client type, not Web or service account. Review any
   billing/admin prompt yourself; do not enable a paid service merely for this test.
2. The required scope is only `https://www.googleapis.com/auth/calendar.app.created`.
   Google describes it as creating secondary calendars and seeing/changing/deleting
   their events. RoleWeave exposes no delete operation. It does not request access
   to your primary calendar or all existing calendars. Google may require consent
   configuration/verification depending on your project and distribution.
3. Copy the Desktop client ID and client secret into RoleWeave's session fields.
   Do not paste them into this chat, commit them, or put them in environment files.
   Desktop client secrets are public-client metadata, not a replacement for PKCE;
   they are still masked/cleared in this UI and not logged.

## First controlled trial

Open a separate synthetic practice shelf. Record/save an active future follow-up.
Select that saved review, then **Evidence & next steps > Review files > Google
Calendar follow-up sync**.

1. Connection tab: review scope, enter the Desktop client fields and check the
   scope consent box. Only **Connect in browser** starts OAuth. Review Google's
   actual account/scope screen before accepting. Connection alone creates nothing.
2. Deliberately create one separate RoleWeave Follow-ups calendar, or paste the
   ID of an existing calendar created by the same OAuth app. Copy the resulting
   ID for reuse: it is not stored across window closes. Repeated Create makes
   additional calendars; it is not a lookup/reuse operation.
3. Reminder tab: Preview local reminder sends nothing. Leave company/role off for
   the first trial. Check read consent, then **Read remote / prepare change**.
4. Inspect operation, target calendar, prior fields and exact proposed payload.
   Confirm this one change and **Send reviewed follow-up**. No automatic retry,
   redirect, deletion or local application stage change occurs.
5. Verify the all-day date and private generic title in Google. Re-preview should
   be unchanged. Correct the saved date locally, re-preview and confirm update;
   verify one event moved. Edit it remotely between preview/send: expect conflict.
6. Close/disconnect. The Google event remains. Closing/withdrawing a local job or
   clearing its follow-up refuses future sync; it does not delete the remote event.
   Remove obsolete reminders manually in Google after reviewing them.

Do not use personal job data until the synthetic trial and permissions are clear.
This live acceptance and your personal usefulness remain unverified.

## Reproduce offline verification

```powershell
python -m unittest discover -s tests -p "test_google_calendar*.py" -v
python desktop.py --self-test out/new-google-calendar-smoke
```

Official contracts inspected11November2026:
[scopes](https://developers.google.com/workspace/calendar/api/auth),
[secondary calendar creation](https://developers.google.com/workspace/calendar/api/v3/reference/calendars/insert),
[event creation](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert),
[conditional event changes](https://developers.google.com/workspace/calendar/api/v3/reference/events/patch),
[Google OAuth library](https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html).
PATCH consumes more API quota than GET+PUT; it keeps unrelated event fields out
of the change payload. Quotas, account policy and actual OAuth behavior need the
live trial. No timing, adoption or hiring outcomes are claimed.
