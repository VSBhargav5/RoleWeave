# From evidence to an application observation

Use 60–90 minutes with synthetic data, not private career or employer material.
Nothing in this exercise sends an application or contacts a model provider.

From the project folder, start a separate practice shelf:

```powershell
python desktop.py --db private/workflow-practice.db
```

1. Enter a synthetic title and company, then import `examples/synthetic.json`.
   Open it. Predict why Python has selected evidence but Spark needs review.
   A linked project claim does not establish production employment experience.
2. Open Application notes. Record `shortlisted`, a note asking whether remote
   work is permitted from India, and today's calendar date as follow-up. Check
   the stage and due-date filters. The note records a question, not its answer.
3. Add a second observation correcting the stage. Inspect the earlier entry:
   it is still present. Revisions order observations; a computer clock changing
   does not make an earlier entry the current state.
4. Export a preparation pack to a new filename. Find the exact quote, selected
   claim, source hash and history revision. Confirm Spark remains an open review
   question. This file prepares you to make a decision; it proves no submission.
5. Review evidence and correct a synthetic claim. Predict which links disappear.
   Save the revised snapshot. Its stage is `saved`; the original keeps its own
   history. This avoids claiming changed evidence was already submitted, at the
   cost of keeping snapshot histories separate. Do not count them as two real
   applications automatically.
6. Back up the full shelf. Start `python desktop.py --db private/workflow-restored.db`
   in a second terminal, restore, and compare source bytes, metadata and history.
   Restore a second time: identical records are skipped. A conflicting event at
   the same revision is rejected rather than silently combined or overwritten.
7. Edit a posting without saving, then try switching jobs or exporting its pack.
   Decline discarding the draft. Confirm that your unsaved text is still present.

To verify the engineering without using the app interactively:

```powershell
python -m unittest discover -s tests -v
```

Explain this tradeoff: why should correcting a fact create a separate saved
review instead of silently changing the evidence attached to an `applied` entry?
Practice and personal usefulness are not established by the tests or this document.
