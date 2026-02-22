"""Sync CSV notes into Anki via AnkiConnect (add/update/delete)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from anki_connect import invoke


MANAGED_TAG = "managed::italiano_repo"
MANUAL_TAG_PREFIX = "my::"
NOTE_ID_FIELD = "NoteID"


@dataclass(frozen=True)
class CsvNote:
    """A single note row from a CSV file."""

    note_id: str
    deck: str
    model: str
    fields: Dict[str, str]
    tags: List[str]


def _read_csv_notes(csv_path: Path) -> List[CsvNote]:
    """Read a CSV file into a list of CsvNote objects."""
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        notes: List[CsvNote] = []
        for row in reader:
            note_id = (row.get("NoteID") or "").strip()
            deck = (row.get("Deck") or "Italiano").strip()
            model = (row.get("NoteType") or "Italiano::Cloze").strip()
            tags = (row.get("Tags") or "").split()

            # fields for the Anki model: everything except meta columns
            fields: Dict[str, str] = {
                "NoteID": note_id,
                "SentenceCloze": (row.get("SentenceCloze") or "").strip(),
                "Answer": (row.get("Answer") or "").strip(),
                "FullSentenceIT": (row.get("FullSentenceIT") or "").strip(),
                "TranslationEN": (row.get("TranslationEN") or "").strip(),
                "Extra": (row.get("Extra") or "").strip(),
                "SourceFile": (row.get("SourceFile") or "").strip(),
                "Level": (row.get("Level") or "").strip(),
                "Difficulty": (row.get("Difficulty") or "").strip(),
                "UpdatedAt": (row.get("UpdatedAt") or "").strip(),
            }

            notes.append(CsvNote(note_id=note_id, deck=deck, model=model, fields=fields, tags=tags))
        return notes


def _ensure_models() -> None:
    """Ensure the required models exist (minimal templates)."""
    model_names = set(invoke("modelNames"))
    if "Italiano::Cloze" not in model_names:
        invoke(
            "createModel",
            {
                "modelName": "Italiano::Cloze",
                "inOrderFields": [
                    "NoteID",
                    "SentenceCloze",
                    "Answer",
                    "FullSentenceIT",
                    "TranslationEN",
                    "Extra",
                    "SourceFile",
                    "Level",
                    "Difficulty",
                    "UpdatedAt",
                ],
                "css": ".card { font-family: arial; font-size: 20px; text-align: left; }",
                "isCloze": False,
                "cardTemplates": [
                    {
                        "Name": "Card 1",
                        "Front": "{{SentenceCloze}}",
                        "Back": "{{FrontSide}}<hr id=answer>{{Answer}}<br><br>{{FullSentenceIT}}<br>{{TranslationEN}}<br><br>{{Extra}}",
                    }
                ],
            },
        )


def _get_managed_notes() -> Dict[str, int]:
    """Return mapping NoteID -> Anki note id for managed notes."""
    note_ids = invoke("findNotes", {"query": f"tag:{MANAGED_TAG}"})
    if not note_ids:
        return {}

    info = invoke("notesInfo", {"notes": note_ids})
    mapping: Dict[str, int] = {}
    for n in info:
        fields = n.get("fields") or {}
        noteid_field = fields.get(NOTE_ID_FIELD, {}).get("value", "")
        noteid_field = (noteid_field or "").strip()
        if noteid_field:
            mapping[noteid_field] = int(n["noteId"])
    return mapping


def _split_tags(tags: List[str]) -> Tuple[List[str], List[str]]:
    """Split tags into (manual, managed_or_other)."""
    manual = [t for t in tags if t.startswith(MANUAL_TAG_PREFIX)]
    non_manual = [t for t in tags if not t.startswith(MANUAL_TAG_PREFIX)]
    return manual, non_manual


def sync_repo(root: Path) -> None:
    """Sync all CSV notes under notes/ into Anki."""
    _ensure_models()

    csv_notes: List[CsvNote] = []
    for csv_path in (root / "notes").rglob("*.csv"):
        csv_notes.extend(_read_csv_notes(csv_path))

    # Build desired NoteID set
    desired_by_id: Dict[str, CsvNote] = {n.note_id: n for n in csv_notes if n.note_id}

    existing = _get_managed_notes()

    to_add = [n for n in csv_notes if n.note_id and n.note_id not in existing]
    to_update = [n for n in csv_notes if n.note_id and n.note_id in existing]
    to_delete_note_ids = [anki_id for noteid, anki_id in existing.items() if noteid not in desired_by_id]

    # Add new notes
    if to_add:
        payload_notes = []
        for n in to_add:
            manual, non_manual = _split_tags(n.tags)
            tags = list(dict.fromkeys([MANAGED_TAG] + non_manual + manual))
            payload_notes.append({"deckName": n.deck, "modelName": n.model, "fields": n.fields, "tags": tags})
        invoke("addNotes", {"notes": payload_notes})
        print(f"Added: {len(to_add)}")

    # Update existing notes (fields + managed tags; keep manual tags)
    if to_update:
        # Fetch current tags so we can preserve manual tags even if CSV doesn't include them
        anki_ids = [existing[n.note_id] for n in to_update]
        infos = invoke("notesInfo", {"notes": anki_ids})
        current_tags_by_anki_id: Dict[int, List[str]] = {int(i["noteId"]): list(i.get("tags") or []) for i in infos}

        for n in to_update:
            anki_id = existing[n.note_id]
            invoke("updateNoteFields", {"note": {"id": anki_id, "fields": n.fields}})

            current_tags = current_tags_by_anki_id.get(anki_id, [])
            current_manual, _ = _split_tags(current_tags)

            csv_manual, csv_non_manual = _split_tags(n.tags)
            # preserve current manual tags + any manual tags in CSV
            merged_manual = list(dict.fromkeys(current_manual + csv_manual))
            merged_non_manual = list(dict.fromkeys([MANAGED_TAG] + csv_non_manual))

            target_tags = list(dict.fromkeys(merged_non_manual + merged_manual))

            # Set tags (replace entirely) to avoid drift
            #invoke("setNoteTags", {"notes": [anki_id], "tags": " ".join(target_tags)})
            # Compute tag delta and apply via AnkiConnect (no set/replace action exists).
            current = set(current_tags)
            target = set(target_tags)

            to_remove = sorted(t for t in (current - target) if not t.startswith(MANUAL_TAG_PREFIX))
            to_add = sorted(target - current)

            if to_remove:
                invoke("removeTags", {"notes": [anki_id], "tags": " ".join(to_remove)})
            if to_add:
                invoke("addTags", {"notes": [anki_id], "tags": " ".join(to_add)})

        print(f"Updated: {len(to_update)}")

    # Delete removed notes
    if to_delete_note_ids:
        invoke("deleteNotes", {"notes": to_delete_note_ids})
        print(f"Deleted: {len(to_delete_note_ids)}")


def main() -> None:
    """Entry point."""
    root = Path(__file__).resolve().parents[1]
    sync_repo(root)


if __name__ == "__main__":
    main()
