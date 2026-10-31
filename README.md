# RoleWeave

A personal Python job-search workspace for Data Engineering and applied AI roles.
Two separate markets: India/remote-from-India and international relocation.
Original implementation inspired by existing tools, with no upstream source,
assets or history imported. Early command-line foundation; no desktop UI yet.

## Run today

Python 3.11+; no dependencies, API keys or server:

```powershell
python roleweave.py examples/synthetic.json
python -m unittest discover -s tests -v
```

The synthetic example links a Python requirement to a reviewed project claim
and leaves production Spark experience as an open review item. It never converts
a project's tests into employment experience. Edit a requirement quote: a quote
absent from the posting is rejected. Change `market` to `relocation`: that review
stays separate from the India market.

Inputs contain a posting, manually extracted requirements, career facts and
human-selected links. Output checks exact quotes, IDs and reviewed flags, and
includes byte-snapshot and posting hashes. A reviewed flag is a user's assertion,
not independent verification. A link does not prove relevance or qualification.
Unlinked requirements need review; they are not automatically missing skills.
No score, ATS prediction, hiring probability, automatic extraction or tailoring.

Keep private career files under ignored `private/`, outside public Git history.
The program only reads your explicit input and prints JSON to your terminal;
redirecting output can store private data. It makes no network/model calls and
does not submit applications or contact anyone. Input is bounded to 1 MiB.

See [research and phased plan](docs/research-and-plan.md). The next useful slice
is a local SQLite store and a small Windows interface for editing these reviews.
This is not yet a usable full job-search application or evidence of superiority.
