"""
Scan insights: where the duplicates are. Read-only, computed on demand from a scan session, so the
answer is always up to date after a delete. The backend sends ids and numbers; the wording lives in
the frontend.

Definitions (also in docs/PROJECT_HISTORY.md):
- folder: the directory directly containing a photo; matched case-insensitively (normcase + normpath).
- photos with a duplicate: members of a duplicate group in that folder, whichever copy is kept.
- extra copies: members that are not the kept photo (what deleting would remove).
- inside share: the fraction of a folder's memberships in groups whose members are ALL in that folder.
  tag "same_folder" at >= 0.70, "other_folders" at <= 0.30, otherwise "mixed".
- pairs: a group whose members span folders S adds +1 to every unordered pair of distinct folders in S
  (once per group, however many copies). A group spanning 3+ folders therefore counts in several pairs,
  and is also counted once in groups_across_3_plus_folders; pair counts are never summed.
"""
import hashlib
import os
import re
from typing import Optional

from models.scan import ScanSession

TOP_FOLDERS = 10
TOP_PAIRS = 5
SAME_FOLDER_AT_LEAST = 0.70
OTHER_FOLDERS_AT_MOST = 0.30
MAX_TIPS = 4

# Tip triggers: a tip is shown only when its numbers clear these bars
NAME_TIP_MIN_COUNT = 5          # " - Copy" / "(1)" names among the extra copies ...
NAME_TIP_MIN_SHARE = 0.20       # ... and at least this share of all extra copies
PAIR_TIP_MIN_GROUPS = 10        # a folder pair sharing at least this many groups ...
PAIR_TIP_MIN_SHARE = 0.25       # ... and at least this share of the smaller folder's photos
SAME_FOLDER_TIP_MIN_PHOTOS = 10  # a "same folder" folder with at least this many photos with a duplicate
SPREAD_TIP_MIN_GROUPS = 5       # groups spanning three or more folders

# "photo - Copy", "photo - Copy (2)", "Copy of photo", "Copy (2) of photo": what Windows Explorer names a paste
_COPY_NAME = re.compile(r"( - Copy( \(\d+\))?$)|(^Copy (\(\d+\) )?of )", re.IGNORECASE)
# "photo (1)": what browsers and many apps name a second download or save of the same file
_NUMBER_NAME = re.compile(r"\s\(\d{1,3}\)$")


def folder_key(file_path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.dirname(file_path)))


def folder_id(key: str) -> str:
    """Short, stable id for a folder (same before and after deletes); the only thing the UI sends back."""
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def root_name(root: str) -> str:
    """Display name of the scanned folder; for a drive root such as D:\\ the drive ("D:")."""
    norm = os.path.normpath(root) if root else ""
    return os.path.basename(norm) or os.path.splitdrive(norm)[0] or norm


def relative_path(path: str, root: str) -> str:
    """Path relative to the scanned folder; "" for the scanned folder itself."""
    if not root:
        return path
    try:
        rel = os.path.relpath(path, root)
    except ValueError:  # another drive
        return path
    if rel == ".":
        return ""
    if rel.startswith(".."):
        return path
    return rel


def tag_for(inside_share: float) -> str:
    if inside_share >= SAME_FOLDER_AT_LEAST:
        return "same_folder"
    if inside_share <= OTHER_FOLDERS_AT_MOST:
        return "other_folders"
    return "mixed"


def coverage_summary(session: ScanSession) -> dict:
    c = session.coverage or {}
    return {
        "photos_checked": c.get("photos_checked", 0),
        "folders_checked": c.get("folders_checked", 0),
        "heic_not_checked": c.get("heic", 0),
        "raw_not_checked": c.get("raw", 0),
        "under_10kb": c.get("under_10kb", 0),
        "online_only": c.get("online_only", 0),
        "unreadable": len(session.skipped_files),
    }


def find_folder(session: ScanSession, wanted_id: str) -> Optional[str]:
    """The absolute path of a folder that holds photos in this scan, or None. Used by Open folder."""
    for photo in session.photos:
        if folder_id(folder_key(photo.file_path)) == wanted_id:
            return os.path.dirname(photo.file_path)
    return None


