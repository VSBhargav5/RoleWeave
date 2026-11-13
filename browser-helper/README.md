# RoleWeave browser companion

Extract the downloaded ZIP. Open Chrome or Edge's extensions page, enable Developer mode, choose **Load unpacked**, and select this folder. This is a local development installation, not a store-reviewed extension. No broad host permission is requested.

In RoleWeave, open Browser helper, review the contact sheet and prepare it. Click the toolbar extension icon on that local tab and load the contact sheet. On the employer form, click the icon, review the destination and proposed fields, select values, consent and fill. Upload your resume, complete screening questions and submit yourself.

Contact values remain in `chrome.storage.session` until cleared, browser-session end or extension reload. A filled page's scripts can immediately process values, even before submission. Only supported visible empty native inputs are mapped from explicit autocomplete or exact labels. Passwords, files, hidden fields, demographic/legal/work-authorization questions, ambiguous labels, custom widgets and iframes remain manual. No guarantees across all ATS sites. No automatic submit, Next, background scanning, AI calls or network requests by this helper.

To remove it, use the browser's extension management page. Clear its session after use. The helper never needs an API key or RoleWeave session token.
