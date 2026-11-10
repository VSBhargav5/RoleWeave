"""Record only a user-reviewed exact email excerpt as a manual job observation."""
from applications import current_application
from mail_observation import mail_observation
from roleweave import text


def record_correspondence(store, job_id, source, quote, note, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Review the source and confirm this correspondence observation")
    observation = mail_observation(source)
    text(quote, "Selected email excerpt")
    if len(quote) > 1400 or quote not in observation["body"]:
        raise ValueError("Choose an exact email body excerpt of at most 1400 characters")
    if not isinstance(note, str) or len(note) > 1000:
        raise ValueError("Your note must be at most 1000 characters")
    if note:
        text(note, "Your note")
    store.load(job_id)
    def label(value):
        return value if len(value) <= 200 else value[:200] + " [header truncated]"
    headers = "\n".join(key + ": " + label(value) for key, value in observation["headers"].items())
    message = ("USER-REVIEWED CORRESPONDENCE (sender/identity not authenticated)\n"
               f"Original email byte SHA256: {observation['source_sha256']}\n{headers}\n"
               "Selected exact body excerpt:\n" + quote + "\nYour observation:\n" + (note or "No additional note") +
               "\nOriginal email/attachments are not stored in the shelf.")
    history = store.application_history(job_id)
    if any(event["note"] == message for event in history):
        raise ValueError("This exact correspondence observation is already recorded")
    current = current_application(history)
    return store.record_application(job_id, current["stage"], message, current["follow_up"], expected_revision=len(history))
