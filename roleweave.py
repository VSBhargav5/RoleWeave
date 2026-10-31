"""Offline, human-reviewed requirement evidence. Python 3.11+, standard library."""
import argparse
import hashlib
import json
from pathlib import Path

MAX_BYTES = 1024 * 1024
MARKETS = {"india_remote", "relocation"}


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 50000:
        raise ValueError(f"{label} must be nonblank text of at most 50000 characters")
    return value


def review(data):
    """Check references and exact quotes, never infer qualification or truth."""
    if not isinstance(data, dict) or set(data) != {"market", "posting", "facts", "requirements"}:
        raise ValueError("Expected market, posting, facts and requirements only")
    if data["market"] not in MARKETS:
        raise ValueError("market must be india_remote or relocation")
    posting = text(data["posting"], "posting")
    if not isinstance(data["facts"], list) or not isinstance(data["requirements"], list):
        raise ValueError("facts and requirements must be lists")
    facts = {}
    for fact in data["facts"]:
        if not isinstance(fact, dict) or set(fact) != {"id", "claim", "source", "reviewed"}:
            raise ValueError("Each fact needs id, claim, source and reviewed")
        identifier = text(fact["id"], "fact id")
        if identifier in facts:
            raise ValueError("Duplicate fact id")
        text(fact["claim"], "claim")
        text(fact["source"], "source")
        if type(fact["reviewed"]) is not bool:
            raise ValueError("reviewed must be a boolean")
        facts[identifier] = fact
    rows, seen = [], set()
    for requirement in data["requirements"]:
        if not isinstance(requirement, dict) or set(requirement) != {"id", "quote", "fact_ids"}:
            raise ValueError("Each requirement needs id, quote and fact_ids")
        identifier = text(requirement["id"], "requirement id")
        if identifier in seen:
            raise ValueError("Duplicate requirement id")
        seen.add(identifier)
        quote = text(requirement["quote"], "quote")
        if quote not in posting:
            raise ValueError("Requirement quote is not an exact substring of the posting")
        refs = requirement["fact_ids"]
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            raise ValueError("fact_ids must be a list of strings")
        if len(set(refs)) != len(refs) or any(ref not in facts for ref in refs):
            raise ValueError("Unknown or duplicate fact reference")
        if any(not facts[ref]["reviewed"] for ref in refs):
            raise ValueError("Unreviewed facts cannot support a selected requirement")
        rows.append({"id": identifier, "quote": quote,
                     "state": "evidence_selected" if refs else "needs_review",
                     "evidence": [{key: facts[ref][key] for key in ("id", "claim", "source")} for ref in refs]})
    return {"market": data["market"], "posting_sha256": hashlib.sha256(posting.encode()).hexdigest(),
            "requirements": rows,
            "notice": "Selections are human assertions. References and quotes were checked; truth, relevance, eligibility and completeness were not verified. No hiring probability or ATS score."}


def read_review(path):
    with Path(path).open("rb") as source:
        snapshot = source.read(MAX_BYTES + 1)
    if len(snapshot) > MAX_BYTES:
        raise ValueError("Input exceeds 1 MiB")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    try:
        result = review(json.loads(snapshot, object_pairs_hook=unique))
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError) as exc:
        raise ValueError("Invalid review JSON") from exc
    result["input_sha256"] = hashlib.sha256(snapshot).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        result = read_review(args.input)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Review failed: {exc}\n")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
