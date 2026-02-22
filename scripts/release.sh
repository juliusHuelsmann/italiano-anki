#!/usr/bin/env bash
set -euo pipefail

# Requires: Anki is running with AnkiConnect enabled.
python3 scripts/uuid_fill.py
python3 scripts/sync_notes.py
python3 scripts/build_filtered_decks.py

echo "Done. If Anki auto-sync-on-close is enabled, close Anki to sync."
