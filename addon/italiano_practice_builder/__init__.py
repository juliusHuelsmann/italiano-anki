"""Anki add-on: build filtered decks from repo-exported practice specs.

This add-on reads `filtered_decks.json` exported by scripts/build_filtered_decks.py and
creates/updates filtered decks accordingly.

Config:
- repo_root: path to your anki-italiano repo (default: empty; must be set)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from aqt import mw
from aqt.qt import QAction, QMessageBox
from anki.errors import FilteredDeckError


ADDON_NAME = "Italiano Practice Builder"


def _read_config() -> Dict[str, Any]:
    """Read add-on config."""
    return mw.addonManager.getConfig(__name__) or {}


def _write_config(cfg: Dict[str, Any]) -> None:
    """Write add-on config."""
    mw.addonManager.writeConfig(__name__, cfg)


def _order_to_anki(order: str) -> int:
    """Map human order to Anki integer order."""
    # Matches Anki UI meanings; keep small set for maintainability.
    mapping = {
        "random": 0,
        "due": 1,
        "newest": 5,
        "oldest": 6,
    }
    return mapping.get(order, 0)


def _ensure_repo_path() -> Path:
    """Get repo root from config or raise."""
    cfg = _read_config()
    repo_root = str(cfg.get("repo_root", "")).strip()
    if not repo_root:
        raise RuntimeError("repo_root is not set in add-on config.")
    return Path(repo_root).expanduser().resolve()


def _load_specs(repo_root: Path) -> List[Dict[str, Any]]:
    """Load filtered deck specs from repo."""
    spec_path = repo_root / "build" / "filtered_decks.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path} (run scripts/build_filtered_decks.py first)")
    return json.loads(spec_path.read_text(encoding="utf-8"))


def _create_or_update_filtered_deck(spec: Dict[str, Any]) -> None:
    """Create/update a filtered deck."""
    name = str(spec["deck"])
    search = str(spec["search"])
    limit = int(spec.get("limit", 30))
    order = _order_to_anki(str(spec.get("order", "random")))
    reschedule = bool(spec.get("reschedule", True))

    # Create or reuse existing filtered deck
    did = mw.col.decks.id(name)

    try:
        # Ensure it's a filtered deck by setting a filtered config. If it already is, this updates it.
        conf = mw.col.decks.get(did)
        # new Anki versions store filtered deck config inside deck dict.
        conf["dyn"] = 1
        conf["terms"] = [[search, limit, order]]
        conf["resched"] = reschedule
        mw.col.decks.save(conf)
        mw.col.reset()
    except FilteredDeckError as e:
        raise RuntimeError(str(e)) from e


def build_all_filtered_decks() -> None:
    """Build all filtered decks from specs."""
    repo_root = _ensure_repo_path()
    specs = _load_specs(repo_root)

    errors: List[str] = []
    for spec in specs:
        try:
            _create_or_update_filtered_deck(spec)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{spec.get('deck')}: {e}")

    if errors:
        QMessageBox.warning(mw, ADDON_NAME, "Some decks failed:\n\n" + "\n".join(errors))
    else:
        QMessageBox.information(mw, ADDON_NAME, "Filtered decks updated.")


def _action_triggered() -> None:
    """Menu action handler."""
    try:
        build_all_filtered_decks()
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(mw, ADDON_NAME, str(e))


def setup_menu() -> None:
    """Add Tools menu entry."""
    action = QAction("Reload Italiano practices (filtered decks)", mw)
    action.triggered.connect(_action_triggered)
    mw.form.menuTools.addAction(action)


setup_menu()
