"""Scan insights and coverage: definitions, thresholds, tips, recompute after delete, and the guarantee that
online-only (cloud placeholder) files are never opened.

Most tests use synthetic sessions (paths need not exist). Run from the repo root with the dev venv:
    backend\\venv\\Scripts\\python.exe -m unittest discover -s backend\\tests -v
"""
import asyncio
import builtins
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP_DIR)

import PIL.Image  # noqa: E402
from PIL import Image  # noqa: E402

import services.services as services  # noqa: E402
from config import Config  # noqa: E402
from models.scan import PhotoRecord, ScanSession  # noqa: E402
from services.insights import build_insights, find_folder, folder_id, folder_key, tag_for  # noqa: E402
from services.services import Deduper, FolderScanner, SafeDeleter  # noqa: E402

ROOT = "C:\\Scan"


def session_of(files: dict, root: str = ROOT) -> ScanSession:
    """files: {relative path: content label}. Same label = exact duplicates. Sizes are 1000 bytes each."""
    photos = [PhotoRecord(file_path=os.path.join(root, rel), file_size_bytes=1000, file_hash_md5=label)
              for rel, label in files.items()]
    session = ScanSession(folder_path=root, photos=photos, total_photos=len(photos), status="completed")
    Deduper(Config()).find_exact_duplicates(session)
    return session


def folder(result: dict, rel: str) -> dict:
    return next(f for f in result["folders"] if f["relative_path"] == rel)


