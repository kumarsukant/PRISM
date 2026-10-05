"""Which files the scanner reads: every supported extension, including both TIFF spellings.

Run from the repo root with the dev venv:
    backend\\venv\\Scripts\\python.exe -m unittest discover -s backend\\tests -v
"""
import os
import shutil
import sys
import tempfile
import unittest

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP_DIR)

from PIL import Image  # noqa: E402

from config import Config  # noqa: E402
from models.scan import ScanSession  # noqa: E402
from services.services import Deduper, FolderScanner  # noqa: E402


def _noise(size: int = 128) -> Image.Image:
    # Random noise compresses badly, so the file stays above the scanner's 10 KB minimum
    return Image.frombytes("RGB", (size, size), os.urandom(size * size * 3))


class TifTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="prism_unit_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _scan(self) -> ScanSession:
        session = ScanSession(folder_path=self.dir)
        FolderScanner(Config()).scan_folder(self.dir, session)
        Deduper(Config()).find_exact_duplicates(session)
        return session

    def test_tif_and_tiff_are_both_scanned_and_grouped(self):
        _noise().save(os.path.join(self.dir, "scan.tif"), format="TIFF")
        shutil.copy(os.path.join(self.dir, "scan.tif"), os.path.join(self.dir, "scan - Copy.TIF"))
        _noise().save(os.path.join(self.dir, "other.tiff"), format="TIFF")
        session = self._scan()
        self.assertEqual(session.total_photos, 3)
        self.assertEqual(session.skipped_files, [])
        self.assertEqual(len(session.duplicate_groups), 1)
        names = {os.path.basename(p.file_path) for p in session.photos}
        self.assertEqual(names, {"scan.tif", "scan - Copy.TIF", "other.tiff"})
        tif = next(p for p in session.photos if p.file_path.endswith("scan.tif"))
        self.assertEqual((tif.width_px, tif.height_px), (128, 128))


if __name__ == "__main__":
    unittest.main()
