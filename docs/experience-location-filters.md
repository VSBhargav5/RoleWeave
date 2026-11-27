# Experience and remote-residence filters (v0.44)

Use v0.44 for the combined trial; it includes the untested v0.43 resume,
assessment and browser-helper updates.

## Search controls

Discover jobs now separates Job country (the provider query) from Remote residence
country (a local restriction check). Residence defaults to IN and can be changed to
another two-letter country code. A remote badge alone does not mean remote worldwide.
Source text saying candidates must reside in Canada excludes the role for an IN
residence. Explicit country restrictions override a generic remote/worldwide label.

Choose Advertised experience: Any, 0-2, 3-5 or 6+ years. Bands refer to the numeric
minimum stated in the posting, not a personal experience calculation. For example,
3-5 years means a stated minimum from three through five; an 8+ requirement is
excluded. The bands do not overlap. A 2-4 range has a minimum of two. Any disables
the years filter. No years are inferred from Senior/Staff titles, salary, company age
or the candidate's profile. Recognized no-prior-experience requirements count as zero.
Preferred/bonus sections and alternative education/experience paths are handled
conservatively; ambiguous experience becomes unknown rather than an invented number.

Unstated or unclear requirements are hidden by default when relevant to a selected
filter. Enable Include unstated / unclear requirements for review to show them in a
separate Needs review group. An explicit mismatch stays excluded. The page explains
why listings were filtered and shows the matched source year phrase where available.

## Saved searches and old queue entries

Edit an existing named search to choose its year band and residence country; new
searches save them with their other filters. Run now freezes the applied preferences
with that run. When an old unconfigured search is run through the new browser UI,
the displayed default preferences are frozen into the run without rewriting older
search/run evidence. Older API clients retain their unfiltered contract when they
omit the new preferences.

The review queue has the same controls. Running a named search selects that search's
preferences in the queue view. Older queued observations are also filtered in the
view; hidden rows and their keep/dismiss/save decisions remain stored. Filtering
does not delete a candidate or change an application stage. Source bytes remain
unchanged, and recovery replays filtered run counts against those original bytes.
The JSON snapshot accepts versioned optional preferences; filtered records need the
new reader, while old unfiltered records remain readable.

## Scope and limitations

These are deterministic English/numeric source-text rules, not an AI eligibility
decision. Common country names/labels and explicit residence phrases are recognized;
unrecognized countries, regions, phrasing and city-only labels can remain unclear.
Company office mentions alone do not establish candidate residence restrictions.
Location metadata and explicit remote-title country labels are treated as advertised
location constraints; review source discrepancies at the employer page.

If a restriction exists only on the employer page and is absent or contradicted in
the feed, RoleWeave cannot establish it from the observation. No automatic employer
page crawling, work-authorization inference, sponsorship guarantee or relocation
promise is introduced. Confirm employer terms before applying.

FreeHire and optional JSearch filters run locally after each observed provider page.
Experience/residence preferences are not new provider parameters and send no resume
or career history. Raw page counts, totals and next-page availability remain provider
observations. A page may have zero matches while later pages exist. Saved discovery
still observes only its first page; no hidden pagination or extra provider requests
are made. Experimental JSearch still needs its existing reviewed key/credit consent.

Synthetic regressions cover numeric bands, preferred/alternative text, Canada-only
remote restrictions, worldwide and unclear cases, cached-source immutability,
saved searches and recovery. Live provider coverage and employer-only restrictions
are not verified by these tests.
