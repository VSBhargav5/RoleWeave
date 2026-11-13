# Browser workspace and reviewed form filling — v0.17

RoleWeave now starts in your default browser. The interface uses browser-rendered
text, CSS gradients, SVG icons, rounded surfaces and responsive layouts. Python
and the existing SQLite shelf remain authoritative. There is no frontend build
step or Node dependency for users. Tkinter remains available under Settings →
Open advanced tools, or `python desktop.py --legacy`.

## First application

1. Open the rebuilt Windows executable or existing source launcher. Close an old
   instance first. The default local address is `http://127.0.0.1:8765`.
2. Career profile: enter your actual contact information, summary and sourced
   career/project facts. Enter first and last names explicitly for form filling;
   the app never guesses how to split your name. Review and save the profile.
3. Discover jobs: enter a role, optional location, country and remote preference.
   Click Search jobs. Choose India/remote or relocation as the destination market,
   then Review & save. A company-board URL is no longer needed for this path.
4. Read the saved description and eligibility requirements. Optionally connect an
   exact requirement quote to reviewed facts; this produces a new immutable review.
   Earlier tracking does not move automatically to that revision.
5. Build resume: select reviewed facts, preview the exact text, confirm, then save
   and download the PDF. A frozen version retains its original profile and job.
   Cover letters use the frozen resume's profile; preview your own introduction,
   selected facts and closing before downloading TXT. Recipient ZIPs contain only
   the explicitly chosen resume PDF, excluding private evidence/history.
6. Browser helper: download and extract the helper ZIP. In Chrome or Edge's
   extensions page, enable Developer mode, choose Load unpacked and select
   `RoleWeave-helper`. This manual local installation is not store publication.
7. Review the contact sheet on RoleWeave's Browser helper page and prepare it.
   Click the helper toolbar icon on that tab and choose Load contact sheet.
8. Open the saved employer page and navigate to its actual application form.
   Click the helper, review this form, inspect the destination and each proposed
   value, select the fields and explicitly consent before filling.
9. Check the filled values. Upload your PDF, answer screening questions and
   submit yourself. Record my submission stores your observed date, channel,
   reference and follow-up; it does not submit or independently verify anything.

The helper supports empty, visible native name/email/phone/location/LinkedIn/
portfolio inputs with explicit autocomplete or exact unambiguous labels. It uses
native setters plus input/change events. It does not click Submit or Next, upload
files, answer legal/work-authorization/demographic questions, touch passwords,
overwrite values, scan background tabs or fill iframes/custom controls. Changed
fields or navigation invalidate a reviewed preview. Some ATS forms remain manual.
Real employer compatibility and human acceptance have not yet been established.

## Data and provider boundaries

- Explicit role/location search sends only those filters to the public
  [FreeHire API](https://freehire.me/docs/api). Its unauthenticated access is for
  personal/non-commercial use; a commercial deployment needs a separate plan.
  This is one source, not exhaustive coverage, sponsorship or eligibility proof.
  Twenty records are fetched per search. No automatic pagination or background
  polling is enabled. Unsupported records have an explicit excluded count.
- One bounded public check on 13 November 2026 returned 20 accepted records and
  zero excluded records for `data engineer`, country `IN`. Provider-reported
  total46815 is an observation, not a verified relevant-job count. Response hash:
  `0ac89812b862ac0c76a142ba65aace82228da493abc30d6e07c501d441998e4b`.
- Saving a live result retains original response bytes under
  `web-artifacts/sources/<sha256>.json`. Hashes establish byte integrity, not
  authenticity or current listing availability. Changed descriptions can produce
  a new review. Local duplicate URL/market/description saves reuse the review.
- The loopback server requires a per-process header token, exact Host and
  same-origin requests. It has no CORS, remote bind, URL credentials or request
  logging. HTML bootstrap contains the token for its own local frontend only.
  Static content uses a restrictive CSP. This does not defend against a malicious
  local program or an extension already authorized to read the tab.
- The contact sheet includes only explicit contact fields, never facts, history,
  provider credentials or the local API token. Preparing it does not fill a site.
  The helper keeps contact data in browser-session memory until clear/session end
  or extension reload. Filled sites can process values immediately, before submit.
- Existing shelf paths and v3 recovery remain unchanged. Backups and documents
  are unencrypted. Separate `web-artifacts` source responses, letters and ZIPs are
  outside shelf backups; preserve that directory separately if required. Clearing
  the prepared local sheet does not clear an already loaded extension sheet.
- Settings → Quit stops the host. Closing a tab alone leaves it running. Optional
  AI/Calendar and older advanced tools remain native and retain their consent gates.

## Runnable verification and a focused exercise

```powershell
python -m unittest discover -s tests -v
python desktop.py --web-self-test out/source-web-check
python desktop.py --demo
```

The synthetic preview opens a separate new shelf. It never contacts the discovery
provider. On Browser helper, load its explicitly synthetic contact sheet and open
the synthetic practice form. Predict which seven empty fields will fill and which
fields will remain untouched. Review/fill, then verify the counter still reads
`0 submissions`. Reload, preview, change one field manually and try the old
preview: it must refuse without filling the other fields. Explain the tradeoff:
strict native-field support reduces coverage but avoids guessing sensitive answers.
This 60–90 minute exercise is offered, not recorded as completed learning.

For reproducible Chromium UI checks (development only, Node24+):

```powershell
npm install --no-save --ignore-scripts playwright@1.62.1
npx playwright install chromium --only-shell
node tests/browser-workflow.cjs
```

Set `ROLEWEAVE_PYTHON` to a Python executable with the pinned project dependencies
if it is not the current `python`. Screenshots are written under `out/web-qa`.
The test exercises discovery/save, PDF/letter/ZIP downloads, tracking, draft guards,
actual synthetic native-input filling and stale/no-overwrite/no-submit behavior.
It exercises the mapper through browser automation; real installed-extension
toolbar permission/installation and actual employer forms require manual acceptance.
Windows packaging also runs source/frozen local HTTP/asset and native self-tests.

## Comparison and remaining work

The [referenced Dossier README](https://github.com/AienTech/dossier) documents
discovery, resume tailoring and application tracking and states its job agent
never sends/applies. No ATS autofill implementation was identified in the reviewed
documentation/tree. RoleWeave's browser mapper is original code; no Dossier AGPL
implementation/assets/history were imported.

This iteration closes the three demonstrated gaps: browser-quality presentation,
role/location discovery, and reviewed form filling. It is still an unsigned
controlled beta. A permitted personal application trial, installed-helper and
real-ATS acceptance, unusual scaling/accessibility review, signing/distribution,
optional live integrations and interrupted-upgrade confidence remain open. A
passing synthetic test does not justify a universal autofill or production claim.