class DefinitionsTest(unittest.TestCase):
    def test_same_folder_only(self):
        r = build_insights(session_of({"A\\1.jpg": "x", "A\\1 - Copy.jpg": "x", "A\\2.jpg": "y", "B\\3.jpg": "z"}))
        a = folder(r, "A")
        self.assertEqual((a["photos"], a["photos_with_duplicate"], a["extra_copies"]), (3, 2, 1))
        self.assertEqual((a["inside_share"], a["tag"]), (1.0, "same_folder"))
        self.assertAlmostEqual(a["share_with_duplicate"], 0.667)
        self.assertEqual(r["pairs"], [])
        self.assertEqual(r["totals"]["groups_in_one_folder"], 1)
        self.assertEqual(r["totals"]["groups_across_folders"], 0)
        self.assertEqual(len(r["folders"]), 1)  # B has no duplicates, so it is not listed
        self.assertEqual(r["totals"]["folders"], 2)

    def test_cross_folder_only(self):
        r = build_insights(session_of({"A\\1.jpg": "x", "B\\1.jpg": "x", "A\\2.jpg": "y", "B\\2.jpg": "y"}))
        for rel in ("A", "B"):
            self.assertEqual((folder(r, rel)["inside_share"], folder(r, rel)["tag"]), (0.0, "other_folders"))
        self.assertEqual(r["pairs"], [{"a": {"id": folder(r, "A")["id"], "relative_path": "A"},
                                       "b": {"id": folder(r, "B")["id"], "relative_path": "B"},
                                       "shared_groups": 2}])
        self.assertEqual(r["totals"]["groups_across_folders"], 2)

    def test_mixed(self):
        # A: one group inside A (2 memberships), one shared with B (1 membership): 2/3 = 0.667 -> mixed
        r = build_insights(session_of({"A\\1.jpg": "x", "A\\1 (1).jpg": "x", "A\\2.jpg": "y", "B\\2.jpg": "y"}))
        self.assertEqual((folder(r, "A")["inside_share"], folder(r, "A")["tag"]), (0.667, "mixed"))

    def test_kept_copy_still_counts_as_photo_with_duplicate(self):
        r = build_insights(session_of({"A\\1.jpg": "x", "B\\1 - Copy.jpg": "x"}))
        self.assertEqual(folder(r, "A")["photos_with_duplicate"], 1)  # A holds the kept one
        self.assertEqual(folder(r, "A")["extra_copies"], 0)
        self.assertEqual(folder(r, "B")["extra_copies"], 1)

    def test_single_folder_scan(self):
        r = build_insights(session_of({"1.jpg": "x", "1 - Copy.jpg": "x", "2.jpg": "y"}))
        self.assertEqual(r["totals"]["folders"], 1)
        self.assertEqual(r["pairs"], [])
        self.assertEqual(folder(r, "")["tag"], "same_folder")  # "" = the scanned folder itself
        self.assertEqual(r["root_name"], "Scan")

    def test_group_spanning_three_folders(self):
        r = build_insights(session_of({"A\\1.jpg": "x", "B\\1.jpg": "x", "C\\1.jpg": "x", "C\\1 - Copy.jpg": "x"}))
        self.assertEqual(r["totals"]["groups_across_3_plus_folders"], 1)
        self.assertEqual(r["totals"]["groups_across_folders"], 1)
        got = sorted((p["a"]["relative_path"], p["b"]["relative_path"], p["shared_groups"]) for p in r["pairs"])
        self.assertEqual(got, [("A", "B", 1), ("A", "C", 1), ("B", "C", 1)])  # once per pair, not per copy
        self.assertEqual(folder(r, "C")["photos_with_duplicate"], 2)

    def test_tag_thresholds(self):
        self.assertEqual(tag_for(0.70), "same_folder")
        self.assertEqual(tag_for(0.699), "mixed")
        self.assertEqual(tag_for(0.30), "other_folders")
        self.assertEqual(tag_for(0.301), "mixed")
        # Through real data: 7 of 10 memberships inside the folder -> exactly 0.70 -> same_folder
        files = {"A\\in1.jpg": "x", "A\\in2.jpg": "x", "A\\in3.jpg": "x", "A\\in4.jpg": "x",
                 "A\\in5.jpg": "x", "A\\in6.jpg": "x", "A\\in7.jpg": "x"}
        for i in range(3):
            files[f"A\\out{i}.jpg"] = f"o{i}"
            files[f"B\\out{i}.jpg"] = f"o{i}"
        r = build_insights(session_of(files))
        self.assertEqual((folder(r, "A")["inside_share"], folder(r, "A")["tag"]), (0.7, "same_folder"))

    @unittest.skipUnless(sys.platform == "win32", "Windows path casing")
    def test_windows_path_casing_is_one_folder(self):
        photos = [PhotoRecord(file_path="C:\\Pics\\Camera\\1.jpg", file_hash_md5="x"),
                  PhotoRecord(file_path="c:\\pics\\CAMERA\\1 - Copy.jpg", file_hash_md5="x")]
        session = ScanSession(folder_path="C:\\Pics", photos=photos, status="completed")
        Deduper(Config()).find_exact_duplicates(session)
        r = build_insights(session)
        self.assertEqual(r["totals"]["folders"], 1)
        self.assertEqual(r["pairs"], [])
        # Real paths in one folder share the disk's casing; with mixed input the first path by sort order wins
        self.assertEqual(r["folders"][0]["relative_path"].lower(), "camera")
        self.assertEqual(r, build_insights(session) | {"scan_id": r["scan_id"]})  # deterministic
        self.assertEqual(r["folders"][0]["tag"], "same_folder")

    def test_drive_root_scan(self):
        r = build_insights(session_of({"Pics\\1.jpg": "x", "1.jpg": "x"}, root="D:\\"))
        self.assertEqual(r["root_name"], "D:")
        self.assertEqual(sorted(f["relative_path"] for f in r["folders"]), ["", "Pics"])

    def test_top_ten_and_rest_count(self):
        files = {}
        for i in range(12):
            files[f"F{i:02d}\\a.jpg"] = f"g{i}"
            files[f"F{i:02d}\\a - Copy.jpg"] = f"g{i}"
        r = build_insights(session_of(files))
        self.assertEqual(len(r["folders"]), 10)
        self.assertEqual(r["folders_with_duplicates_not_shown"], 2)
        self.assertEqual(r["folders"][0]["relative_path"], "F00")  # ties broken by path

    def test_folder_lookup_by_id(self):
        s = session_of({"A\\1.jpg": "x", "B\\1.jpg": "x"})
        fid = folder_id(folder_key(os.path.join(ROOT, "A", "1.jpg")))
        self.assertEqual(find_folder(s, fid), os.path.join(ROOT, "A"))
        self.assertIsNone(find_folder(s, "000000000000"))


