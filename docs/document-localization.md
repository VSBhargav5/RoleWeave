# Document languages (v0.37)

In the resume studio choose **Document language** before previewing. The original
English choice keeps ISO months and the old English renderer. English (UK) and
English (US) use named months; year-month precision means both display March 2024,
not a manufactured day. German, Spanish, French, Italian, Brazilian Portuguese
and Dutch have fixed labels and month names: nine choices across seven languages.
No OS locale, network translation, API key or model request is used.

The cover-letter editor starts with its frozen resume's language. You can explicitly
choose a different language. Preview and approve each document independently.
Changing the language clears approval and invalidates the prior preview. Both the
locale and original source identity are included in the frozen snapshot. Downloads,
recipient packs, private dossiers and managed recovery retain the exact bytes.

## What changes, and what stays human-authored

Only built-in section/field labels, structured YYYY-MM dates, ongoing labels,
letter scaffold and document metadata are localized. Original names, role/company,
claims, summary, titles, custom headings, links, introduction and closing stay
exactly as authored. A source claim containing a written date is not parsed or
translated. Skills, self-described proficiency and review statements stay human
assertions. No years-of-experience or eligibility inference is added.

This can produce a mixed-language document. Write/review your own introduction,
closing and content in the intended language. Selecting French does not translate
English claims. The app interface, emails, source postings, generated AI wording,
calendar and source models keep their existing contracts. No global preference or
silent language selection based on market/location. Fixed copy has not had a
native-speaker acceptance review or employment-document/legal review.

## Compatibility and integrity

Old resume-v1/v2 and letter-v1/v2 keep their default English rendering and formats.
Non-default choices use resume-v3/letter-v3 snapshots. Localized resumes bind their
PDF to the replayed source/theme/locale, not just the claimed PDF fingerprint.
Localized letters replay their exact text/PDF too. A locale change cannot silently
reuse the previous preview. Older app versions cannot open the new snapshot format;
keep the current complete app and an untouched original recovery copy. Existing
backups are not migrated in place. Unsupported locales fail rather than defaulting.

The existing bundled font boundary remains: unsupported content fails PDF export
with the missing code points; no replacement glyphs, remote fonts or truncation.
Resume HTML retains Unicode and can be printed separately through existing source
exports. The supported browser studio still requires a renderable PDF resume.
Letter TXT-only remains available for unsupported PDF content. This is not a
21-language system, full app localization, arbitrary Unicode PDF or translation
service. Localization moves from missing to partial in the scoped comparison.
Four unrelated missing areas remain: Gmail, inbox/AI responses, MCP and remote
hosting/authentication. Other partially implemented workflows remain partial.

## Focused practice (60–90 minutes)

Use a separate synthetic practice workspace. Choose one structured experience with
2024-03 and ongoing status. Predict German's März 2024 - Heute, then preview it.
Check that the original claim and custom heading are unchanged. Select French:
confirm that approval disappears and saving requires the new preview. Freeze and
open the downloaded PDF, inspect accents and page boundaries. Create a letter
with your own introduction and notice which scaffold is localized. Download the
recipient kit; restore a managed backup into a separate shelf and compare exact
PDF/TXT bytes. Explain the tradeoff: a fixed label catalog preserves source facts,
but cannot make an untranslated claim a fluent localized application. Practice,
translation quality and personal usefulness are not presumed completed.

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_document_locale.py -v
```
