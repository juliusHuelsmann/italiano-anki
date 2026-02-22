"""Ensure required columns exist and fill defaults for every row in notes/*.csv."""

from __future__ import annotations

import csv
import datetime as _dt
import uuid
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_DECK = "Italiano"
DEFAULT_NOTE_TYPE = "Italiano::Cloze"
MANAGED_TAG = "managed::italiano_repo"


def _is_empty(value: str) -> bool:
    """Return True if a CSV cell should be treated as empty."""
    return value.strip() == ""


def _difficulty_from_level(level: str) -> str:
    """Return a default difficulty number for a CEFR level string."""
    mapping = {
        "A1": "1",
        "A2": "2",
        "B1": "3",
        "B2": "4",
        "C1": "5",
        "C2": "6",
    }
    return mapping.get(level.strip().upper(), "")


def _ensure_columns(header: List[str], required: List[str]) -> Tuple[List[str], Dict[str, int], bool]:
    """Ensure required columns exist, appending missing ones to the end."""
    changed = False
    existing = set(header)
    for col in required:
        if col not in existing:
            header.append(col)
            existing.add(col)
            changed = True
    index = {name: i for i, name in enumerate(header)}
    return header, index, changed


def _row_pad(row: List[str], width: int) -> None:
    """Pad a row in-place to the given width."""
    if len(row) < width:
        row.extend([""] * (width - len(row)))


def _derive_sourcefile(csv_path: Path, notes_dir: Path, row: List[str], idx: Dict[str, int]) -> str:
    """Derive SourceFile from row or from filesystem path."""
    if "SourceFile" in idx:
        v = row[idx["SourceFile"]]
        if not _is_empty(v):
            return v.strip()

    # Fallback: relative path under notes/ (posix style)
    rel = csv_path.relative_to(notes_dir).as_posix()
    # Mirror earlier convention: top folder + filename
    return rel


def _managed_tags_for(sourcefile: str, level: str) -> List[str]:
    """Compute machine-managed tags for a row."""
    sourcefile = sourcefile.strip()
    level = level.strip()

    folder = ""
    stem = ""
    if sourcefile:
        p = Path(sourcefile)
        if len(p.parts) > 0:
            folder = p.parts[0]
        stem = p.stem

    tags = [MANAGED_TAG]
    if folder:
        tags.append(f"source::{folder}")
    if stem:
        tags.append(f"file::{stem}")
    if level:
        tags.append(f"level::{level.upper()}")
    return tags


def _merge_tags(existing: str, to_add: List[str]) -> str:
    """Merge tags, preserving existing order and appending missing."""
    current = [t for t in existing.split() if t]
    have = set(current)
    out = list(current)
    for t in to_add:
        if t not in have:
            out.append(t)
            have.add(t)
    return " ".join(out)


def fill_defaults(root: Path) -> List[Path]:
    """Fill missing NoteID and default values for all CSV files under root.

    What this does:
    - Ensures columns exist: NoteID, Deck, NoteType, Tags, UpdatedAt
    - Fills missing values:
      - NoteID: UUID if empty
      - Deck: DEFAULT_DECK if empty
      - NoteType: DEFAULT_NOTE_TYPE if empty
      - UpdatedAt: today's ISO date if empty
      - Difficulty: if empty and Level is present, fill via A1..C2 -> 1..6
      - Tags: appends managed tags (managed::italiano_repo, source::..., file::..., level::...)

    Args:
        root: Repository root folder.

    Returns:
        List of CSV paths that were modified.

    Raises:
        FileNotFoundError: If the notes directory does not exist.
    """
    notes_dir = root / "notes"
    if not notes_dir.exists():
        raise FileNotFoundError(f"notes directory not found: {notes_dir}")

    today = _dt.date.today().isoformat()

    modified: List[Path] = []
    for csv_path in notes_dir.rglob("*.csv"):
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            continue

        header = rows[0]
        required_cols = ["NoteID", "Deck", "NoteType", "Tags", "UpdatedAt"]
        # Optional but used for smarter defaults if present
        # (we do NOT force-create Level/Difficulty/SourceFile unless asked)
        header, idx, header_changed = _ensure_columns(header, required_cols)

        changed = header_changed

        for r in rows[1:]:
            _row_pad(r, len(header))

            # NoteID
            if _is_empty(r[idx["NoteID"]]):
                r[idx["NoteID"]] = str(uuid.uuid4())
                changed = True

            # Deck
            if _is_empty(r[idx["Deck"]]):
                r[idx["Deck"]] = DEFAULT_DECK
                changed = True

            # NoteType
            if _is_empty(r[idx["NoteType"]]):
                r[idx["NoteType"]] = DEFAULT_NOTE_TYPE
                changed = True

            # UpdatedAt
            if _is_empty(r[idx["UpdatedAt"]]):
                r[idx["UpdatedAt"]] = today
                changed = True

            # Difficulty (only if Difficulty column exists OR we can add it based on Level existing in header)
            # Your request: "Difficulty if Level exists"
            if "Level" in idx:
                if "Difficulty" not in idx:
                    # Add Difficulty column if missing (because Level exists)
                    header.append("Difficulty")
                    idx = {name: i for i, name in enumerate(header)}
                    # Pad all rows to new width
                    for rr in rows[1:]:
                        _row_pad(rr, len(header))
                    changed = True

                level = r[idx["Level"]].strip()
                if _is_empty(r[idx["Difficulty"]]) and not _is_empty(level):
                    d = _difficulty_from_level(level)
                    if d:
                        r[idx["Difficulty"]] = d
                        changed = True

            # Managed tags (only if we have enough info to derive them)
            level_val = r[idx["Level"]].strip() if "Level" in idx else ""
            sourcefile_val = _derive_sourcefile(csv_path, notes_dir, r, idx)
            managed = _managed_tags_for(sourcefile_val, level_val)

            existing_tags = r[idx["Tags"]]
            merged = _merge_tags(existing_tags, managed)
            if merged != existing_tags:
                r[idx["Tags"]] = merged
                changed = True

            # If we derived SourceFile from path and the column exists but is empty, fill it too (nice for maintainability)
            if "SourceFile" in idx and _is_empty(r[idx["SourceFile"]]):
                r[idx["SourceFile"]] = sourcefile_val
                changed = True

        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            modified.append(csv_path)

    return modified


def main() -> None:
    """Run default filling for the current repository."""
    root = Path(__file__).resolve().parents[1]
    modified = fill_defaults(root)
    if modified:
        print("Updated CSVs:")
        for p in modified:
            print(f"- {p}")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
