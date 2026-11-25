# RoleWeave browser companion

## Contact fields and reusable professional answers (v0.5)

Click Review this form. Under Choose fields to fill, tick the checkbox beside each
proposed field, then approve the destination and click Fill checked fields. Contact
fields start checked; professional answers start unchecked. Changing selection
clears consent. With zero matches the button stays disabled and explains why.
ARIA-labelled contacts are supported; embedded forms expose a direct HTTPS link
to open and review in their own tab. Custom widgets remain manual.

Under Questions to save for next time, choose Save an answer for this question.
Review or write the answer and save it locally. New answer also supports manual
entry. You can add up to ten exact alternate question wordings. Re-scan to see
saved-answer matches. Select page-only (default), this site, or all sites. Page-only
keeps job-specific answers separate even on shared ATS hosts. No fuzzy match,
model call, silent learning, answer inference or background capture occurs. Exact
normalized question matches are used; conflicting answers are left for review.

The library supports labelled text, textarea, numeric and native single-select
controls. Existing values are preserved. Legal, sensitive and salary questions,
radio groups, file uploads and custom widgets remain manual. Review years of
experience and role-specific wording before reuse.

Answers persist unencrypted in chrome.storage.local, separately from contact
session data and RoleWeave workspace backups. Use Export answers JSON to retain
a portable copy; import merges only non-conflicting IDs. Edit/delete individual
answers in the library. Clear contact session retains answers. Uninstalling the
helper removes its local library, so export first. Contact JSON remains compatible
and contains contact fields only. No new extension permissions are required.


Extract the downloaded ZIP. Open Chrome or Edge's extensions page, enable Developer mode, choose **Load unpacked**, and select this folder. This is a local development installation, not a store-reviewed extension. No broad host permission is requested.

Helper version 0.5.0: download the updated helper ZIP and reload/reinstall this
folder in Chrome/Edge if you previously installed an older version. The popup header must show v0.5.0.
If it only says **Load contact sheet** and has no JSON import, it is still the old
installation. Remove that old entry in the browser extensions page and use Load
unpacked with the newly extracted folder; downloading a ZIP alone does not update
the installed extension.

In RoleWeave, open Browser helper, review the contact sheet and prepare it. Choose
**Download contact JSON**. On the employer tab, open the helper and choose
**Import contact JSON** to select that file. The file contains unencrypted contact
details; remove it when no longer needed. You can alternatively use **Load from
RoleWeave tab** while the local RoleWeave helper page is active, then switch tabs.

Once the popup says the sheet is loaded, choose **Review this form**, review the
destination and values, explicitly consent and fill checked fields. Upload your
resume, complete screening questions and submit yourself. Importing alone never
fills anything. **No contact sheet loaded** means the transfer has not happened;
Review is disabled until a sheet is loaded. Exact Preferred First Name and Preferred
Last Name and Location (City) labels are supported; pronoun, sponsorship and authorization questions
remain manual.

Contact values remain in `chrome.storage.session` until cleared, browser-session end or extension reload. A filled page's scripts can immediately process values, even before submission. Only supported visible empty native inputs are mapped from explicit autocomplete or exact labels. Passwords, files, hidden fields, demographic/legal/work-authorization questions, ambiguous labels, custom widgets and iframes remain manual. No guarantees across all ATS sites. No automatic submit, Next, background scanning, AI calls or network requests by this helper.

To remove it, use the browser's extension management page. Clear its session after use. The helper never needs an API key or RoleWeave session token.


Version 0.4 opens a persistent companion window, bound to the tab where you click
its toolbar action. File pickers cannot dismiss this companion as a transient
extension popup. Keep it open during import, review and fill. Clicking the action
on a different application tab opens a companion for that tab. No host permission
was added: access is still granted only for the tab where you invoke the helper.

Load prepared sheet only works when the helper was opened on the local RoleWeave
Browser helper page with a prepared sheet. On the employer tab use Import contact
JSON, not Load. To switch from local loading to the employer, invoke the toolbar
action again on the employer tab; session contact values carry over. The review
shows the destination before filling. Closing/changing the source tab invalidates
the destination. Existing user-entered values and sensitive questions stay manual.
