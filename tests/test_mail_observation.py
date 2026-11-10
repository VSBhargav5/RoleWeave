from email.message import EmailMessage
import hashlib
import unittest

from mail_observation import mail_observation, MAX_MAIL_BYTES


def synthetic_mail():
    message = EmailMessage()
    message["From"] = "Synthetic hiring <hiring@example.invalid>"
    message["Subject"] = "Synthetic interview discussion"
    message["Date"] = "Tue, 10 Nov 2026 09:00:00 +0000"
    message["Message-ID"] = "<synthetic@example.invalid>"
    message.set_content("Please suggest a time to discuss the data role.")
    message.add_alternative("<p>HTML is not opened.</p><img src='https://example.invalid/tracker'>", subtype="html")
    message.add_attachment(b"untrusted attachment", maintype="application", subtype="octet-stream", filename="do-not-open.exe")
    return message.as_bytes()


class MailObservationTests(unittest.TestCase):
    def test_plain_text_and_identity_are_preserved_without_attachment_execution(self):
        raw = synthetic_mail()
        result = mail_observation(raw)
        self.assertIn("suggest a time", result["body"])
        self.assertNotIn("img", result["body"])
        self.assertEqual(result["ignored_attachment_names"], ["do-not-open.exe"])
        self.assertEqual(result["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["headers"]["Message-ID"], "<synthetic@example.invalid>")

    def test_html_only_ambiguous_and_oversized_messages_fail_closed(self):
        message = EmailMessage()
        message.set_content("<p>HTML only</p>", subtype="html")
        for raw in (message.as_bytes(), b"From: one@example.invalid\nFrom: two@example.invalid\n\nBody",
                    b"x" * (MAX_MAIL_BYTES + 1)):
            with self.assertRaises(ValueError):
                mail_observation(raw)

    def test_attached_message_body_is_not_silently_treated_as_current_reply(self):
        outer = EmailMessage()
        outer.set_content("Current message.")
        forwarded = EmailMessage()
        forwarded.set_content("Forwarded attachment.")
        outer.add_attachment(forwarded)
        result = mail_observation(outer.as_bytes())
        self.assertIn("Current message.", result["body"])
        self.assertNotIn("Forwarded attachment.", result["body"])
