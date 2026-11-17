# Dossier comparison — 16 November 2026

Compared Dossier at [c79562e](https://github.com/AienTech/dossier/tree/c79562e67e0459c999ea5dcbbeb444e98837ccda)
with RoleWeave v0.23, then the v0.24 email handoff. No upstream app installed or
benchmarked; Dossier's features are documentation claims except noted source
inspection. No upstream source/assets/history copied. This checklist measures
25 named capability areas, not effort, overall completion, quality or acceptance.

**Baseline v0.23: 7 implemented, 9 partial, 9 missing.**
**With v0.24: 8 implemented, 9 partial, 8 missing.**
**With v0.25: 9 implemented, 9 partial, 7 missing.**
**With v0.26: 10 implemented, 8 partial, 7 missing.**
**With v0.27: 11 implemented, 7 partial, 7 missing.**
**With v0.28: 12 implemented, 6 partial, 7 missing.**
**With v0.31: 13 implemented, 5 partial, 7 missing.**
**With v0.32: 14 implemented, 4 partial, 7 missing.**
**With v0.33: 15 implemented, 3 partial, 7 missing.**
Source-bound advisory assessment, corrected reviews, like-for-like rankings and
per-job version history close the assessment area; score quality/calibration and
real suitability remain unverified. Current status is now explicit in the table;
the v0.23 baseline column stays historical.
Retained full request/proposal turns and older-proposal browsing close the scoped
refinement area, alongside existing local Undo/Redo/reset. Keystroke autosave,
durable Undo stacks, every Dossier interaction and live model quality are not claimed.
Structured career sections close the scoped profile-area gap: ten typed sections,
browser edit/order/removal/review, selected documents/evidence, privacy and recovery.
No photo/arbitrary rich text, personal acceptance or complete Dossier parity claim.
Theme builder/import/export closes the local styling area; three presets remain,
not a claim to reproduce Dossier's twelve designs or arbitrary CSS.
The dashboard area now has explicit stage-observation bars, weekly activity and a
follow-up month calendar; interview-event/account sync remains in Calendar partial.
Provider selection closes the scoped provider/model/local-server area; arbitrary
remote endpoints and every model variant are not claimed supported.
Markdown closes the stated import-format gap; saved manual searches/review queue
move the agent area from missing to partial. Scheduler/scoring/automatic drafts
remain absent; the other partial areas are not claimed complete.
Implemented means the stated local workflow exists and is offline tested; it does
not mean every Dossier detail, live provider quality or personal acceptance passed.
Partial includes native-only work unavailable in the sole supported browser UI.

| Capability | v0.23 baseline | Current status | Shipped scope / remaining detail |
| --- | --- | --- | --- |
| Shared reviewed career profile | Implemented | Implemented | Same; source review is a human assertion |
| Career profile and rich sections | Partial | Implemented | **Implemented in v0.31:** ten typed human-authored sections with browser edit/reorder/remove/review, selected TXT/HTML/PDF/letters/evidence reuse, contact-aware AI context and managed recovery; no inferred qualifications. |
| Existing resume import | Partial | Implemented | **Implemented in v0.25:** text PDF/DOCX/TXT/Markdown with explicit excerpt review; no scanned OCR |
| Resume editing/preview/PDF export | Implemented | Implemented | Reviewed selections, exact preview and frozen document |
| Themes and theme builder | Partial | Implemented | **Implemented in v0.28:** three unchanged presets plus bounded color/font/size/margin/paper builder and strict styling-only JSON sharing; no arbitrary CSS/remote fonts |
| Pasted posting and saved applications | Implemented | Implemented | Manual capture and immutable review versions |
| Multi-source role/location discovery | Partial | Partial | **Expanded in v0.29:** FreeHire role/location search plus browser Greenhouse/Lever global/Lever EU/Ashby, local filtering/import/archive replay/comparison and source-bound recovery; no JSearch/Adzuna/startup sources. Area remains partial. |
| YC/Hacker News startup discovery | Missing | Missing | Not implemented |
| Named scheduled discovery/agent queue | Missing | Partial | **Partial in v0.25:** named manual runs, local budget, dedupe/review queue/recovery; no scheduler/AI score/auto-drafts |
| Profile-to-posting assessment | Partial | Implemented | **Implemented in v0.33:** exact-quote/advisory-score proposals, human evidence/status/opinion correction, same-source/model group rankings, market filters, per-job version history, byte-replayed requests and managed recovery. No calibrated fit/eligibility/hiring probability claim. |
| Reviewed tailored resume and PDF letter | Implemented | Implemented | Source-bound reviewed provider workflow; real quality unverified |
| Full refinement chat and undo | Partial | Implemented | **Implemented in v0.32:** opt-in retained instruction/request/proposal turns, immutable edited-parent branches, exact-source older-proposal browser/reopen, fresh review, local Undo/Redo/reset, explicit removal and managed recovery; no keystroke autosave or durable Undo stack. |
| AI provider/model settings and local models | Partial | Implemented | **Implemented in v0.26:** selected models, OpenAI/Anthropic/Mistral, Ollama/LM Studio numeric loopback; fixed hosts, no arbitrary remote URL; live quality unverified |
| Application email composer and mail-client handoff | Missing | Implemented | **Implemented in v0.24:** reviewed local EML, exact PDFs, reopen/copy/download; no automated sending |
| Connected Gmail sending | Missing | Missing | No account integration or sends |
| Mailbox reply reading and AI responses | Missing | Missing | Native manual local excerpt review is not browser inbox/AI reply handling |
| Google Calendar integration | Partial | Partial | Narrow native-only follow-up contract; no browser/two-way interview calendar |
| Application board/table/stage tracking | Implemented | Implemented | Manual observations, reminders and conflict guards |
| Dashboard funnel/charts/calendar | Partial | Implemented | **Implemented in v0.27:** current/ever-recorded bars,12UTC weeks, market-filtered follow-up month/agenda; no inferred conversion rates or verified outcome claims |
| Managed data export/import/recovery | Implemented | Implemented | Managed ZIP plus DB backup; explicitly scoped exclusions |
| Nightly automatic backups | Missing | Missing | Explicit manual recovery only |
| External MCP connector | Missing | Missing | Not implemented |
| Local Windows package/installer | Implemented | Implemented | Offline runtime/lifecycle tested; unsigned, personal acceptance open |
| Remote self-hosting and password sign-in | Missing | Missing | Deliberately loopback-only Windows app; no supported remote hosting/authentication |
| Locale-aware document labels/dates | Missing | Missing | User-written content is possible; no equivalent 21-language document-localization system |

Extra RoleWeave features, such as separate India/relocation markets, exact-review
journals and audited source recovery, are useful but do not cancel missing parity
areas. Dossier's README does not document automatic employer-form filling or
submission. RoleWeave's contact helper is separate: uploads, screening and final
submission remain manual. Neither an AI score nor a claim guard proves suitability
or truth; this comparison does not endorse Dossier's absolute reliability wording.

## Inspected sources

- [Pinned feature documentation](https://github.com/AienTech/dossier/blob/c79562e67e0459c999ea5dcbbeb444e98837ccda/README.md).
- [Email UI](https://github.com/AienTech/dossier/blob/c79562e67e0459c999ea5dcbbeb444e98837ccda/src/app/(app)/applications/[id]/email-tab.tsx) and [mailto helper](https://github.com/AienTech/dossier/blob/c79562e67e0459c999ea5dcbbeb444e98837ccda/src/lib/application-email.ts): message copy/mail-app handoff and PDF downloads; Gmail is a separate integration.
- [Agent runner](https://github.com/AienTech/dossier/blob/c79562e67e0459c999ea5dcbbeb444e98837ccda/src/lib/agent/run.ts): saved searches, request admission, dedupe, scoring/draft queue; no automatic application sending.
- [Provider options](https://github.com/AienTech/dossier/blob/c79562e67e0459c999ea5dcbbeb444e98837ccda/src/lib/ai/provider-options.ts): local and hosted configurations.

## Implementation order

1. v0.24 local application email composer/handoff, without requiring accounts.
2. v0.25 saved manual searches/review queue and Markdown import. Scheduler/AI
   agent work remains separate; inspect source terms before background requests.
3. Broader AI provider settings, with reviewed local-model contracts and consent.
4. Browser Calendar and manual reply review; connected Gmail/two-way sync require
   separate access/setup and authorized live validation.
5. Structured profile/theme/analytics/backup/MCP scope, chosen by real workflow need.

Remaining real gates: personal first-use, real helper/employer compatibility,
mail-client EML import, live model/provider quality, account consent, signing and
interrupted upgrades. No production-readiness percentage or adoption claim.
