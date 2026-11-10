"""Bounded local plaintext email inspection; attachments are never opened."""
import argparse
from email import policy
from email.errors import MessageError
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path

from roleweave import text

MAX_MAIL_BYTES = 2 * 1024 * 1024


def mail_observation(snapshot):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_MAIL_BYTES:
        raise ValueError("Email must be bytes of at most 2 MiB")
    try:
        message = BytesParser(policy=policy.default.clone(raise_on_defect=True)).parsebytes(snapshot)
        headers = {}
        for key in ("From", "Subject", "Date", "Message-ID"):
            values = message.get_all(key, [])
            if len(values) > 1:
                raise ValueError("Ambiguous repeated email identity header")
            value = str(values[0]) if values else "Not stated"
            text(value, "Email header")
            if len(value) > 2000:
                raise ValueError("Email header exceeds 2000 characters")
            headers[key] = value
        stack, count, bodies, attachments = [(message, 0)], 0, [], []
        while stack:
            part, depth = stack.pop()
            count += 1
            if depth > 20 or count > 100:
                raise ValueError("Email MIME nesting or part count exceeds supported limits")
            if part.get_content_disposition() == "attachment" or part.get_content_maintype() == "message" or part.get_filename():
                name = part.get_filename() or "Unnamed attachment/message"
                text(name, "Attachment label")
                if len(name) > 2000:
                    raise ValueError("Attachment label exceeds its limit")
                attachments.append(name)
                continue
            if part.is_multipart():
                children = part.get_payload()
                if not isinstance(children, list):
                    raise ValueError("Unsupported MIME structure")
                stack.extend((child, depth + 1) for child in reversed(children))
            elif part.get_content_type() == "text/plain":
                value = part.get_content()
                if not isinstance(value, str) or part.defects:
                    raise ValueError("Unsupported email body encoding")
                if value.strip():
                    text(value, "Email body")
                    bodies.append(value)
        body = "\n\n".join(bodies)
        text(body, "Inline plaintext email body")
        return {"source_sha256": hashlib.sha256(snapshot).hexdigest(), "headers": headers,
                "body": body, "ignored_attachment_names": attachments, "plaintext_parts": len(bodies)}
    except (MessageError, ValueError, LookupError, UnicodeError, RecursionError, TypeError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(("Email ", "Ambiguous ", "Unsupported ", "Inline ", "Attachment ")):
            raise
        raise ValueError("Unsupported or malformed plaintext email") from None


def read_mail(path):
    with Path(path).open("rb") as handle:
        snapshot = handle.read(MAX_MAIL_BYTES + 1)
    return mail_observation(snapshot)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", type=Path)
    args = parser.parse_args()
    print(json.dumps(read_mail(args.email), ensure_ascii=True, indent=2))
