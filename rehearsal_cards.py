"""Pure source-bound rehearsal prompts; no grading or generated career claims."""
from roleweave import review_snapshot
import re

PRACTICE_PROMPT = "Explain a relevant example for this exact requirement. Distinguish project practice from employment."


def suggested_requirements(posting):
    """Local suggestions only; each remains an exact, human-reviewed source quote."""
    result=[]
    for line in posting.splitlines():
        for part in re.split(r'(?<=[.!?])\s+',line):
            quote=part.strip().strip('*•- \t')
            if not 20<=len(quote)<=1000 or quote in result:continue
            if re.search(r'compensation|salary|vacation|benefits|401\(k\)|equal opportunity|privacy|personal data|we are pioneers|we are shaping|our mission|best places to work',quote,re.I):continue
            if re.search(r'\b(?:experience|proficien\w*|expertise|hands.on|knowledge|familiarity|design\w*|develop\w*|implement\w*|maintain\w*|build\w*|optim\w*|debug\w*|collaborat\w*)\b',quote,re.I):result.append(quote)
            if len(result)>=30:return result
    return result


def practice_cards(item):
    result = review_snapshot(item["snapshot"])
    if result["input_sha256"] != item["input_sha256"]:
        raise ValueError("Practice source fingerprint mismatch")
    return [{"requirement_id": row["id"], "quote": row["quote"], "prompt": PRACTICE_PROMPT,
             "evidence": "\n\n".join(f"{fact['claim']}\nSource: {fact['source']}" for fact in row["evidence"]) or
                         "No evidence linked. Review this open question; do not invent an example."}
            for row in result["requirements"]]
