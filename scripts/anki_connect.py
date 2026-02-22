"""Small AnkiConnect client helper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import json
import urllib.request


@dataclass(frozen=True)
class AnkiConnectError(Exception):
    """Raised when AnkiConnect returns an error."""

    message: str

    def __str__(self) -> str:
        return self.message


def invoke(action: str, params: Optional[Dict[str, Any]] = None, *, version: int = 6) -> Any:
    """Invoke an AnkiConnect action and return the result.

    Args:
        action: AnkiConnect action name.
        params: Parameters for the action.
        version: AnkiConnect API version.

    Returns:
        The `result` field from AnkiConnect.

    Raises:
        AnkiConnectError: If AnkiConnect returns a non-null error.
        URLError: If AnkiConnect is unreachable.
        ValueError: If response is not valid JSON.
    """
    payload: Dict[str, Any] = {"action": action, "version": version}
    if params is not None:
        payload["params"] = params

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8765", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw)
    if parsed.get("error") is not None:
        raise AnkiConnectError(str(parsed["error"]))
    return parsed.get("result")