class TipsTest(unittest.TestCase):
    def tips(self, files):
        return {t["id"]: t for t in build_insights(session_of(files))["tips"]}

    def test_copy_and_number_suffix_are_separate_tips(self):
        files = {}
        for i in range(5):
            files[f"A\\p{i}.jpg"] = f"c{i}"
            files[f"A\\p{i} - Copy.jpg"] = f"c{i}"
            files[f"A\\q{i}.jpg"] = f"n{i}"
            files[f"A\\q{i} (1).jpg"] = f"n{i}"
        tips = self.tips(files)
        self.assertEqual(tips["copy_suffix"]["count"], 5)
        self.assertEqual(tips["number_suffix"]["count"], 5)

    def test_name_tips_stay_silent_below_the_bar(self):
        files = {}
        for i in range(4):  # 4 < 5
            files[f"A\\p{i}.jpg"] = f"c{i}"
            files[f"A\\p{i} - Copy.jpg"] = f"c{i}"
        self.assertNotIn("copy_suffix", self.tips(files))
        # 5 names but under 20% of 30 extra copies
        files = {}
        for i in range(5):
            files[f"A\\p{i}.jpg"] = f"c{i}"
            files[f"A\\p{i} - Copy.jpg"] = f"c{i}"
        for i in range(25):
            files[f"A\\r{i}.jpg"] = f"r{i}"
            files[f"B\\r{i}x.jpg"] = f"r{i}"
        self.assertNotIn("copy_suffix", self.tips(files))

    def test_folder_pair_tip(self):
        files = {}
        for i in range(10):
            files[f"Camera\\{i}.jpg"] = f"g{i}"
            files[f"Chat\\{i}.jpg"] = f"g{i}"
        tip = self.tips(files)["folder_pair"]
        self.assertEqual(tip["shared_groups"], 10)
        self.assertEqual((tip["a"]["relative_path"], tip["b"]["relative_path"]), ("Camera", "Chat"))
        files.pop("Camera\\9.jpg")
        files.pop("Chat\\9.jpg")  # 9 shared < 10
        self.assertNotIn("folder_pair", self.tips(files))

    def test_same_folder_and_spread_tips(self):
        files = {}
        for i in range(5):
            files[f"A\\s{i}.jpg"] = f"s{i}"
            files[f"A\\s{i}b.jpg"] = f"s{i}"   # 10 memberships, all inside A
            for f in ("X", "Y", "Z"):
                files[f"{f}\\t{i}.jpg"] = f"t{i}"  # 5 groups across 3 folders
        tips = self.tips(files)
        self.assertEqual(tips["same_folder"]["folder"]["relative_path"], "A")
        self.assertEqual(tips["spread"]["count"], 5)

    def test_no_tips_for_a_small_clean_scan(self):
        self.assertEqual(self.tips({"A\\1.jpg": "x", "B\\1.jpg": "x"}), {})

    def test_at_most_four_tips(self):
        files = {}
        for i in range(10):
            files[f"A\\p{i}.jpg"] = f"c{i}"
            files[f"A\\p{i} - Copy.jpg"] = f"c{i}"
            files[f"A\\q{i}.jpg"] = f"n{i}"
            files[f"A\\q{i} (1).jpg"] = f"n{i}"
            for f in ("X", "Y", "Z"):
                files[f"{f}\\t{i}.jpg"] = f"t{i}"
        r = build_insights(session_of(files))
        self.assertEqual(len(r["tips"]), 4)

    def test_headlines(self):
        r = build_insights(session_of({"A\\1.jpg": "x", "A\\1 - Copy.jpg": "x", "B\\2.jpg": "y", "C\\2.jpg": "y"}))
        top, split = r["headlines"]
        self.assertEqual((top["id"], top["folder"]["relative_path"], top["tag"]), ("top_folder", "A", "same_folder"))
        self.assertEqual((split["groups_in_one_folder"], split["groups_across_folders"]), (1, 1))
        self.assertEqual(build_insights(session_of({"A\\1.jpg": "x", "B\\2.jpg": "y"}))["headlines"], [])


