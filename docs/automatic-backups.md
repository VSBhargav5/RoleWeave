# Automatic local recovery (v0.35)

The saved profile, reviewed documents, source observations and application history
should not depend on remembering a manual export. Settings & backup now has an
opt-in daily recovery schedule and an inspect-before-restore list. Off by default.

## What it does

Enable the checkbox and explicitly accept unencrypted local storage and retention.
The running local host checks every30seconds. The cycle changes at02:00 in the
machine's current local timezone. A missed cycle is captured when the host next
runs; it does not replay a burst of every missed day. A successful cycle is not
repeated automatically. Create recovery snapshot now is an explicit additional
capture. Disabled schedules create nothing and do not delete existing snapshots.

No Windows Task Scheduler job, login registration, service, laptop wake, cloud
upload or background operation after the local host exits. Closing just the
browser tab leaves the host running, as before. Machine clock/timezone changes
can change the displayed cycle; each file also keeps its UTC capture timestamp.
Failures wait at least15minutes before another scheduled attempt, including
restarts. Shutdown or disabling drops a not-yet-published capture; an operation
already publishing can finish before the preference change returns.

Each ZIP reuses the existing managed recovery contract: database records, reviewed
profiles/resumes, saved managed drafts/letters/packets/rehearsals, model preferences,
discovery queue and original managed source/import bytes. It excludes unsaved edits,
external exports, separate unmanaged files, recovered workspaces and earlier backup
ZIPs. Backup preferences themselves are deliberately not transferred. Restored
workspaces start disabled and require renewed retention consent.

## Publication and retention

The fixed automatic-backups folder is beside that workspace's database. No arbitrary
backup destination or path traversal. Up to64MiB per stored ZIP, as for manual
managed exports; at most1,000 managed source artifacts. Existing snapshot bytes are
fingerprinted and fully inspected before publication/retention. The new payload is
validated, closed and atomically published without overwrite using the existing
hardlink-based exporter, then read back and inspected. Unsupported storage fails
closed. Nothing is called successful before readback verification.

After a new verified snapshot, retain it plus six latest older snapshots. Clock
rollback never deletes the just-created snapshot or regresses the recorded cycle.
Only recognized, reverified managed files in that exact directory can be pruned;
linked, unexpected, excessive, malformed or damaged entries stop the operation.
No repair or recursive deletion. A retention failure is distinct from capture
failure: the new verified snapshot remains and the same cycle is not retried.
Seven ZIPs can use448MiB at the size limit; interrupted publication/retention may
leave extra or staging files and pause automatic operation. Check the disclosed
folder before retrying; private files are never silently cleaned up.

This is a single local-host workflow, not a cross-process distributed scheduler.
Snapshots and ZIPs are unencrypted and on the same device: they do not protect
against device loss, ransomware or arbitrary corruption. Keep a separate trusted
copy. Fingerprints prove byte consistency, not authorship, truth or recoverability
under every failure. A real overnight/sleep/power-loss trial is still unverified.

## Inspect and restore

Download snapshot ZIP exports the exact reverified snapshot for a separate trusted
copy. Choose Inspect & restore snapshot. RoleWeave rechecks the filename fingerprint,
ZIP manifest, domain records and source bindings before showing the standard
recovery summary. Confirming creates a separate recovered workspace. The current
workspace is not replaced. An invalid snapshot cannot be restored through this
flow. Existing downloaded manual bundles keep their existing workflow.

## Focused practice (60–90 minutes)

Use Offline practice. Predict which records enter the ZIP, then enable the schedule
and wait for its catch-up snapshot. Create one more snapshot manually, disable the
schedule and verify both files remain. Inspect one and restore a separate workspace;
compare a saved profile and application, and confirm its schedule starts off.
Explain the tradeoff: same-device recovery is convenient but is not a second-device
backup. Practice and personal usefulness are not presumed completed.

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_automatic_backups.py -v
```

Tests inject aware clocks around02:00, missed days/restarts, rollback and cooldown;
exercise complete restore, seven-file retention, failed capture/publication/readback/
retention, invalid settings/files, explicit consent and overlapping/disabled/stopped
captures. The real synthetic browser flow covers consent, scheduled catch-up, manual
capture, disable preserving snapshots, narrow layout and separate recovery. No
personal workspace, live provider call, account or OS scheduler is used.

Implementation uses [Python Event wait/wake](https://docs.python.org/3.11/library/threading.html#threading.Event.wait)
and the existing workspace export/recovery validation rather than copying an open
SQLite file or inventing a second backup format. Storage/permissions and hardlink
support remain necessary; no measured performance claim.
