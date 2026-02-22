#!/bin/bash
set -e
python3 scripts/fill_missing_columns.py
python3 scripts/sync_notes.py
python3 scripts/build_filtered_decks.py