class RecomputeAfterDeleteTest(unittest.TestCase):
    def test_insights_follow_deletes_and_folder_ids_stay(self):
        d = tempfile.mkdtemp(prefix="prism_unit_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        files = {"A\\1.jpg": "x", "A\\1 - Copy.jpg": "x", "A\\2.jpg": "y", "B\\2.jpg": "y"}
        for rel in files:
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            with open(os.path.join(d, rel), "wb") as f:
                f.write(b"x" * 1000)
        s = session_of(files, root=d)
        before = build_insights(s)
        a_id = folder(before, "A")["id"]
        inside = next(g for g in s.duplicate_groups if len({folder_key(p.file_path) for p in s.photos if p.id in g.photo_ids}) == 1)
        with mock.patch("send2trash.send2trash"):
            SafeDeleter(Config()).delete_duplicates(s, [inside])
        after = build_insights(s)
        self.assertEqual(before["totals"]["duplicate_groups"], 2)
        self.assertEqual(after["totals"]["duplicate_groups"], 1)
        self.assertEqual(folder(after, "A")["id"], a_id)
        self.assertEqual((folder(after, "A")["photos"], folder(after, "A")["tag"]), (2, "other_folders"))


class PerformanceTest(unittest.TestCase):
    def test_25k_photos_is_fast(self):
        photos = []
        for f in range(250):  # 250 folders x 100 photos
            for i in range(100):
                if i % 3 == 0:
                    label = f"pair{f // 2}-{i}"   # same content in folders 2k and 2k+1: across-folder groups
                elif i % 3 == 1 and i + 1 < 100:
                    label = f"in{f}-{i // 3}"     # with the next photo: same-folder groups
                else:
                    label = f"in{f}-{(i - 1) // 3}" if i % 3 == 2 else f"u{f}-{i}"
                photos.append(PhotoRecord(file_path=f"C:\\Big\\F{f:03d}\\IMG_{i:04d}.jpg",
                                          file_size_bytes=2_000_000, file_hash_md5=label))
        s = ScanSession(folder_path="C:\\Big", photos=photos, status="completed")
        Deduper(Config()).find_exact_duplicates(s)
        start = time.perf_counter()
        r = build_insights(s)
        elapsed = time.perf_counter() - start
        self.assertEqual(r["totals"]["photos"], 25_000)
        self.assertGreater(r["totals"]["duplicate_groups"], 1000)
        self.assertLess(elapsed, 1.0, f"build_insights took {elapsed:.2f}s for 25k photos")
        print(f"\n  25k photos, {r['totals']['duplicate_groups']} groups: build_insights {elapsed * 1000:.0f} ms", file=sys.stderr)


class CoverageAndOnlineOnlyTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="prism_unit_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        for name in ("a.png", "cloud.png"):
            Image.frombytes("RGB", (128, 128), os.urandom(128 * 128 * 3)).save(os.path.join(self.dir, name))
        shutil.copy(os.path.join(self.dir, "a.png"), os.path.join(self.dir, "a - Copy.png"))
        for name, size in (("p.heic", 20000), ("q.HEIF", 20000), ("r.CR2", 20000), ("s.dng", 20000),
                           ("tiny.png", 500), ("notes.txt", 20000)):
            with open(os.path.join(self.dir, name), "wb") as f:
                f.write(b"0" * size)
        self.cloud = os.path.join(self.dir, "cloud.png")

    def _watch_opens(self):
        """Patch every way the backend reads file data, recording the paths it was asked to open."""
        opened = []
        real_open, real_image_open = builtins.open, PIL.Image.open

        def spy_open(file, *args, **kwargs):
            opened.append(os.path.normcase(os.fspath(file)))
            return real_open(file, *args, **kwargs)

        def spy_image_open(fp, *args, **kwargs):
            if isinstance(fp, (str, os.PathLike)):
                opened.append(os.path.normcase(os.fspath(fp)))
            return real_image_open(fp, *args, **kwargs)
        patches = [mock.patch.object(services, "open", spy_open, create=True),
                   mock.patch.object(services.Image, "open", spy_image_open)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return opened

    def _scan(self) -> ScanSession:
        s = ScanSession(folder_path=self.dir)
        FolderScanner(Config()).scan_folder(self.dir, s)
        return s

    def test_coverage_counters(self):
        s = self._scan()
        self.assertEqual(s.coverage, {"heic": 2, "raw": 2, "under_10kb": 1, "online_only": 0,
                                      "photos_checked": 3, "folders_checked": 1})

    def test_online_only_file_is_counted_and_never_opened_during_discovery(self):
        real_entry_info = services._entry_info

        def fake_entry_info(entry):
            size, attributes = real_entry_info(entry)
            if os.path.normcase(entry.path) == os.path.normcase(self.cloud):
                attributes |= services.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
            return size, attributes
        opened = self._watch_opens()
        with mock.patch.object(services, "_entry_info", fake_entry_info):
            s = self._scan()
        self.assertEqual(s.coverage["online_only"], 1)
        self.assertEqual(s.total_photos, 2)
        self.assertEqual(s.skipped_files, [])  # counted as online-only, not as unreadable
        self.assertNotIn(os.path.normcase(self.cloud), opened)
        self.assertIn(os.path.normcase(os.path.join(self.dir, "a.png")), opened)  # the spy works

    def test_file_made_online_only_after_discovery_is_never_opened(self):
        def fake_attributes(path):
            return services.FILE_ATTRIBUTE_RECALL_ON_OPEN if os.path.normcase(path) == os.path.normcase(self.cloud) else 0x20
        opened = self._watch_opens()
        with mock.patch.object(services, "file_attributes", fake_attributes):
            s = self._scan()
        self.assertEqual((s.coverage["online_only"], s.total_photos), (1, 2))
        self.assertNotIn(os.path.normcase(self.cloud), opened)

    def test_every_recall_flag_counts_as_online_only(self):
        for flag in (0x400000, 0x40000, 0x1000):
            self.assertTrue(services.is_online_only(flag | 0x20))
        self.assertFalse(services.is_online_only(0x20))     # ARCHIVE: an ordinary local file
        self.assertFalse(services.is_online_only(0x80000))  # PINNED ("always keep on this device")
        self.assertFalse(services.is_online_only(None))

    def test_thumbnail_never_opens_an_online_only_file(self):
        import main
        s = self._scan()
        main.scan_results[s.id] = s
        self.addCleanup(main.scan_results.pop, s.id, None)
        target = os.path.join(self.dir, "a.png")
        with mock.patch.object(main, "file_attributes", return_value=services.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS), \
             mock.patch.object(PIL.Image, "open", side_effect=AssertionError("opened an online-only file")), \
             mock.patch("tempfile.gettempdir", return_value=self.dir):  # empty cache, so it would have to open the file
            response = asyncio.run(main.get_thumbnail(target))
        self.assertEqual(response.status_code, 409)


class EndpointsTest(unittest.TestCase):
    def setUp(self):
        import main
        self.main = main
        self.s = session_of({"A\\1.jpg": "x", "B\\1.jpg": "x"})
        main.scan_results[self.s.id] = self.s
        self.addCleanup(main.scan_results.pop, self.s.id, None)

    def test_insights_and_folder_endpoints(self):
        r = self.main.get_insights(self.s.id)
        self.assertEqual(r["status"], "ok")
        fid = r["folders"][0]["id"]
        self.assertEqual(self.main.get_folder(self.s.id, fid)["path"], r["folders"][0]["path"])
        self.assertEqual(self.main.get_folder(self.s.id, "000000000000").status_code, 404)
        self.assertEqual(self.main.get_insights("nope").status_code, 404)

    def test_running_scan_gets_409(self):
        self.s.status = "in_progress"
        self.assertEqual(self.main.get_insights(self.s.id).status_code, 409)
        self.assertEqual(self.main.get_folder(self.s.id, "x").status_code, 409)

    def test_progress_carries_coverage(self):
        self.s.coverage = {"heic": 3, "online_only": 2, "photos_checked": 2}
        c = asyncio.run(self.main.get_progress(self.s.id))["coverage"]
        self.assertEqual((c["heic_not_checked"], c["online_only"], c["photos_checked"], c["unreadable"]), (3, 2, 2, 0))


if __name__ == "__main__":
    unittest.main()
