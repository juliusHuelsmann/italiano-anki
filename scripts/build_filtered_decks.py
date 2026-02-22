"""Build practice description notes via AnkiConnect and export filtered-deck specs for the add-on.

Why:
- AnkiConnect does NOT provide an API action to create filtered decks.
- Filtered decks are therefore created by the included Anki add-on, which reads the exported specs.

This script:
1) Ensures the practice-description note model exists.
2) Upserts one "PracticeDescription" note per practice into `Italiano::Practice::Info`.
3) Exports `build/filtered_decks.json` for the add-on to consume.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from anki_connect import invoke


PRACTICE_INFO_DECK = "Italiano::Practice::Info"
PRACTICE_MODEL = "Italiano::PracticeDescription"

def _ensure_deck(deck_name:str) -> None:
    invoke('createDeck', {'deck': deck_name})


@dataclass(frozen=True)
class Practice:
    """A single practice definition."""

    name: str
    deck: str
    search: str
    limit: int
    order: str
    reschedule: bool
    description: str


def _slug(s: str) -> str:
    """Create a stable slug."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _ensure_practice_model() -> None:
    """Ensure practice model exists."""
    models = set(invoke("modelNames"))
    if PRACTICE_MODEL in models:
        return

    invoke(
        "createModel",
        {
            "modelName": PRACTICE_MODEL,
            "inOrderFields": ["NoteID", "Name", "Search", "Description"],
            "css": ".card { font-family: arial; font-size: 18px; text-align: left; }",
            "isCloze": False,
            "cardTemplates": [
                {
                    "Name": "Info",
                    "Front": "{{Name}}",
                    "Back": "<b>Search</b><br><pre>{{Search}}</pre><hr><b>Description</b><br>{{Description}}",
                }
            ],
        },
    )


def _load_practices(root: Path) -> List[Practice]:
    """Load all practice JSON files."""
    practices: List[Practice] = []
    for p in sorted((root / "practices").glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        practices.append(
            Practice(
                name=str(data["name"]),
                deck=str(data["deck"]),
                search=str(data["search"]),
                limit=int(data.get("limit", 30)),
                order=str(data.get("order", "random")),
                reschedule=bool(data.get("reschedule", True)),
                description=str(data.get("description", "")).strip(),
            )
        )
    return practices


def _upsert_practice_info_note(p: Practice) -> None:
    """Create or update a practice description note in PRACTICE_INFO_DECK."""
    _ensure_deck(PRACTICE_INFO_DECK)
    note_id = f"practice:{_slug(p.name)}"
    query = f'deck:"{PRACTICE_INFO_DECK}" "{note_id}"'
    existing = invoke("findNotes", {"query": query})

    fields = {
        "NoteID": note_id,
        "Name": p.name,
        "Search": p.search,
        "Description": p.description,
    }

    if existing:
        invoke("updateNoteFields", {"note": {"id": int(existing[0]), "fields": fields}})
        return

    invoke(
        "addNote",
        {
            "note": {
                "deckName": PRACTICE_INFO_DECK,
                "modelName": PRACTICE_MODEL,
                "fields": fields,
                "tags": ["managed::italiano_repo", "practice::info"],
            }
        },
    )


def export_filtered_deck_specs(root: Path, practices: List[Practice]) -> Path:
    """Export the filtered deck specs for the add-on to build."""
    out_dir = root / "build"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "filtered_decks.json"

    specs = [
        {
            "name": p.name,
            "deck": p.deck,
            "search": p.search,
            "limit": p.limit,
            "order": p.order,
            "reschedule": p.reschedule,
            "description": p.description,
        }
        for p in practices
    ]
    out_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def build_all(root: Path) -> None:
    """Build all practices (info notes + export specs)."""
    _ensure_practice_model()
    practices = _load_practices(root)

    for p in practices:
        _upsert_practice_info_note(p)
        print(f"Upserted practice info note: {p.name}")

    out_path = export_filtered_deck_specs(root, practices)
    print(f"Exported filtered deck specs for add-on: {out_path}")


def main() -> None:
    """Entry point."""
    root = Path(__file__).resolve().parents[1]
    build_all(root)


if __name__ == "__main__":
    main()

