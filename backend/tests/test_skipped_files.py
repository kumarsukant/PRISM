"""Skipped-files behaviour: files the scanner cannot read are reported with a plain reason, never dropped.

Unreadable files are simulated by patching open() / os.path.getsize, because a real lock is timing-
dependent. (scripts/smoke-test.ps1 still covers one real lock end to end.)

Run from the repo root with the dev venv:
    backend\\venv\\Scripts\\python.exe -m unittest discover -s backend\\tests -v
"""
import asyncio
import builtins
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP_DIR)

from PIL import Image  # noqa: E402

import services.services as services  # noqa: E402
from config import Config  # noqa: E402
from models.scan import DuplicateGroup, PhotoRecord, ScanSession  # noqa: E402
from services.services import FolderScanner, SafeDeleter  # noqa: E402

_real_open = builtins.open
_real_getsize = os.path.getsize


def _make_png(path: str) -> None:
    # Random 128x128 RGB noise compresses badly, so the file stays above the scanner's 10 KB minimum
    Image.frombytes("RGB", (128, 128), os.urandom(128 * 128 * 3)).save(path)


class SkippedFilesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="prism_unit_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        for name in ("a.png", "c.png"):
            _make_png(os.path.join(self.dir, name))
        shutil.copy(os.path.join(self.dir, "a.png"), os.path.join(self.dir, "b.png"))
        self.unreadable = os.path.join(self.dir, "c.png")
        self.scanner = FolderScanner(Config())

    def _open_failing_for(self, target: str):
        """open() that raises PermissionError for one path, exactly as Python does for a locked file."""
        def fake_open(file, *args, **kwargs):
            if os.path.normcase(os.fspath(file)) == os.path.normcase(target):
                raise PermissionError(13, "Permission denied", file)  # no winerror, like the real thing
            return _real_open(file, *args, **kwargs)
        return fake_open

    def _scan(self) -> ScanSession:
        session = ScanSession(folder_path=self.dir)
        self.scanner.scan_folder(self.dir, session)
        return session

    def test_locked_file_is_reported_not_dropped(self):
        with mock.patch.object(services, "open", self._open_failing_for(self.unreadable), create=True), \
             mock.patch.object(services, "_windows_open_error", return_value=32):
            session = self._scan()
        self.assertEqual(session.total_photos, 2)
        self.assertEqual(session.skipped_files, [
            {"file": "c.png", "path": self.unreadable, "reason": "open in another program"},
        ])

    def test_access_denied_gets_its_own_reason(self):
        with mock.patch.object(services, "open", self._open_failing_for(self.unreadable), create=True), \
             mock.patch.object(services, "_windows_open_error", return_value=5):
            session = self._scan()
        self.assertEqual([s["reason"] for s in session.skipped_files], ["Windows denied access"])

    def test_file_vanishing_during_discovery(self):
        def fake_getsize(path):
            if os.path.normcase(path) == os.path.normcase(self.unreadable):
                raise FileNotFoundError(2, "No such file", path)
            return _real_getsize(path)
        with mock.patch.object(services.os.path, "getsize", fake_getsize):
            session = self._scan()
        self.assertEqual(session.total_photos, 2)
        self.assertEqual([s["reason"] for s in session.skipped_files], ["no longer there (moved or deleted)"])

    def test_clean_scan_reports_nothing_skipped(self):
        session = self._scan()
        self.assertEqual(session.total_photos, 3)
        self.assertEqual(session.skipped_files, [])

    def test_skipped_list_is_sorted_by_path(self):
        for name in ("z.png", "m.png"):
            _make_png(os.path.join(self.dir, name))
        unreadable = {os.path.normcase(os.path.join(self.dir, n)) for n in ("z.png", "m.png", "c.png")}

        def fake_open(file, *args, **kwargs):
            if os.path.normcase(os.fspath(file)) in unreadable:
                raise PermissionError(13, "Permission denied", file)
            return _real_open(file, *args, **kwargs)
        with mock.patch.object(services, "open", fake_open, create=True), \
             mock.patch.object(services, "_windows_open_error", return_value=32):
            session = self._scan()
        self.assertEqual([s["file"] for s in session.skipped_files], ["c.png", "m.png", "z.png"])


class ProgressApiCapTest(unittest.TestCase):
    def test_progress_lists_at_most_20_but_counts_all(self):
        import main  # the FastAPI module; importing it does not start a server
        session = ScanSession(folder_path="C:\\x", status="completed", phase="completed")
        session.skipped_files = [
            {"file": f"f{i:02d}.png", "path": f"C:\\x\\f{i:02d}.png", "reason": "open in another program"}
            for i in range(25)
        ]
        main.scan_results[session.id] = session
        self.addCleanup(main.scan_results.pop, session.id, None)

        progress = asyncio.run(main.get_progress(session.id))
        self.assertEqual(progress["skipped_count"], 25)
        self.assertEqual(len(progress["skipped"]), 20)
        self.assertEqual(progress["skipped"][0]["file"], "f00.png")


class DeleteFailureReasonTest(unittest.TestCase):
    def test_locked_file_on_delete_gets_plain_reason_and_group_stays(self):
        d = tempfile.mkdtemp(prefix="prism_unit_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        keep, copy = os.path.join(d, "k.png"), os.path.join(d, "k - Copy.png")
        for p in (keep, copy):
            with open(p, "wb") as f:
                f.write(b"x" * 20000)
        p_keep = PhotoRecord(file_path=keep, file_size_bytes=20000)
        p_copy = PhotoRecord(file_path=copy, file_size_bytes=20000)
        group = DuplicateGroup(photo_ids=[p_keep.id, p_copy.id], kept_photo_id=p_keep.id)
        session = ScanSession(photos=[p_keep, p_copy], duplicate_groups=[group], status="completed")

        # What send2trash raises on Windows for a file that is open elsewhere: an OSError carrying winerror 32
        locked = OSError(None, "The process cannot access the file", copy, 32)
        with mock.patch("send2trash.send2trash", side_effect=locked):
            result = SafeDeleter(Config()).delete_duplicates(session, [group])

        self.assertEqual(result["files_deleted"], 0)
        self.assertEqual(result["failed"], [{"file": "k - Copy.png", "reason": "open in another program"}])
        self.assertEqual(len(session.duplicate_groups), 1)  # still listed so the user can retry
        self.assertTrue(os.path.exists(copy))


if __name__ == "__main__":
    unittest.main()
