"""Versioned human-authored career information; no inferred employment claims."""
import hashlib
import json

from roleweave import MAX_BYTES, text

SECTIONS = ("Experience", "Projects", "Education", "Skills", "Additional")
PROFILE_FIELDS = ("name", "headline", "email", "phone", "location", "links", "summary")
OPTIONAL_PROFILE_FIELDS = ("first_name", "last_name", "linkedin", "website")


def validate_profile(data):
    if not isinstance(data, dict) or not {*PROFILE_FIELDS, "facts"} <= set(data) or set(data) - {*PROFILE_FIELDS, "facts", *OPTIONAL_PROFILE_FIELDS}:
        raise ValueError("Invalid career profile fields")
    text(data["name"], "Name")
    for key in (*PROFILE_FIELDS, *(key for key in OPTIONAL_PROFILE_FIELDS if key in data)):
        value = data[key]
        if not isinstance(value, str) or len(value) > (6000 if key == "summary" else 2000):
            raise ValueError(f"{key} must be text within its length limit")
        if any(ord(char) < 32 and char not in "\n\t\r" for char in value):
            raise ValueError(f"{key} contains unsupported control characters")
        value.encode("utf-8")
    if not isinstance(data["facts"], list):
        raise ValueError("Career facts must be a list")
    seen = set()
    for fact in data["facts"]:
        if not isinstance(fact, dict) or set(fact) != {"id", "claim", "source", "reviewed", "section"}:
            raise ValueError("Invalid career fact fields")
        identifier = text(fact["id"], "Fact ID")
        if identifier in seen:
            raise ValueError("Duplicate career fact ID")
        seen.add(identifier)
        text(fact["claim"], "Claim")
        text(fact["source"], "Source")
        for key in ("claim", "source"):
            fact[key].encode("utf-8")
            if any(ord(char) < 32 and char not in "\n\t\r" for char in fact[key]):
                raise ValueError("Career fact contains unsupported control characters")
        if type(fact["reviewed"]) is not bool:
            raise ValueError("Career fact review must be a boolean")
        if not isinstance(fact["section"], str) or fact["section"] not in SECTIONS:
            raise ValueError("Choose a career fact section explicitly")
    return data


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def profile_snapshot(snapshot):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_BYTES:
        raise ValueError("Career profile must be bytes of at most 1 MiB")
    try:
        data = json.loads(snapshot, object_pairs_hook=unique_json)
        validate_profile(data)
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError) as exc:
        raise ValueError("Invalid career profile JSON") from exc
    return data, hashlib.sha256(snapshot).hexdigest()


def imported_career_facts(profile, selected_ids):
    """Freeze selected reviewed facts for a job; never overwrite older copies."""
    data, digest = profile_snapshot(profile["snapshot"])
    if digest != profile["snapshot_sha256"]:
        raise ValueError("Career profile fingerprint mismatch")
    if not isinstance(selected_ids, list) or any(not isinstance(value, str) for value in selected_ids) or len(set(selected_ids)) != len(selected_ids):
        raise ValueError("Select distinct career facts")
    facts = {fact["id"]: fact for fact in data["facts"]}
    result = []
    for identifier in selected_ids:
        if identifier not in facts or not facts[identifier]["reviewed"]:
            raise ValueError("Select existing reviewed career facts only")
        fact = facts[identifier]
        result.append({"id": f"career:{profile['id']}:{identifier}", "claim": fact["claim"],
                       "source": f"{fact['source']}\nCareer profile {profile['id']}, fact {identifier}", "reviewed": True})
    return result
