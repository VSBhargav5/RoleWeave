"""User-reported submission observations referencing prepared dossier evidence."""
from datetime import date

from application_dossier import JOB_FIELDS, verify_dossier_bytes
from applications import current_application, follow_up_date
from roleweave import text

CHANNELS = ("Employer portal", "Email", "Referral", "Other")


def _validate_submission(submitted_on, channel, reference, note, confirmed):
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


def _append_submission(store, job_id, message, follow_up, expected_revision):
    history = store.application_history(job_id)
    if expected_revision is not None and len(history) != expected_revision:
        raise ValueError("Application history changed. Reload saved tracking and review it before confirming again; your draft is retained.")
    if any(event["note"] == message for event in history):
        raise ValueError("This exact submission observation is already recorded")
    current = current_application(history)
    selected_date = current["follow_up"] if follow_up is None else follow_up_date(follow_up)
    # A historical receipt must not reset a later interview/offer/closed state.
    stage = current["stage"] if current["stage"] in ("interview", "offer", "closed", "withdrawn") else "applied"
    return store.record_application(job_id, stage, message, selected_date, expected_revision=len(history))


def record_submission(store, job_id, dossier, submitted_on, channel, reference, note, *, confirmed=False, follow_up=None, expected_revision=None):
    _validate_submission(submitted_on, channel, reference, note, confirmed)
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
    return _append_submission(store, job_id, message, follow_up, expected_revision)


def record_basic_submission(store, job_id, submitted_on, channel, reference, note, *, confirmed=False, follow_up=None, expected_revision=None):
    _validate_submission(submitted_on, channel, reference, note, confirmed)
    store.load(job_id)
    message = ("USER-REPORTED SUBMISSION (not independently verified)\n"
               f"Observed submission date: {submitted_on}\nChannel: {channel}\n"
               f"Your reference: {reference or 'Not recorded'}\n"
               "Prepared documents: not linked; no file transmission is verified.\n"
               f"Your observation: {note or 'No additional note'}")
    return _append_submission(store, job_id, message, follow_up, expected_revision)
