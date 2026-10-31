# Research and personal build plan

Reviewed 31 October 2026. Features below are upstream documentation claims unless
specific source inspection is stated. No upstream apps were installed or
benchmarked, and upstream test/performance counts are not our verification.

## Existing tools worth learning from

| Tool | Useful emphasis | Implication for this personal build |
| --- | --- | --- |
| [Dossier](https://github.com/AienTech/dossier) | Profile, resume/letter refinement, application board, multiple model providers, optional email/calendar | Strong reference for review flow; Next.js/PostgreSQL/Docker is a larger starting footprint than this Python prototype |
| [Jobleft](https://github.com/Blueturboguy07/jobleft) | Employer-board discovery, local store, deterministic match reasons, tracker, network imports | Discovery and transparent reasons are useful; published installer targets Apple Silicon macOS, so Windows needs a separate delivery plan |
| [JobOps](https://github.com/DaKheera47/job-ops) | Multi-source search, tailoring, document export and reply tracking | Broad orchestration reference; avoid copying its entire operational scope into an initial personal app |
| [Resume Matcher](https://github.com/srbhr/Resume-Matcher) | Python FastAPI/SQLite backend, master resume, tailoring review, exported-PDF checks | Closest Python-oriented reference for later resume work; keyword formulas are not an employer's ATS result |
| [Reactive Resume](https://github.com/reactive-resume/reactive-resume) | Document editor, proposed edits, versions, exports and application tracking | Excellent reference for document review; evaluate interoperability before building a large template engine |

Licenses observed in upstream repository/docs: Dossier AGPL-3.0; Jobleft MIT;
JobOps describes AGPLv3 plus Commons Clause; Resume Matcher describes Apache-2.0;
Reactive Resume describes MIT. No code is imported here. Recheck the exact
license and third-party notices at a pinned revision before any future reuse.

## Specific source findings

Inspected Dossier's [fact guard](https://github.com/AienTech/dossier/blob/main/src/lib/ai/fact-guard.ts)
and [posting scoring task](https://github.com/AienTech/dossier/blob/main/src/lib/ai/tasks/score-posting.ts).
The guard checks names, numbers and credentials against pooled profile/posting
sources; the scoring task asks a model for reasons and a bounded score. These
are useful checks, but presence of a word/number does not prove that a specific
accomplishment belongs to a candidate. This is an inference about that inspected
check, not a claim that the whole application fabricates claims.

Inspected Jobleft's [match integration](https://github.com/Blueturboguy07/jobleft/blob/main/apps/server/src/integ/match.ts)
and [match acceptance outcomes](https://github.com/Blueturboguy07/jobleft/blob/main/docs/outcomes/match.md).
It delegates scoring to a shared engine and documents stable scores, quoted
hard requirements and unknown profile answers. Acceptance outcomes state goals;
reading them does not establish they pass. Its [build report](https://github.com/Blueturboguy07/jobleft/blob/main/docs/BUILD-REPORT.md)
also records gaps and untested live services. We should preserve that honesty.

## Personal direction

The user chose both job markets, tracked separately. A remote label alone cannot
establish permission to work from India, and sponsorship history cannot establish
that a particular role sponsors relocation. Record stated requirements, source
quotes and unanswered eligibility questions per job. Do not infer nationality,
work authorization, salary expectations, employment dates or years of experience.

Build around a small weekly workflow: collect selected postings, review hard
constraints, link relevant career/project evidence, decide what to pursue,
prepare a reviewed application pack, and rehearse the examples you will explain.
Over time, observed requirement gaps can guide portfolio learning priorities.
Project evidence and production employment experience remain separate categories.

## Sequence over the next few months

| Phase | Deliverable | Evidence gate |
| --- | --- | --- |
| Foundation, now | Requirement/fact references, exact posting quotes, separate market label, synthetic CLI | Invalid quotes, unreviewed references and invented IDs fail; no qualification claim |
| Weeks 1–2 | Python SQLite store, immutable posting snapshots, basic Windows review UI, export/restore | User saves and reopens five manually selected jobs without losing source text; restore verified |
| Weeks 3–4 | Reviewed career fact bank and constraints, separate market views, job decisions and reminders | User corrects extraction and identifies unknown constraints; no arbitrary match percent |
| Weeks 5–6 | Reviewed resume selections, one text-based PDF layout, exact per-application versions | User approves every selected claim; extracted PDF text/order checked; no fabricated metrics |
| Weeks 7–8 | One permitted employer-board adapter, freshness and duplicate handling | Fixture tests and a permitted source check; fetch failure never means a job closed |
| Weeks 9–10 | Optional AI extraction/rewording with exact payload preview and cited fact IDs | Deliberate provider send, cost controls, adversarial fixtures and reviewed live examples |
| Weeks 11–12 | Interview evidence cards, Windows packaging and recovery rehearsal | User completes several real workflows; records usefulness/problems before broader scope |

These are sequencing estimates, not a delivery guarantee. Gate each phase on
actual use. AI, source adapters and PDF export may shift earlier only when the
manual workflow demonstrates the need. Gmail, calendar, contacts import and form
filling stay deferred until a specific need and authorization exist.

Start with Python and standard-library SQLite. Prefer a small PySide6 interface
for Windows, consistent with StudyFrame; choose it after testing the review flow.
No queue, hosted accounts, browser extension or agent framework is justified yet.
The current prototype has no database or UI dependency. No adoption, time savings,
ATS compatibility, answer quality or revenue has been demonstrated.

## Learning exercise

In 60–90 minutes, run the synthetic review, predict which requirement remains
open, change a quote, change a fact reference, and explain why valid references
still do not prove that a fact is true or relevant. Then manually prepare one
posting review using only your own permitted material, kept outside public Git.
User practice is not marked complete by creating this prototype.

RoleWeave is the latest requested implementation focus. StudyFrame stays at its
merged AI workflow pending an authorized live trial; SettleTrace remains paused.
Choose the next sprint deliberately rather than implementing all three at once.
