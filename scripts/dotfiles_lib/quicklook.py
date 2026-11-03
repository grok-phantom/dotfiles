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


def inspect(plugin):
    """Return (path, text, patched); never writes or invokes Herdr."""
    if not plugin or plugin.get("source", {}).get("resolved_commit") != REVISION:
        raise ValueError("Quicklook revision changed; review the punctuation patch before applying.")
    path = Path(plugin["plugin_root"]) / "scripts/lib.sh"
    original = path.read_text()
    patched = NEW in original
    baseline = original.replace(NEW, OLD, 1) if patched else original
    if hashlib.sha256(baseline.encode()).hexdigest() != ORIGINAL_SHA256 or baseline.count(OLD) != 1:
        raise ValueError("Quicklook lib.sh changed; refusing to overwrite local edits.")
    return path, original, patched


def apply(plugin):
    path, original, patched = inspect(plugin)
    if patched:
        return
    backup = Path.home() / ".local/state/dotfiles-backups/herdr-quicklook-cjk" / REVISION
    backup.mkdir(parents=True, exist_ok=True)
    backup_file = backup / "lib.sh"
    if not backup_file.exists():
        shutil.copy2(path, backup_file)
    path.write_text(original.replace(OLD, NEW, 1))
    if not inspect(plugin)[2]:
        raise ValueError("Quicklook patch readback failed")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Require patched bytes, without writing')
    args = parser.parse_args()
    plugins = json.loads(subprocess.check_output(
        ["herdr", "plugin", "list", "--json"], text=True))["result"]["plugins"]
    plugin = next((p for p in plugins if p["plugin_id"] == "herdr-quicklook"), None)
    if plugin is None:
        raise ValueError("Quicklook is not installed")
    if args.check:
        if not inspect(plugin)[2]:
            raise ValueError("Quicklook punctuation patch is missing")
    else:
        apply(plugin)
    print("Quicklook punctuation patch verified.")
