#!/bin/bash
set -e
python3 scripts/fill_missing_columns.py
python3 scripts/sync_notes.py
python3 scripts/build_filtered_decks.py

target=~/"snap/anki-desktop/63/.local/share/anki_italiano_practice_builder/"
mkdir -p "$target"
cp build/filtered_decks.json $target

