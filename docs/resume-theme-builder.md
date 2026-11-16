# Portable resume theme builder (v0.28)

In a saved job, open Build application resume. Existing Classic/Slate/Editorial
presets stay available and their HTML bytes remain unchanged. Expand Build or
import your own theme, choose Use custom theme and adjust:

- Six-digit accent color with at least4.5:1 contrast against white paper.
- Body9–12pt, name18–30pt, margins14–24mm; whole numbers only.
- Sans (embedded Bitstream Vera PDF) or Serif (standard PDF Times).
- A4 or Letter paper.

Preview again after any change, inspect the exact PDF pagination, then explicitly
confirm before freezing. The browser HTML preview uses available Arial or Georgia/
Times fonts; the PDF uses its stated fonts. It is an aid, not a pixel-identical PDF
renderer. Download the PDF preview to check exact pages. Serif rejects characters
outside Windows-1252 instead of silently substituting them; Sans retains existing
bundled-font glyph checks. Standard PDF Times is a core PDF font, not an additional
font file embedded by this app. Unknown Unicode scripts are not promised supported.

Export theme JSON validates and downloads styling only. Import accepts at most2KiB
of strict JSON with duplicate/unknown fields refused. No facts/profile/contact info,
CSS, script, URL, font file or network font is part of the format. Changing controls
while an import is pending prevents its late response from overwriting newer edits.
Imported styling resets preview/confirmation. Saving a shared theme file is separate
from saving a reviewed document; it does not modify the career profile.

Each newly saved custom resume freezes its validated configuration in the existing
v2 snapshot plus exact HTML/PDF bytes. Managed recovery replays HTML against that
configuration and original selected profile facts; rehashed altered styling is
refused. Old v1/v2 preset documents remain supported. Saved PDFs are not rerendered
during recovery; fingerprints verify stored bytes, not factual truth or recipient
acceptance. Styling doesn't guarantee ATS compatibility, interviews or hiring.

## Runnable verification and focused practice

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_resume_theme.py -v
```

Eight targeted tests cover strict bounds/contrast/JSON, old preset fingerprints,
escaping, deterministic selected-only PDFs, paper dimensions/unsupported characters,
long pagination, frozen source identity/recovery and stale preview refusal. Actual
browser tests cover import/export, rejected unsafe data, rendered preview color/font
and custom PDF freeze. Synthetic Sans A4/Serif Letter and four-page stress PDFs were
rendered and all six pages inspected locally. No personal layout acceptance claimed.

Use a separate synthetic shelf for60–90minutes: predict why white is rejected;
choose a dark accent, export/import it and verify the JSON contains no career data.
Preview then change margins; explain why renewed review is needed. Compare the
HTML preview with the downloaded PDF, freeze one version and recover separately.
Tradeoff: a small portable schema preserves source replay and limits surprising
content, while excluding arbitrary CSS and remote fonts. No learning completion
or usefulness is claimed without your practice.
