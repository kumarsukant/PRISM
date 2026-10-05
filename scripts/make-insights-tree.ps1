# Builds a nested test tree with known duplicate counts, for the Insights tab and the smoke test.
# Read-only for Prism: it only scans it. Default root: C:\prism_insights (generated; never point this at real photos).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\make-insights-tree.ps1 [-Root <folder>]
#
# Layout (all PNGs are 128x128 noise, about 49 KB, so above the 10 KB minimum):
#   Pictures\Camera            IMG_001..IMG_020 (unique) + "IMG_001 - Copy".."IMG_006 - Copy" (same-folder copies)
#   Pictures\WhatsApp\Images   WA_IMG_0007..WA_IMG_0018 (copies of Camera 7..18) + WA_unique_1..3
#   Downloads                  dl1..dl6 + "dl1 (1)".."dl6 (1)" (same-folder copies)
#                              saved_IMG_016..018 (copies of Camera 16..18, so 3 groups span 3 folders)
#                              holiday.heic, photo.CR2 (fake, not scanned), icon.png (under 10 KB)
#   top.png                    one unique photo in the scanned folder itself
# The expected insights numbers are written to <Root>\_expected.json (ignored by the scan: not an image).
param(
    [string]$Root = 'C:\prism_insights',
    [string]$PythonExe = 'C:\projects\PRISM\backend\venv\Scripts\python.exe'
)
$Root = [System.IO.Path]::GetFullPath($Root)
if ([System.IO.Path]::GetPathRoot($Root) -eq $Root) { Write-Host "Refusing to use a drive root: $Root" -ForegroundColor Red; exit 1 }
$marker = Join-Path $Root '_expected.json'
if (Test-Path $Root) {
    if (-not (Test-Path $marker)) {
        Write-Host "Refusing: $Root exists and was not made by this script (no _expected.json)" -ForegroundColor Red
        exit 1
    }
    Remove-Item $Root -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Root | Out-Null

$py = @'
import json, os, shutil, sys
from PIL import Image
root = sys.argv[1]
def png(rel, size=128):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.frombytes("RGB", (size, size), os.urandom(size * size * 3)).save(path)
    return path
def copy(src, rel):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.copy(src, path)
def raw(rel, size):
    with open(os.path.join(root, rel), "wb") as f:
        f.write(b"\0" * size)
cam = {i: png(f"Pictures\\Camera\\IMG_{i:03d}.png") for i in range(1, 21)}
for i in range(1, 7):
    copy(cam[i], f"Pictures\\Camera\\IMG_{i:03d} - Copy.png")
for i in range(7, 19):
    copy(cam[i], f"Pictures\\WhatsApp\\Images\\WA_IMG_{i:04d}.png")
for i in range(1, 4):
    png(f"Pictures\\WhatsApp\\Images\\WA_unique_{i}.png")
for i in range(1, 7):
    copy(png(f"Downloads\\dl{i}.png"), f"Downloads\\dl{i} (1).png")
for i in range(16, 19):
    copy(cam[i], f"Downloads\\saved_IMG_{i:03d}.png")
raw("Downloads\\holiday.heic", 20000)
raw("Downloads\\photo.CR2", 20000)
png("Downloads\\icon.png", size=16)
png("top.png")
cam_rel, wa_rel, dl_rel = "Pictures\\Camera", "Pictures\\WhatsApp\\Images", "Downloads"
expected = {
    "photos": 57, "folders": 4, "folders_with_duplicates": 3, "duplicate_groups": 24,
    "groups_in_one_folder": 12, "groups_across_folders": 12, "groups_across_3_plus_folders": 3,
    "extra_copies": 27,
    "folders_ranked": [[cam_rel, 26, 24, "mixed"], [dl_rel, 15, 15, "same_folder"], [wa_rel, 15, 12, "other_folders"]],
    "pairs": [[cam_rel, wa_rel, 12], [dl_rel, cam_rel, 3], [dl_rel, wa_rel, 3]],
    "tips": ["copy_suffix", "number_suffix", "folder_pair", "same_folder"],
    "coverage": {"photos_checked": 57, "folders_checked": 4, "heic_not_checked": 1, "raw_not_checked": 1,
                 "under_10kb": 1, "online_only": 0, "unreadable": 0},
    "after_deleting_camera_copies": {"duplicate_groups": 18, "tips": ["number_suffix", "folder_pair", "same_folder"]},
}
with open(os.path.join(root, "_expected.json"), "w", encoding="utf-8") as f:
    json.dump(expected, f, indent=1)
print(f"Insights test tree ready: {root}")
'@
$py | & $PythonExe - $Root
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $marker)) { Write-Host 'Generating the tree failed' -ForegroundColor Red; exit 1 }
exit 0
