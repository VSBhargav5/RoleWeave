"""Stable data locations for source and portable Windows builds."""
import os
from pathlib import Path
import sys
import tempfile

APP_VERSION = "0.7.0"
RESOURCE_ROOT = Path(__file__).resolve().parent


def default_database_path():
    if not getattr(sys, "frozen", False):
        return RESOURCE_ROOT / "private" / "jobs.db"
    local = os.environ.get("LOCALAPPDATA", "")
    base = Path(local) if local and Path(local).is_absolute() else Path.home() / ".local" / "share"
    return base / "RoleWeave" / "jobs.db"


def new_practice_path(parent):
    base = Path(parent) / "practice"
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="synthetic-", dir=base)) / "jobs.db"
