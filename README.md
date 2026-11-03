# RoleWeave

A personal Python job-search workspace for Data Engineering and applied AI roles.
Two separate markets: India/remote-from-India and international relocation.
Original implementation inspired by existing tools, with no upstream source,
assets or history imported. Local Windows posting shelf plus an evidence-review CLI.

## Run today

Python 3.11+; no dependencies, API keys or server:

```powershell
python desktop.py
python roleweave.py examples/synthetic.json
python -m unittest discover -s tests -v
```

On Windows, open `Launch-RoleWeave.cmd` in File Explorer. Python 3.11+ with
Tkinter is required; no extra packages or credentials. If Tk is absent, enable
Tcl/Tk in your Python installation. The launcher keeps its console on failure.

## Save and reopen a job

1. Enter the job title, company, source URL if available, and choose its market.
2. Paste permitted posting text and choose **Save as new snapshot**.
3. Select a saved job on the left to reopen it. Filter India/remote and
   relocation separately. Neither label verifies work authorization or sponsorship.
4. To import the existing evidence format, enter title/company first, then choose
   **Import review JSON**. The JSON's market is retained. Select the saved job to
   see requirement quotes and selected evidence alongside the posting.
5. Export a selected job's original JSON to a new filename. Existing files are
   refused. This exports review bytes, not title/company/URL or the whole shelf.

Storage defaults to ignored `private/jobs.db`; `python desktop.py --db PATH`
chooses another SQLite file. Close the app before copying this database as a
backup. Exported JSON can be imported into a fresh shelf after re-entering job
metadata. Full database backup/restore has not been rehearsed.

Every Save appends a snapshot. Exact duplicates with the same job details are
rejected. Editing a saved posting creates a new snapshot with no requirements or
evidence links; the original imported review is preserved. Use **Review evidence**
instead to edit quotes and links while keeping original snapshots.
Hash checks detect changed source bytes on reopen; they do not prove
truth, eligibility, completeness or authenticity against a malicious database edit.
The database and exports are plain text/SQLite without encryption: keep them
private and outside public Git. The app makes no network calls or submissions.

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
The CLI only reads your explicit input and prints JSON to your terminal;
redirecting output can store private data. It makes no network/model calls and
does not submit applications or contact anyone. Input is bounded to 1 MiB.

See [research and phased plan](docs/research-and-plan.md). The next useful slice
is a user trial of saved postings and their reviewed evidence.
This is not yet a usable full job-search application or evidence of superiority.

## Review requirements and evidence

Select a saved job (or enter a new posting and job details), then choose
**Review evidence**. In the review window:

1. Select exact text in the posting and choose **Use selected posting text**,
   or paste an exact quote into the quote field.
2. Add a career/project claim and its source. Mark it reviewed only after checking
   it yourself. This checkbox is your assertion, not external verification.
3. Select the facts that relate to a requirement, then **Add requirement**, or
   select an existing requirement and **Update selected**. Unreviewed facts cannot
   be linked; leave a requirement unlinked when the evidence is still unknown.
4. **Save reviewed snapshot** appends a validated review. **Cancel** discards the
   draft. Quotes absent from the posting, unresolved form edits and invalid links
   block saving. Earlier snapshots and their original exports remain available.

Facts can be added here; editing/deleting an existing fact is not yet supported.
To correct a claim, add a corrected fact and update the relevant requirement links.
No model inference, eligibility score or qualification claim is produced.
