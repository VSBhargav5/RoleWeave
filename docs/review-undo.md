# Undo review edits locally (v0.30)

After an explicit AI request completes, Review edits provides Undo review edit and
Redo review edit for that proposal's wording and selected suggestions. Reset wording
to proposal / Reset claim to proposal restores one original model suggestion; that
reset is itself undoable. Model wording remains untrusted and needs human review.

Each wording input or selection records a state, up to20states including the current
one. Oldest states are evicted at the bound. Editing after Undo discards the abandoned
Redo branch. Undo/redo/reset clears accuracy confirmation, so it cannot silently
accept an earlier review decision. Source references and backend source/result guards
remain unchanged. Final acceptance still requires your explicit factual review.

These controls are local: no provider send, retry, key, source change or main-profile
write. A new provider proposal starts fresh history. Request preview/back/cancel/close
clears the edit stack; closing does not promise immediate process-memory erasure.
Accepted drafts keep their existing frozen provenance but do not include this edit
stack. Native editor keyboard undo remains available inside individual fields.

This is not a persisted full refinement chat or a history browser for old proposals.
Long-lived conversation/replay and older-proposal selection remain partial. A new
revision still requires exact provider payload preview and renewed per-request consent.
No live model quality, personal usefulness or learning completion is claimed.

## Reproducible checks

```powershell
node --test tests/review-history.test.mjs
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_ai_tailoring.py -v
```

Five state-transition tests cover selection/wording restoration, branch invalidation,
deep copy isolation, bounded eviction and proposal/close reset. The actual browser
journey checks undo/redo/reset, fresh accuracy consent, no extra provider request and
fresh history after a revised proposal. Source and packaged synthetic trials use
fixed local output only; no live account/key is used.

For one60–90minute synthetic practice session, predict the states after changing a
summary and selecting it. Undo selection then wording, redo once, type an alternative
and predict why Redo is unavailable. Reset to proposal and undo that reset. Confirm
accuracy must be reviewed again, then save only corrected wording for the application.
Tradeoff: a small transient stack makes review edits recoverable without keeping a
new permanent record of private drafts, but cannot recover history after close.
