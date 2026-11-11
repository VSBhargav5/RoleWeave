"""Pure source-bound rehearsal prompts; no grading or generated career claims."""
from roleweave import review_snapshot

PRACTICE_PROMPT = "Explain a relevant example for this exact requirement. Distinguish project practice from employment."


def practice_cards(item):
    result = review_snapshot(item["snapshot"])
    if result["input_sha256"] != item["input_sha256"]:
        raise ValueError("Practice source fingerprint mismatch")
    return [{"requirement_id": row["id"], "quote": row["quote"], "prompt": PRACTICE_PROMPT,
             "evidence": "\n\n".join(f"{fact['claim']}\nSource: {fact['source']}" for fact in row["evidence"]) or
                         "No evidence linked. Review this open question; do not invent an example."}
            for row in result["requirements"]]
