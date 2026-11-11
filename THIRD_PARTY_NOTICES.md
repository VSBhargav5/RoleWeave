# Third-party components

RoleWeave is original software under the repository LICENSE. The portable build
bundles Python, Tcl/Tk, ReportLab, Pillow and charset-normalizer. Their license
texts are copied into the build's `licenses/` directory and package metadata.

- Python: Python Software Foundation license; https://www.python.org/psf/license/
- Tcl/Tk: Tcl/Tk license; https://www.tcl-lang.org/software/tcltk/license.html
- ReportLab: BSD license; https://pypi.org/project/reportlab/5.1.0/
- Pillow: license text distributed with Pillow; https://pypi.org/project/Pillow/13.0.0/
- charset-normalizer: MIT; https://pypi.org/project/charset-normalizer/3.5.2/
- Bitstream Vera fonts: bundled with ReportLab, under the included
  `bitstream-vera-license.txt`. The font files are embedded in generated PDFs.

PyInstaller is a build tool under its distribution exception; it is not the app's
license. See https://pyinstaller.org/en/stable/license.html . Its build tools and
pypdf are development dependencies rather than features of the application.

No upstream Dossier, Jobleft, Cue or StudyFrame code/assets are imported.


Optional Google Calendar browser consent uses Google's maintained
`google-auth-oauthlib` and `google-auth` (Apache2.0), with requests-oauthlib
(ISC), OAuthlib (BSD), Requests (Apache2.0), urllib3 (MIT), certifi (MPL2.0),
idna (BSD), cryptography (Apache2.0/BSD), cffi (MIT), pycparser (BSD), pyasn1
(BSD) and pyasn1-modules (BSD). Distribution license texts and package metadata
are included in the portable build. See each pinned distribution's metadata
and license under `licenses/` for the authoritative terms and attributions.
These are dependencies; no Google Calendar API server code is imported.
