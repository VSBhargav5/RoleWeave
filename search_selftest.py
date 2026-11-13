"""Explicit, opt-in public search check for the installed/frozen runtime."""
import json
from pathlib import Path
import sys
import traceback
from job_search import JobSearch
from runtime_paths import APP_VERSION


def run_search_check(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    report = {"version": APP_VERSION, "frozen": bool(getattr(sys, "frozen", False)), "ok": False,
              "query": "data engineer", "location": "london"}
    try:
        result = JobSearch().search("data engineer", "london")
        report.update(ok=True, accepted=len(result['jobs']), excluded=len(result['excluded']),
                      source_sha256=result['source_sha256'])
    except Exception as exc:
        # No provider body, personal records, credentials, arbitrary exception text or paths.
        report.update(error_type=type(exc).__name__, errno=getattr(exc, 'errno', None),
                      functions=[frame.name for frame in traceback.extract_tb(exc.__traceback__)])
    (destination / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report['ok']
