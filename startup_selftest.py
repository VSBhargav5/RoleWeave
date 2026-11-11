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
        from provider_boards import parse_source
        from discovery_archive import export_archive, load_archive, compare_observations
        for provider, filename in (("lever", "lever-synthetic.json"),
                                   ("lever-eu", "lever-synthetic.json"),
                                   ("ashby", "ashby-synthetic.json")):
            feed = parse_source((RESOURCE_ROOT / "examples" / filename).read_bytes(), provider, "synthetic")
            discovery.provider.set(provider)
            discovery.received(feed)
            discovery.rows.selection_set("0")
            discovery.preview_selected()
            assert feed["jobs"][0]["title"] in discovery.rows.item("0", "values")
            archive = folder / (provider + "-observation.json")
            export_archive(feed, archive)
            replay = load_archive(archive)
            assert replay == feed
            assert all(row["state"] == "unchanged" for row in compare_observations(feed, replay))
        report["checks"].append("multi-provider-discovery-and-byte-exact-offline-replay")
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
        from application_dossier import verify_dossier_bytes
        from cover_letter import export_letter
        from correspondence import record_correspondence
        from recipient_bundle import export_recipient_bundle
        from submission_receipt import record_submission
        from datetime import date, datetime, timezone
        letter = shelf.open_letter()
        letter.withdraw()
        letter.choices.selection_set(0)
        letter.motivation.insert("1.0", "Synthetic interest in reliable data workflows.")
        letter.preview()
        assert letter.prepared is not None, letter.status.get()
        letter_bytes = letter.prepared[1]
        export_letter(letter_bytes, folder / "synthetic-letter.json", "json", confirmed=True)
        export_letter(letter_bytes, folder / "synthetic-letter.txt", "txt", confirmed=True)
        letter.destroy()
        dossier = shelf.open_dossier()
        dossier.withdraw()
        dossier.choices.selection_set(0)
        dossier.letter_snapshot = letter_bytes
        dossier.preview()
        assert dossier.prepared is not None, dossier.status.get()
        dossier_bytes = dossier.prepared[1]
        from safe_export import publish_bytes
        publish_bytes(folder / "synthetic-private-dossier.zip", dossier_bytes)
        assert verify_dossier_bytes(dossier_bytes)["job"]["id"] == job
        export_recipient_bundle(dossier_bytes, folder / "synthetic-recipient-files.zip", ["pdf", "letter"], confirmed=True)
        dossier.destroy()
        record_submission(store, job, dossier_bytes, date.today().isoformat(), "Employer portal",
                          "Synthetic reference", "Offline synthetic observation only.", confirmed=True)
        mail = (RESOURCE_ROOT / "examples/reply-synthetic.eml").read_bytes()
        record_correspondence(store, job, mail, "Please suggest a time", "Synthetic correspondence observation.", confirmed=True)
        assert store.application_history(job)[-1]["stage"] == "applied"
        report["checks"].append("private-dossier-letter-recipient-files-and-manual-correspondence")
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
        from employer_watchlist import read_watchlist, save_watchlist
        from watchlist_fetch import collection_rows
        from provider_boards import parse_source
        watchlist_data = read_watchlist(RESOURCE_ROOT / "examples/watchlist-synthetic.json")
        save_watchlist(watchlist_data, folder / "synthetic-watchlist.json")
        watchlist = shelf.open_watchlist()
        watchlist.withdraw()
        watchlist.boards = watchlist_data["boards"]
        watchlist.name.set(watchlist_data["name"])
        watchlist.refresh_rows()
        watchlist.rows.selection_set("0")
        watchlist.load_selected()
        board_window = watchlist.open_board()
        assert board_window is not None, watchlist.status.get()
        assert board_window.provider.get() == "lever"
        assert board_window.feed is None
        board_window.destroy()
        from collection_archive import archive_collection, read_collection_archive
        from collection_compare import compare_collections, export_comparison
        from collection_export import export_collection_csv
        from watchlist_fetch import validate_collection
        collection_started = datetime.now(timezone.utc).isoformat()
        feeds = [{"board_index": index, "feed": parse_source((RESOURCE_ROOT / "examples" / filename).read_bytes(), provider, "synthetic")}
                 for index, (provider, filename) in enumerate((("lever", "lever-synthetic.json"), ("ashby", "ashby-synthetic.json")))]
        collection = {"format": "roleweave-collection-v1", "watchlist": watchlist_data,
                      "selected_indices": [0, 1], "feeds": feeds, "failures": [],
                      "started_at": collection_started, "finished_at": datetime.now(timezone.utc).isoformat()}
        validate_collection(collection)
        assert len(collection_rows(collection)) == 2
        archive_collection(collection, folder / "synthetic-collection.json")
        replay = read_collection_archive(folder / "synthetic-collection.json")
        assert replay == collection
        assert compare_collections(collection, replay)["scope_counts"] == {"compared": 2}
        export_comparison(collection, replay, folder / "synthetic-collection-comparison.json")
        assert export_collection_csv(collection, folder / "synthetic-collection-shortlist.csv") == 2
        watchlist.rows.selection_set("0", "1")
        watchlist.load_selected()
        collection_window = watchlist.open_collection()
        assert collection_window is not None, watchlist.status.get()
        collection_window.received(replay)
        collection_window.rows.selection_set("0")
        collection_window.preview_selected()
        assert "Response SHA256" in collection_window.preview.get("1.0", "end")
        collection_window.close()
        watchlist.destroy()
        report["checks"].append("selected-source-collection-offline-replay-comparison-and-shortlist")
        report["checks"].append("portable-watchlist-and-offline-source-reuse")

        from rehearsal_journal import read_rehearsal, rehearsal_snapshot
        from rehearsal_pack import export_pack
        from rehearsal_compare import compare_rehearsals, export_comparison as export_rehearsal_comparison
        rehearsal = shelf.open_rehearsal()
        rehearsal.withdraw()
        rehearsal.choices.selection_set(0)
        rehearsal.start_selected()
        rehearsal.answer.insert("1.0", "Synthetic practice answer, not employment experience.")
        rehearsal.confirmed.set(True)
        from unittest.mock import patch
        with patch("rehearsal_window.filedialog.asksaveasfilename", return_value=str(folder / "synthetic-rehearsal.json")):
            rehearsal.save()
        first = read_rehearsal(folder / "synthetic-rehearsal.json")[0]
        assert rehearsal_snapshot(first)[0]["learning_verified"] is False
        rehearsal.answer.insert("end", " Explain validation boundaries.")
        rehearsal.confirmed.set(True)
        with patch("rehearsal_window.filedialog.asksaveasfilename", return_value=str(folder / "synthetic-rehearsal-revised.json")):
            rehearsal.save()
        second = read_rehearsal(folder / "synthetic-rehearsal-revised.json")[0]
        assert compare_rehearsals(first, second)["questions"][0]["state"] == "draft_changed"
        export_pack(second, folder / "synthetic-private-questions.txt", confirmed=True)
        export_pack(second, folder / "synthetic-private-answers.txt", include_answers=True, confirmed=True)
        export_rehearsal_comparison(first, second, folder / "synthetic-rehearsal-comparison.json", confirmed=True)
        rehearsal.destroy()
        report["checks"].append("native-source-bound-rehearsal-drafts-private-packs-and-comparison")

        report["ok"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"[:4000]
    finally:
        if root is not None:
            root.destroy()
        (folder / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report["ok"]
