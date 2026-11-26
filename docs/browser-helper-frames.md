# Embedded application form support

The Samsara careers page embeds its application in Greenhouse. Earlier helper
versions only executed page.js in frame zero. That frame contains navigation
controls, not the application inputs. Reporting zero fields and linking to a new
tab described the problem without implementing iframe autofill.

## Primary-source comparison

- [Chrome scripting targets](https://developer.chrome.com/docs/extensions/reference/api/scripting): default injection targets the main frame; frame IDs or document IDs target embedded documents.
- [Chrome activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab): temporary access covers the invoked tab's main origin, not arbitrary cross-origin embedded ATS pages.
- [Chrome optional host permissions](https://developer.chrome.com/docs/extensions/reference/api/permissions): runtime access can be requested for a specific discovered origin.
- [JobFill manifest](https://github.com/Thesirloc/job-autofill/blob/main/manifest.json) and [Greenhouse adapter](https://github.com/Thesirloc/job-autofill/blob/main/content/adapters/greenhouse.js): explicitly matched ATS hosts and all-frame content scripts. Its orchestrator waits for form fields and uses platform adapters.
- [Richie Form Fill manifest](https://github.com/richtank2/job-autofill-extension/blob/main/manifest.json) and [background routing](https://github.com/richtank2/job-autofill-extension/blob/main/background.js): frame enumeration and targeted script execution with ATS host permissions.
- [Playwright extension testing](https://playwright.dev/docs/chrome-extensions): real MV3 testing uses a persistent full-Chromium context; headless-shell tests with mocked chrome APIs do not establish iframe permissions or document routing.

These implementations were inspected for mechanisms, not copied. Proprietary
extensions' unpublished internals were not inferred from their marketing claims.

## RoleWeave implementation

frames.js coordinates explicit scans of visible frame trees. It recognizes known
ATS redirects (including boards.greenhouse.io to job-boards.greenhouse.io), asks
for the actual embedded origin when access is missing, and injects page.js into
that frame. No broad site access is granted automatically. The optional HTTPS
pattern permits requesting a discovered site; it is not an all-sites grant.

The helper retains document and frame identity with each proposed field. It
checks all selected documents and values before writing, uses native value setters
and input/change events, then checks that the site retained the result. Consent
and previews are invalidated when the target or selected values change. Saved
answers learned from an iframe default to that frame's exact job URL, preventing
wrapper-page scope mistakes on shared ATS hosts.

This requires a frame coordinator and an additional optional frame-enumeration permission;
it is more code than a main-document-only helper, but fixes the demonstrated
failure without adding background scanning or unrestricted host grants.

## Verification and limits

A real installed MV3 extension was first tested against an employer wrapper with
three unrelated controls and a separate-origin application frame: v0.5 returned
zero contact choices. The regression now requires six contact choices and checks
actual filled values, existing/sensitive preservation and zero submissions.
It also covers same-URL document reloads, changed inputs, multi-document preflight,
frame-scoped answer reuse, framework-style value setters, cleared-value detection,
manual suggestion controls and the browser's actual denied-access state.

The test profile is synthetic. Its positive tests explicitly grant fixture hosts
in an isolated manifest; they do not simulate approval of the browser's native
permission prompt. A separate profile omits the frame grant and checks that the
helper asks for that origin and cannot write. Normal tests never contact employers.
An optional read-only live Greenhouse check follows the real public embed redirect
and found seven contact choices. No live employer values or submissions were sent.

Native text, textarea, numeric and single-select inputs and open shadow roots are
supported. React-select city/country fields are shown as manual because typing a
search string does not establish a selected option. Radio groups, upload controls,
closed shadow roots and unsupported custom widgets remain manual. Browser site
permission approval and varied real ATS layouts still require user acceptance;
there is no claim of universal platform coverage.
