#!/usr/bin/env python3
"""Apply the reviewed CJK sentence-punctuation fix to the pinned Quicklook."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


REVISION = "b6567740aaceeabf8fd31c002c4936bfbf1523e6"
ORIGINAL_SHA256 = "f48d5980901a13e166845ee7f0f2186607bd7ec5a29091d2e9ca97f18b2be0f7"
OLD = """        prev = s
        while (length(s) > 0) {"""
NEW = """        prev = s
        # Strip CJK sentence punctuation before the ASCII wrapper pass.
        # Alternation matches complete UTF-8 sequences even with LC_ALL=C.
        sub(/(。|，|；|：|！|？|、)+$/, "", s)
        while (length(s) > 0) {"""


def main():
    plugins = json.loads(subprocess.check_output(
        ["herdr", "plugin", "list", "--json"], text=True))["result"]["plugins"]
    plugin = next(p for p in plugins if p["plugin_id"] == "herdr-quicklook")
    if plugin.get("source", {}).get("resolved_commit") != REVISION:
        sys.exit("Quicklook revision changed; review the punctuation patch before applying.")
    path = Path(plugin["plugin_root"]) / "scripts/lib.sh"
    original = path.read_text()
    if NEW in original:
        baseline = original.replace(NEW, OLD, 1)
        if hashlib.sha256(baseline.encode()).hexdigest() != ORIGINAL_SHA256:
            sys.exit("Patched Quicklook has other changes; inspect it manually.")
        print("Quicklook CJK punctuation fix already applied.")
        return
    if hashlib.sha256(original.encode()).hexdigest() != ORIGINAL_SHA256:
        sys.exit("Quicklook lib.sh changed; refusing to overwrite local edits.")
    assert original.count(OLD) == 1
    backup = Path.home() / ".local/state/dotfiles-backups/herdr-quicklook-cjk" / REVISION
    backup.mkdir(parents=True, exist_ok=True)
    backup_file = backup / "lib.sh"
    if not backup_file.exists():
        shutil.copy2(path, backup_file)
    path.write_text(original.replace(OLD, NEW, 1))
    print("Applied Quicklook CJK punctuation fix. Backup:", backup_file)


if __name__ == "__main__":
    main()
