# Browser interview rehearsal — v0.23

Open a saved application and choose **Interview rehearsal**. Check 1–30 exact
requirement questions. Reveal linked evidence after thinking through your example;
open questions explicitly have no linked evidence. Write your answer and reflection
in your own words. Only checked questions are included in the saved version.

Review and confirm, then **Save private version**. Editing any question selection
or draft clears the confirmation. Closing or replacing unsaved drafts asks before
discarding them. Saved versions reopen under the same exact saved review, including
after an app restart. Every save creates a separate immutable version; it never
replaces earlier answers. Reopening and saving is how you revise an answer.

**Private JSON** downloads the original saved bytes. This file contains the full
frozen review, evidence and source notes as well as your answers. It is unencrypted
and intended for you, not an employer application pack. No account or provider is
used. Managed workspace recovery includes these journals and checks the embedded
review against the recovered shelf, in addition to byte hashes. A different saved
review does not inherit these drafts automatically. Older bundles remain supported.
Database-only JSON backups still exclude managed files, including these journals.
The managed rehearsal collection is bounded to 1000 files and 64 MiB. Further
saves are refused at capacity; existing versions are preserved.

This browser workflow records no timer, generates no answers, grades nothing and
never marks learning complete. Older native journal import, version comparison and
private text practice packs are not yet migrated. The native interface stays retired.

## Verify and practise

```powershell
python -m unittest discover -s tests -p test_browser_rehearsal.py -v
```

In a separate offline practice workspace, spend 60–90 minutes selecting the Python
requirement, predict the linked evidence, reveal it, and write a concrete example.
Keep the Spark requirement as an open question rather than inventing experience.
Save, reopen, revise and download. Create a workspace recovery ZIP, restore it as a
separate workspace and compare the saved answer. Explain why a hash can preserve an
answer without proving the answer is true. Neither saved text nor time spent proves
learning or interview readiness; practice has not been completed on your behalf.
