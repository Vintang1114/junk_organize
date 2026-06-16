#!/usr/bin/env python3
"""
organize_junk.py — Duplicate File Organizer
Finds duplicate files (by name and/or content) in a folder and moves them to a trash folder.
"""
"""
To Test:
python organize_junk.py /path/to/your/folder --dry-run

To move duplicates to trash sub folder:
python organize_junk.py /path/to/your/folder

Choosing a custom trash folder:
python organize_junk.py /path/to/your/folder --trash /path/to/trash

Change direction:
python organize_junk.py /path/to/your/folder --mode content
"""


import os
import hashlib
import shutil
import argparse
from collections import defaultdict
from pathlib import Path


def hash_file(path: Path, chunk_size: int = 65536) -> str:
    """Return the MD5 hash of a file's contents."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(folder: Path, mode: str) -> list[tuple[Path, Path]]:
    """
    Scan folder recursively and return a list of (duplicate, original) pairs.

    mode:
      'content' — same file hash
      'name'    — same filename (case-insensitive)
      'both'    — same hash AND same filename
    """
    # Gather all files
    all_files: list[Path] = [p for p in folder.rglob("*") if p.is_file()]

    seen_hashes: dict[str, Path] = {}
    seen_names: dict[str, Path] = {}
    duplicates: list[tuple[Path, Path]] = []

    for file in all_files:
        file_hash = hash_file(file) if mode in ("content", "both") else None
        file_name = file.name.lower() if mode in ("name", "both") else None

        if mode == "content":
            key = file_hash
            seen = seen_hashes
        elif mode == "name":
            key = file_name
            seen = seen_names
        else:  # both
            key = (file_hash, file_name)
            seen = seen_hashes  # reuse one dict with tuple keys

        if key in seen:
            duplicates.append((file, seen[key]))
        else:
            seen[key] = file

    return duplicates


def move_duplicates(
    duplicates: list[tuple[Path, Path]],
    trash_folder: Path,
    dry_run: bool = False,
) -> list[dict]:
    """Move duplicate files to the trash folder. Returns a log of actions."""
    trash_folder.mkdir(parents=True, exist_ok=True)
    log = []

    for dup, original in duplicates:
        # Build destination path, avoiding collisions
        dest = trash_folder / dup.name
        counter = 1
        while dest.exists():
            dest = trash_folder / f"{dup.stem}_{counter}{dup.suffix}"
            counter += 1

        entry = {
            "duplicate": str(dup),
            "original": str(original),
            "moved_to": str(dest),
            "dry_run": dry_run,
        }
        log.append(entry)

        if not dry_run:
            shutil.move(str(dup), dest)

    return log


def print_report(log: list[dict], dry_run: bool) -> None:
    label = "[DRY RUN] " if dry_run else ""
    if not log:
        print("✅ No duplicates found.")
        return

    print(f"\n{'='*60}")
    print(f"  {label}Duplicate File Report — {len(log)} duplicate(s) found")
    print(f"{'='*60}")
    for i, entry in enumerate(log, 1):
        action = "Would move" if dry_run else "Moved"
        print(f"\n#{i}")
        print(f"  Duplicate : {entry['duplicate']}")
        print(f"  Original  : {entry['original']}")
        print(f"  {action} → {entry['moved_to']}")
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Find and move duplicate files to a trash folder."
    )
    parser.add_argument(
        "folder",
        type=str,
        help="Path to the folder to scan for duplicates.",
    )
    parser.add_argument(
        "--trash",
        type=str,
        default=None,
        help="Path to the trash folder (default: <folder>/_duplicates_trash).",
    )
    parser.add_argument(
        "--mode",
        choices=["content", "name", "both"],
        default="both",
        help="How to detect duplicates: by file content, name, or both (default: both).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without moving any files.",
    )

    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"❌ Error: '{folder}' is not a valid directory.")
        return

    trash_folder = Path(args.trash).resolve() if args.trash else folder / "_duplicates_trash"

    print(f"\n🔍 Scanning: {folder}")
    print(f"🗑️  Trash folder: {trash_folder}")
    print(f"🔎 Detection mode: {args.mode}")
    if args.dry_run:
        print("⚠️  DRY RUN — no files will be moved.\n")

    duplicates = find_duplicates(folder, args.mode)
    log = move_duplicates(duplicates, trash_folder, dry_run=args.dry_run)
    print_report(log, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
