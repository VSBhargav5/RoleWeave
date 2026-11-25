# Resume organization and free models (v0.39)

## Start with your resume

Career profile → Import existing resume accepts selectable-text PDF, DOCX and
UTF-8 TXT/Markdown. Extraction remains local. The review now suggests grouped
career entries under Experience, Projects, Skills, Education and other recognized
English headings. Related titles and bullets stay together where reading order
and paragraph boundaries permit. Name, contacts and summary appear separately.

Choose the information you want, correct its section, and confirm against your
original resume. Contact suggestions replace existing draft fields only when you
explicitly select them. Nothing saves your career profile automatically. After
adding the information, review the profile draft and save it yourself.

**Choose individual lines instead** remains available for unusual layouts or
misclassified text. Switching views resets selection. The original extracted text
is always inspectable. Section/name/phone recognition is a suggestion, not verified
identity or employment. Multi-column PDF reading order and wrapped titles can
still need correction. This release does not add scanned-PDF OCR or translate
headings in every language.

## Optional AI organization

Select OpenRouter free or an installed local model in Settings first. Inside the
resume review, choose **Review AI organization request**. Inspect the destination
and exact career text. Separate contact and summary suggestions are excluded;
remaining career text can still contain personal information. Enter your key in
the masked one-request field for OpenRouter, then explicitly confirm the send.

The model can return original line IDs and section names only. Unknown/repeated
IDs, rewritten facts, out-of-order excerpts, oversized entries and missing career
text are refused. The app reconstructs entry text from the local extraction; it
does not accept model-authored resume claims. Check the resulting groups again
before adding selections. No dates, qualifications or structured employment fields
are inferred into your saved profile. The master profile stays unchanged until
you save the reviewed draft.

Cancel organization or close the dialog to stop adopting its result. A request
already sent may still be processed remotely. Failed/rate-limited requests retain
local suggestions. No automatic retry or paid fallback. Pending import previews
are valid for ten minutes; keys are not stored in preferences, files or results.
Offline practice uses a labelled synthetic response and never needs a real key.

## Use OpenRouter free

Settings & backup → Provider → **OpenRouter (free models only)** → Save model
preferences. New workspaces default to `openrouter/free`. Previously saved provider
preferences are preserved: use the free preset to change them deliberately.

Use `openrouter/free` or an exact OpenRouter model ID ending in `:free`. Paid IDs,
auto routes, extra fallback-model lists and arbitrary provider URLs are refused.
Requests use the fixed HTTPS host, JSON-schema capability requirements, zero
prompt/completion/request price limits and disabled provider fallback. Unsupported
routes fail rather than switch to a paid model. Your OpenRouter key is still
required when sending a real request. Free capacity is not guaranteed and output
quality requires review. OpenRouter and its downstream provider policies apply;
the app does not change your account privacy preferences.

The free router can choose different underlying models across requests. Assessment
groups identify the configured model route, not a claim that the same underlying
model ran every assessment. Scores remain uncalibrated model opinions.

Official contracts checked for this implementation:
[free router](https://openrouter.ai/docs/guides/routing/routers/free-router),
[provider capabilities, price caps and fallback](https://openrouter.ai/docs/guides/routing/provider-selection).
No real key, model quality or account quota was tested by the agent.

## Employer boards and documents

The employer board name is a public URL identifier, not an API token. Paste a
supported board homepage, such as `https://boards.greenhouse.io/company` or
`https://jobs.lever.co/company`; the provider is detected. Or enter `company` and
select the provider yourself. Specific job URLs, query parameters, credentials
and unsupported hosts are refused. Regular Discover jobs requires no employer URL.

Documents now separates original imported resumes from generated application
resumes and cover letters. Originals become available after a confirmed import
selection retains the source file. Download verifies its original byte hash.
**Create resume** opens the saved-opportunity chooser (or guides you to profile/
discovery first). Importing a resume does not itself generate a tailored PDF.
An empty assessment page offers the first workflow instead of a blank model filter.

## Verification limits

Automated regressions use synthetic resumes and mocked model transport. They
exercise grouping, contact selection, source provenance, dropped/invented IDs,
cancellation, original-file downloads, free routing constraints and board URLs.
The actual browser journey covers local/synthetic AI organization, profile review,
the new empty states and document creation. Real resume layout quality, free-model
availability and live output quality still require your own trial.
