"""JSON message types for GridNotes LAN broadcast."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

BROADCAST_WS_PORT = 8765
BROADCAST_DISCOVERY_PORT = 8766
DISCOVERY_MAGIC = "gridnotes-broadcast-v1"
PROTOCOL_VERSION = 1


@dataclass
class SnapshotPayload:
    drivers: list[dict[str, Any]]
    race_results: list[dict[str, Any]]
    broadcaster_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "version": PROTOCOL_VERSION,
            "broadcaster_name": self.broadcaster_name,
            "drivers": self.drivers,
            "race_results": self.race_results,
        }


@dataclass
class LiveStatePayload:
    connected: bool = False
    subsession_id: int = 0
    session_kind: str = ""
    session_context: dict[str, str] = field(default_factory=dict)
    drivers: list[dict[str, Any]] = field(default_factory=list)
    grid_slots: list[dict[str, Any]] = field(default_factory=list)
    player_cust_id: int | None = None
    spotter_cust_id: int | None = None
    spotter_gap: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "live",
            "version": PROTOCOL_VERSION,
            "connected": self.connected,
            "subsession_id": self.subsession_id,
            "session_kind": self.session_kind,
            "session_context": self.session_context,
            "drivers": self.drivers,
            "grid_slots": self.grid_slots,
            "player_cust_id": self.player_cust_id,
            "spotter_cust_id": self.spotter_cust_id,
            "spotter_gap": self.spotter_gap,
        }


def encode_message(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), default=str)


def driver_patch_message(
    cust_id: int,
    *,
    notes: str | None = None,
    race_preference: int | None | object = ...,
) -> dict[str, Any]:
    """Build a driver_patch payload. Omit a field to leave it unchanged on the broadcaster."""
    payload: dict[str, Any] = {
        "type": "driver_patch",
        "version": PROTOCOL_VERSION,
        "cust_id": int(cust_id),
    }
    if notes is not None:
        payload["notes"] = notes
    if race_preference is not ...:
        payload["race_preference"] = race_preference
    return payload


def decode_message(raw: str | bytes) -> dict[str, Any] | None:
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data
