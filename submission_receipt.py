"""User-reported submission observations referencing prepared dossier evidence."""
from datetime import date

from application_dossier import JOB_FIELDS, verify_dossier_bytes
from applications import current_application, follow_up_date
from roleweave import text

CHANNELS = ("Employer portal", "Email", "Referral", "Other")


def record_submission(store, job_id, dossier, submitted_on, channel, reference, note, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Explicitly confirm your own submission observation")
    follow_up_date(submitted_on)
    if not submitted_on or date.fromisoformat(submitted_on) > date.today():
        raise ValueError("Use an observed submission date, not a future date")
    if channel not in CHANNELS:
        raise ValueError("Choose a submission channel")
    for value, label, limit in ((reference, "Reference", 1000), (note, "Observation", 1800)):
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError(label + " exceeds its text limit")
        if value:
            text(value, label)
    report = verify_dossier_bytes(dossier)
    item = store.load(job_id)
    if report["job"] != {key: item[key] for key in JOB_FIELDS}:
        raise ValueError("Dossier belongs to another exact saved review")
    message = ("USER-REPORTED SUBMISSION (not independently verified)\n"
               f"Observed submission date: {submitted_on}\nChannel: {channel}\n"
               f"Your reference: {reference or 'Not recorded'}\n"
               f"Prepared dossier SHA256: {report['sha256']}\n"
               f"Frozen resume version: {report['resume_id']}\n"
               "Dossier reference does not prove which files were sent.\n"
               f"Your observation: {note or 'No additional note'}")
    # Preserve the current follow-up explicitly; history is append-only.
    history = store.application_history(job_id)
    if any(event["stage"] == "applied" and event["note"] == message for event in history):
        raise ValueError("This exact submission observation is already recorded")
    current = current_application(history)
    return store.record_application(job_id, "applied", message, current["follow_up"])
