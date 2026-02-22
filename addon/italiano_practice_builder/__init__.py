"""Anki add-on: build filtered decks from filtered_decks.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from aqt import mw
from aqt.qt import QAction, QMessageBox


ADDON_NAME = "Italiano Practice Builder"
PRACTICE_PREFIX = "Italiano::Practice::"


def _addon_config() -> Dict[str, Any]:
    return mw.addonManager.getConfig(__name__) or {}


def _ensure_repo_path() -> Path:
    root_str = str(_addon_config().get("root", "")).strip()
    if not root_str:
        raise RuntimeError("Configure add-on: set 'root' to your repo path.")
    root = Path(root_str).expanduser()
    if not root.exists():
        raise RuntimeError(f"Repo root does not exist: {root}")
    return root


def _load_specs(root: Path) -> List[Dict[str, Any]]:
    spec_path = root / "filtered_decks.json"
    if not spec_path.exists():
        raise RuntimeError(f"Spec file not found: {spec_path}")
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("filtered_decks.json must contain a list")
    return data


def _parse_limit(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 50


def _parse_order(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.lower().strip()
        if v == "random":
            return 0
        if v == "due":
            return 1
    return 0


def _create_or_update_filtered_deck(spec: Dict[str, Any]) -> None:
    deck_name = str(spec["deck"])
    search = str(spec["search"])
    limit = _parse_limit(spec.get("limit", 50))
    order = _parse_order(spec.get("order", 0))
    reschedule = bool(spec.get("reschedule", False))

    did = mw.col.decks.id(deck_name)
    conf = mw.col.decks.get(did)

    conf["dyn"] = 1
    conf["terms"] = [[search, limit, order]]
    conf["resched"] = reschedule

    mw.col.decks.save(conf)

    # IMPORTANT: force rebuild synchronously
    try:
        mw.col.sched.rebuild_filtered_deck(did)
    except AttributeError:
        try:
            mw.col.sched.rebuildFilteredDeck(did)
        except Exception:
            pass


def _existing_practice_decks() -> Set[str]:
    decks = mw.col.decks
    if hasattr(decks, "all_names_and_ids"):
        return {
            d.name
            for d in decks.all_names_and_ids()
            if d.name.startswith(PRACTICE_PREFIX)
        }
    if hasattr(decks, "all_names"):
        return {
            n for n in decks.all_names() if n.startswith(PRACTICE_PREFIX)
        }
    return set()


def _delete_obsolete(desired: Set[str]) -> None:
    existing = _existing_practice_decks()
    obsolete = existing - desired
    for name in obsolete:
        did = mw.col.decks.id(name)
        if hasattr(mw.col.decks, "remove"):
            mw.col.decks.remove([did])
        else:
            mw.col.decks.rem(did)


def build_all_filtered_decks() -> None:
    root = _ensure_repo_path()
    specs = _load_specs(root)
    desired = {s["deck"] for s in specs}

    errors: List[str] = []

    for spec in specs:
        try:
            _create_or_update_filtered_deck(spec)
        except Exception as e:
            errors.append(f"{spec.get('deck')}: {e}")

    try:
        _delete_obsolete(desired)
    except Exception as e:
        errors.append(f"delete obsolete: {e}")

    if hasattr(mw, "reset"):
        mw.reset()

    if errors:
        QMessageBox.warning(mw, ADDON_NAME, "\n".join(errors))
    else:
        QMessageBox.information(mw, ADDON_NAME, "Filtered decks rebuilt.")


def _setup_menu() -> None:
    action = QAction(ADDON_NAME, mw)
    action.triggered.connect(build_all_filtered_decks)
    mw.form.menuTools.addAction(action)


_setup_menu()
