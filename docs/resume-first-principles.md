# A resume is a selection of checked claims

Use **Start here / help → Open synthetic practice workspace**, or run
`python desktop.py --demo`. Your real shelf is separate. This exercise takes
60–90 minutes; implementation does not mean you have completed the exercise.

1. Open **My career profile** and inspect both facts and their sources. Which
   claim describes a project, and which describes practice rather than employment?
2. Open **Build / export resume**. Predict which facts will be offered: the
   unreviewed draft must be excluded. Select the Python project, preview, approve
   and save. Export PDF and HTML to new filenames; inspect both yourself.
3. Reopen the profile, correct the project wording, explicitly review the fact
   and save a new profile version. Reopen the earlier resume under Saved versions.
   Predict its wording before exporting again: the older wording must remain.
4. In a job's evidence review, copy a reviewed career fact. Confirm that it is
   not automatically linked to a requirement. Link only where relevant; a valid
   ID or reviewed checkbox cannot establish that you meet the requirement.
5. Back up the full shelf. Start a separate empty database with `--db`, restore,
   and compare profile versions, resume bytes and application history. Restore
   again: identical records must not multiply. Keep backups private.

The rule is: document = explicitly selected reviewed facts + the chosen profile
version's identity and summary. There is no language-model rewriting. Your review
is an assertion, not external verification; check every claim before using it.

The tradeoff is deliberate: frozen versions preserve exactly what you prepared,
but corrections require creating a new version rather than silently updating old
documents. This is preparation history, not proof that an application was sent.

To reproduce the synthetic checks:

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python desktop.py --self-test out/my-new-smoke
```

The PDF font rejects unsupported characters explicitly. For those names/scripts,
choose HTML-only and inspect your browser's PDF output. Neither path proves ATS
compatibility. No personal information leaves the local app.
