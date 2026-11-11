# Private rehearsal workflow (v0.10)

A job requirement is a question to explain. A linked fact is source material;
it is not proof that you can explain it. RoleWeave keeps these separate from your
answer draft, reflection and explicitly started local elapsed timer. It generates
no answers, grades, hiring predictions or verified learning assertions.

## Windows workflow

Open a saved review, then **Evidence & next steps > Review files > Write/save rehearsal answers**. Choose
1-30 exact source requirements. Draft an example in your own words, reveal linked
evidence when useful, and record what you still cannot explain. Previous/Next
preserves each draft. Open questions without evidence stay open questions.
Changing the question selection warns before discarding nonblank drafts.

Use **Private tools > Start/pause local elapsed timer** if useful. It starts
paused, records only locally elapsed seconds (up to 86400), and pauses on save.
It does not measure attention or learning. Reset affects only the current draft.
Review the privacy checkbox and **Save new private journal JSON**. Existing paths
are refused. Each file includes the full original review, even unselected facts,
plus selected requirement IDs and your drafts. Keep these unencrypted files
private. They are separate files, not included in full-shelf backups.

**Evidence & next steps > Review files > Open private rehearsal version** reopens the exact frozen source,
not a newer posting revision. This does not change application history. From a
saved, unchanged journal, Private tools can export selected questions/linked
evidence as TXT; answer/reflection drafts are excluded unless explicitly chosen.
The TXT is still private because it includes linked career evidence.

**Compare an earlier private version** shows exact text/selection differences,
source hashes and elapsed-time delta. Both versions must refer to the same exact
review and be ordered by their declared recorded times. Imported timestamps and
hashes establish neither authenticity nor practice quality. A change or omission
is not improvement, correctness or forgetting. No automatic answer transfer to
revised job sources is performed.

## One focused 60-90 minute exercise

```powershell
python desktop.py --demo
```

1. In the separate synthetic shelf choose Python and Spark requirements. Predict
   which has evidence before revealing it. Explain why an open question must not
   become invented employment experience.
2. Write a short Python example and a reflection, navigate away and back, reveal
   evidence, and verify the draft stays unchanged. Start/pause the timer explicitly.
3. Save `practice-v1.json` to a private new path. Revise your explanation, save
   `practice-v2.json`, then compare them. Predict the changed requirement ID.
4. Export a question-only pack and a pack with drafts. Inspect their text and
   explain what each still discloses. Neither is intended for a recruiter.
5. Close/reopen a saved journal. Confirm application stage/history is unchanged.
   Test an existing output filename: it must not be replaced.

```powershell
python rehearsal_journal.py C:\private\practice-v1.json
python rehearsal_pack.py C:\private\practice-v1.json --output C:\private\questions.txt --confirm
python rehearsal_compare.py C:\private\practice-v1.json C:\private\practice-v2.json
python -m unittest discover -s tests -p "test_rehearsal*.py" -v
```

Tradeoff: freezing source bytes preserves exactly what a draft addressed, but
copies private data and does not authenticate the claims. A new source revision
needs a deliberate new rehearsal. User practice, explanation quality, manual
file dialogs/scaling and usefulness remain unverified until actually tried.
