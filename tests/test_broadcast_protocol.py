"""Tests for gridnotes.broadcast.protocol."""

import json

from gridnotes.broadcast.protocol import (
    PROTOCOL_VERSION,
    LiveStatePayload,
    SnapshotPayload,
    decode_message,
    driver_patch_message,
    encode_message,
    hello_message,
)


def test_snapshot_round_trip():
    payload = SnapshotPayload(
        drivers=[{"cust_id": 1, "driver_name": "A"}],
        race_results=[{"cust_id": 1, "subsession_id": 99}],
        broadcaster_name="Host-PC",
    )
    raw = encode_message(payload.to_dict())
    data = decode_message(raw)
    assert data is not None
    assert data["type"] == "snapshot"
    assert data["version"] == PROTOCOL_VERSION
    assert data["broadcaster_name"] == "Host-PC"
    assert len(data["drivers"]) == 1


def test_live_state_payload():
    live = LiveStatePayload(connected=True, subsession_id=42, session_kind="race")
    d = live.to_dict()
    assert d["type"] == "live"
    assert d["connected"] is True


def test_driver_patch_message_partial():
    patch = driver_patch_message(100, notes="Watch sends")
    assert patch["cust_id"] == 100
    assert patch["notes"] == "Watch sends"
    assert "race_preference" not in patch

    patch_pref = driver_patch_message(100, race_preference=1)
    assert patch_pref["race_preference"] == 1


def test_hello_message_defaults():
    msg = hello_message("  ")
    assert msg["type"] == "hello"
    assert msg["receiver_name"] == "Receiver"

    msg2 = hello_message("Tablet")
    assert msg2["receiver_name"] == "Tablet"


def test_decode_message_invalid():
    assert decode_message("not json") is None
    assert decode_message(json.dumps([1, 2, 3])) is None
    assert decode_message(b'{"type":"ok"}') == {"type": "ok"}
