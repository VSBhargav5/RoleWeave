"""Packaged-runtime smoke using a fresh, explicit synthetic output directory."""
import json
from pathlib import Path
import platform
import sys
import tkinter as tk

from demo_data import seed_practice
from job_store import JobStore
from runtime_paths import APP_VERSION, RESOURCE_ROOT
from discovery import parse_board
from workspace_exports import review_list_csv, follow_up_list
from workspace_health import inspect_database


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
        discovery = shelf.open_discovery()
        discovery.withdraw()
        discovery.token.insert(0, "synthetic")
        discovery.company.insert(0, "Synthetic Discovered Co")
        discovery.market.set("International relocation")
        discovery.received(parse_board((RESOURCE_ROOT / "examples/greenhouse-synthetic.json").read_bytes(), "synthetic"))
        discovery.rows.selection_set("0")
        discovery.import_selected()
        assert len(store.list_jobs()) == 3, discovery.status.get()
        discovery.close()
        shelf.show_saved(job)
        editor = shelf.edit_evidence()
        editor.withdraw()
        assistant = editor.open_ai()
        assistant.withdraw()
        # Synthetic proposals exercise review/adoption without a provider call.
        assistant.received(["Spark operations required."])
        assistant.quotes.selection_set(0)
        assistant.reviewed.set(True)
        assistant.accept()
        editor.save()
        assert len(store.list_jobs()) == 4
        job = shelf.current_id
        report["checks"].append("offline-discovery-and-ai-quote-review")
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
        store.export_resume(identifier, folder / "synthetic-resume.txt", "txt")
        assert (folder / "synthetic-resume.pdf").read_bytes().startswith(b"%PDF-")
        assert b"Synthetic Candidate" in (folder / "synthetic-resume.html").read_bytes()
        resume.destroy()
        report["checks"].append("reviewed-html-pdf-and-bundled-fonts")
        store.record_application(job, "shortlisted", "Synthetic self-test observation", "2026-12-03")
        store.export_follow_up(job, folder / "synthetic-follow-up.ics")
        assert b"DTSTART;VALUE=DATE:20261203" in (folder / "synthetic-follow-up.ics").read_bytes()
        report["checks"].append("private-calendar-export")
        store.backup(folder / "synthetic-backup.json")
        review_list_csv(store.list_jobs(), folder / "synthetic-reviews.csv")
        assert follow_up_list(store, store.list_jobs(), folder / "synthetic-followups.ics") == 1
        assert JobStore.inspect_backup(folder / "synthetic-backup.json")["saved_reviews"] == 4
        assert inspect_database(store.path)["jobs"] == 4
        practice = shelf.open_practice_cards()
        assert practice.cards
        practice.render(True)
        practice.destroy()
        versions = shelf.open_versions()
        assert versions.rows
        versions.destroy()
        report["checks"].append("readiness-exports-inspection-and-rehearsal")
        restored = JobStore(folder / "restored.db")
        restored.restore(folder / "synthetic-backup.json")
        assert restored.load_resume(identifier)["snapshot"] == store.load_resume(identifier)["snapshot"]
        assert restored.application_history(job) == store.application_history(job)
        assert restored.active_profile()["snapshot"] == store.active_profile()["snapshot"]
        assert restored.restore(folder / "synthetic-backup.json") == (0, 4)
        report["checks"].append("v3-profile-resume-history-recovery")
        report["ok"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"[:4000]
    finally:
        if root is not None:
            root.destroy()
        (folder / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report["ok"]