def build_insights(session: ScanSession) -> dict:
    # One snapshot: a delete replaces these lists rather than editing them, so they stay consistent
    photos = session.photos
    groups = session.duplicate_groups
    root = session.folder_path
    by_id = {p.id: p for p in photos}

    folders: dict[str, dict] = {}
    for p in sorted(photos, key=lambda p: p.file_path.lower()):  # sorted: the displayed casing is deterministic
        key = folder_key(p.file_path)
        f = folders.get(key)
        if f is None:
            f = folders[key] = {"path": os.path.dirname(p.file_path), "photos": 0, "members": 0,
                                "internal": 0, "extra": 0, "extra_bytes": 0}
        f["photos"] += 1

    pairs: dict[tuple, int] = {}
    in_one = across = three_plus = 0
    extra_copies = extra_bytes = copy_names = number_names = 0
    group_count = 0
    for g in groups:
        members = [by_id[i] for i in g.photo_ids if i in by_id]
        if len(members) < 2:
            continue
        group_count += 1
        keys = [folder_key(m.file_path) for m in members]
        distinct = sorted(set(keys))
        internal = len(distinct) == 1
        if internal:
            in_one += 1
        else:
            across += 1
        if len(distinct) >= 3:
            three_plus += 1
        for m, key in zip(members, keys):
            f = folders[key]
            f["members"] += 1
            if internal:
                f["internal"] += 1
            if m.id != g.kept_photo_id:
                f["extra"] += 1
                f["extra_bytes"] += m.file_size_bytes
                extra_copies += 1
                extra_bytes += m.file_size_bytes
                stem = os.path.splitext(os.path.basename(m.file_path))[0]
                if _COPY_NAME.search(stem):
                    copy_names += 1
                elif _NUMBER_NAME.search(stem):
                    number_names += 1
        for i in range(len(distinct)):
            for j in range(i + 1, len(distinct)):
                pairs[(distinct[i], distinct[j])] = pairs.get((distinct[i], distinct[j]), 0) + 1

    def folder_out(key: str) -> dict:
        f = folders[key]
        inside = f["internal"] / f["members"] if f["members"] else 0.0
        return {
            "id": folder_id(key),
            "path": f["path"],
            "relative_path": relative_path(f["path"], root),
            "photos": f["photos"],
            "photos_with_duplicate": f["members"],
            "share_with_duplicate": round(f["members"] / f["photos"], 3) if f["photos"] else 0.0,
            "extra_copies": f["extra"],
            "extra_bytes": f["extra_bytes"],
            "inside_share": round(inside, 3),
            "tag": tag_for(inside),
        }

    with_dups = [k for k, f in folders.items() if f["members"]]
    with_dups.sort(key=lambda k: (-folders[k]["members"], -folders[k]["extra"], folders[k]["path"].lower()))
    top = [folder_out(k) for k in with_dups[:TOP_FOLDERS]]

    def ref(key: str) -> dict:
        return {"id": folder_id(key), "relative_path": relative_path(folders[key]["path"], root)}

    ranked_pairs = []
    for (a, b), count in pairs.items():
        ra, rb = ref(a), ref(b)
        if (ra["relative_path"].lower(), a) > (rb["relative_path"].lower(), b):
            a, b, ra, rb = b, a, rb, ra
        ranked_pairs.append((count, a, b, ra, rb))
    ranked_pairs.sort(key=lambda t: (-t[0], t[3]["relative_path"].lower(), t[4]["relative_path"].lower()))
    top_pairs = [{"a": ra, "b": rb, "shared_groups": count} for count, _, _, ra, rb in ranked_pairs[:TOP_PAIRS]]

    tips = []
    if extra_copies:
        if copy_names >= NAME_TIP_MIN_COUNT and copy_names >= NAME_TIP_MIN_SHARE * extra_copies:
            tips.append({"id": "copy_suffix", "count": copy_names})
        if number_names >= NAME_TIP_MIN_COUNT and number_names >= NAME_TIP_MIN_SHARE * extra_copies:
            tips.append({"id": "number_suffix", "count": number_names})
    if ranked_pairs:
        count, a, b, ra, rb = ranked_pairs[0]
        smaller = min(folders[a]["photos"], folders[b]["photos"])
        if count >= PAIR_TIP_MIN_GROUPS and count >= PAIR_TIP_MIN_SHARE * smaller:
            tips.append({"id": "folder_pair", "a": ra, "b": rb, "shared_groups": count})
    same = [k for k in with_dups
            if folders[k]["members"] >= SAME_FOLDER_TIP_MIN_PHOTOS
            and tag_for(folders[k]["internal"] / folders[k]["members"]) == "same_folder"]
    if same:
        k = same[0]  # with_dups is already ranked
        tips.append({"id": "same_folder", "folder": ref(k), "photos_with_duplicate": folders[k]["members"]})
    if three_plus >= SPREAD_TIP_MIN_GROUPS:
        tips.append({"id": "spread", "count": three_plus})

    headlines = []
    if top:
        f0 = top[0]
        headlines.append({"id": "top_folder", "folder": {"id": f0["id"], "relative_path": f0["relative_path"]},
                          "photos": f0["photos"], "photos_with_duplicate": f0["photos_with_duplicate"],
                          "tag": f0["tag"]})
        headlines.append({"id": "split", "groups_in_one_folder": in_one, "groups_across_folders": across})

    return {
        "status": "ok",
        "scan_id": session.id,
        "root": root,
        "root_name": root_name(root),
        "headlines": headlines,
        "totals": {
            "photos": len(photos),
            "folders": len(folders),
            "folders_with_duplicates": len(with_dups),
            "duplicate_groups": group_count,
            "groups_in_one_folder": in_one,
            "groups_across_folders": across,
            "groups_across_3_plus_folders": three_plus,
            "extra_copies": extra_copies,
            "extra_bytes": extra_bytes,
        },
        "folders": top,
        "folders_with_duplicates_not_shown": max(0, len(with_dups) - TOP_FOLDERS),
        "pairs": top_pairs,
        "tips": tips[:MAX_TIPS],
        "coverage": coverage_summary(session),
    }
