"""Packaged-runtime smoke using a fresh, explicit synthetic output directory."""
import json
from pathlib import Path
import platform
import sys
import tkinter as tk

from demo_data import seed_practice
from job_store import JobStore
from runtime_paths import APP_VERSION


def run_self_test(folder, shelf_type):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    report = {"version": APP_VERSION, "python": platform.python_version(),
              "frozen": bool(getattr(sys, "frozen", False)), "checks": [], "ok": False}
    root = None
    try:
        store = JobStore(folder / "synthetic.db")
        job = seed_practice(store)
        report["checks"].append("sqlite-and-bundled-examples")
        root = tk.Tk()
        root.withdraw()
        shelf = shelf_type(root, store)
        shelf.show_saved(job)
        profile = shelf.open_profile()
        profile.withdraw()
        assert profile.fields["name"].get() == "Synthetic Candidate"
        profile.destroy()
        report["checks"].append("native-tk-profile")
        resume = shelf.open_resume()
        resume.withdraw()
        resume.facts.selection_set(0)
        resume.preview()
        resume.confirmed.set(True)
        resume.save()
        versions = store.list_resumes()
        assert len(versions) == 1 and versions[0]["has_pdf"], resume.status.get()
        identifier = versions[0]["id"]
        store.export_resume(identifier, folder / "synthetic-resume.pdf", "pdf")
        store.export_resume(identifier, folder / "synthetic-resume.html", "html")
        assert (folder / "synthetic-resume.pdf").read_bytes().startswith(b"%PDF-")
        assert b"Synthetic Candidate" in (folder / "synthetic-resume.html").read_bytes()
        resume.destroy()
        report["checks"].append("reviewed-html-pdf-and-bundled-fonts")
        store.record_application(job, "shortlisted", "Synthetic self-test observation", "2026-12-03")
        store.backup(folder / "synthetic-backup.json")
        restored = JobStore(folder / "restored.db")
        restored.restore(folder / "synthetic-backup.json")
        assert restored.load_resume(identifier)["snapshot"] == store.load_resume(identifier)["snapshot"]
        assert restored.application_history(job) == store.application_history(job)
        assert restored.active_profile()["snapshot"] == store.active_profile()["snapshot"]
        assert restored.restore(folder / "synthetic-backup.json") == (0, 2)
        report["checks"].append("v3-profile-resume-history-recovery")
        report["ok"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"[:4000]
    finally:
        if root is not None:
            root.destroy()
        (folder / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report["ok"]
