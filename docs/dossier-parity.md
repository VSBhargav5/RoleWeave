# Dossier comparison — 16 November 2026

Compared Dossier at [c79562e](https://github.com/AienTech/dossier/tree/c79562e67e0459c999ea5dcbbeb444e98837ccda)
with RoleWeave v0.23, then the v0.24 email handoff. No upstream app installed or
benchmarked; Dossier's features are documentation claims except noted source
inspection. No upstream source/assets/history copied. This checklist measures
25 named capability areas, not effort, overall completion, quality or acceptance.

**Baseline v0.23: 7 implemented, 9 partial, 9 missing.**
**With v0.24: 8 implemented, 9 partial, 8 missing.**
Implemented means the stated local workflow exists and is offline tested; it does
not mean every Dossier detail, live provider quality or personal acceptance passed.
Partial includes native-only work unavailable in the sole supported browser UI.

| Capability | v0.23 | v0.24 / remaining detail |
| --- | --- | --- |
| Shared reviewed career profile | Implemented | Same; source review is a human assertion |
| Rich structured career sections | Partial | Generic facts/sections, fewer dedicated fields than Dossier |
| Existing resume import | Partial | Text PDF/DOCX/TXT; no Markdown import or scanned OCR |
| Resume editing/preview/PDF export | Implemented | Reviewed selections, exact preview and frozen document |
| Themes and theme builder | Partial | Three themes; Dossier documents twelve plus builder/sharing |
| Pasted posting and saved applications | Implemented | Manual capture and immutable review versions |
| Multi-source role/location discovery | Partial | FreeHire browser search; existing employer boards not browser-migrated; no JSearch/Adzuna |
| YC/Hacker News startup discovery | Missing | Not implemented |
| Named scheduled discovery/agent queue | Missing | No saved recurring agent, source budget or automatic draft queue |
| Profile-to-posting assessment | Partial | Explicit requirement/evidence links; no equivalent AI scored ranking |
| Reviewed tailored resume and PDF letter | Implemented | One source-bound OpenAI workflow; real quality unverified |
| Full refinement chat and undo | Partial | Explicit revised proposals and saved drafts; no full chat/unit-level undo |
| AI provider/model settings and local models | Partial | One OpenAI model; no Ollama/LM Studio/Anthropic/Mistral/custom endpoint |
| Application email composer and mail-client handoff | Missing | **Implemented in v0.24:** reviewed local EML, exact PDFs, reopen/copy/download; no automated sending |
| Connected Gmail sending | Missing | No account integration or sends |
| Mailbox reply reading and AI responses | Missing | Native manual local excerpt review is not browser inbox/AI reply handling |
| Google Calendar integration | Partial | Narrow native-only follow-up contract; no browser/two-way interview calendar |
| Application board/table/stage tracking | Implemented | Manual observations, reminders and conflict guards |
| Dashboard funnel/charts/calendar | Partial | Global counts and reminders; no equivalent funnel/week charts/month calendar |
| Managed data export/import/recovery | Implemented | Managed ZIP plus DB backup; explicitly scoped exclusions |
| Nightly automatic backups | Missing | Explicit manual recovery only |
| External MCP connector | Missing | Not implemented |
| Local Windows package/installer | Implemented | Offline runtime/lifecycle tested; unsigned, personal acceptance open |
| Remote self-hosting and password sign-in | Missing | Deliberately loopback-only Windows app; no supported remote hosting/authentication |
| Locale-aware document labels/dates | Missing | User-written content is possible; no equivalent 21-language document-localization system |

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
2. Saved discovery searches and explicit run/review queue; inspect source terms
   before any scheduler or background requests.
3. Broader AI provider settings, with reviewed local-model contracts and consent.
4. Browser Calendar and manual reply review; connected Gmail/two-way sync require
   separate access/setup and authorized live validation.
5. Structured profile/theme/analytics/backup/MCP scope, chosen by real workflow need.

Remaining real gates: personal first-use, real helper/employer compatibility,
mail-client EML import, live model/provider quality, account consent, signing and
interrupted upgrades. No production-readiness percentage or adoption claim.
