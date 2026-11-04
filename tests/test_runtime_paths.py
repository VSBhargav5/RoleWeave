import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from demo_data import seed_practice
from job_store import JobStore
from runtime_paths import RESOURCE_ROOT, default_database_path, new_practice_path


class RuntimeTests(unittest.TestCase):
    def test_source_keeps_existing_project_database_location(self):
        with patch.object(sys, "frozen", False, create=True):
            self.assertEqual(default_database_path(), RESOURCE_ROOT / "private" / "jobs.db")

    def test_portable_data_is_outside_extraction_or_executable_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(sys, "frozen", True, create=True), patch.dict(os.environ, {"LOCALAPPDATA": temp}):
                self.assertEqual(default_database_path(), Path(temp) / "RoleWeave" / "jobs.db")

    def test_practice_is_separate_and_never_overwrites_an_existing_shelf(self):
        with tempfile.TemporaryDirectory() as temp:
            first = new_practice_path(temp)
            second = new_practice_path(temp)
            self.assertNotEqual(first, second)
            store = JobStore(first)
            seed_practice(store)
            self.assertEqual(len(store.list_jobs()), 2)
            self.assertEqual(len(store.list_jobs("relocation")), 1)
            self.assertEqual(store.active_profile()["profile"]["name"], "Synthetic Candidate")
            with self.assertRaises(ValueError):
                seed_practice(store)
