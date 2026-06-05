"""Integration tests for BroadcastServer and BroadcastClient over WebSocket."""

from __future__ import annotations

import socket

import pytest

pytest.importorskip("PyQt6.QtWebSockets")

from PyQt6.QtCore import QEventLoop, QTimer

from gridnotes.broadcast.client import BroadcastClient
from gridnotes.broadcast.protocol import LiveStatePayload, SnapshotPayload, driver_patch_message
from gridnotes.broadcast.server import BroadcastServer


def _wait_until(qapp, predicate, *, timeout_ms: int = 5000) -> bool:
    """Process Qt events until *predicate* is true or *timeout_ms* elapses."""
    if predicate():
        return True

    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)

    def poll() -> None:
        if predicate():
            loop.quit()
            return
        QTimer.singleShot(25, poll)

    timer.start(timeout_ms)
    poll()
    loop.exec()
    return predicate()


@pytest.fixture
def broadcast_server(qapp):
    server = BroadcastServer(broadcaster_name="Test Broadcaster", port=0)
    assert server.start(), "BroadcastServer failed to listen"
    port = server.port()
    try:
        yield server, port
    finally:
        server.stop()


def test_client_receives_snapshot_and_live_on_connect(qapp, broadcast_server):
    server, port = broadcast_server
    snapshot = SnapshotPayload(
        broadcaster_name="Test Broadcaster",
        drivers=[{"cust_id": 42, "driver_name": "Alice", "notes": ""}],
        race_results=[{"cust_id": 42, "subsession_id": 100, "incidents": 2}],
    )
    live = LiveStatePayload(connected=True, subsession_id=100, session_kind="race")
    server.set_snapshot(snapshot)
    server.set_live_state(live)

    snapshots: list[dict] = []
    live_states: list[dict] = []

    client = BroadcastClient(host="127.0.0.1", port=port)
    client.snapshot_received.connect(snapshots.append)
    client.live_state_received.connect(live_states.append)

    try:
        client.connect_to_broadcaster()
        assert _wait_until(qapp, lambda: client.is_connected())
        assert _wait_until(qapp, lambda: len(snapshots) >= 1 and len(live_states) >= 1)

        assert snapshots[0]["type"] == "snapshot"
        assert snapshots[0]["drivers"][0]["driver_name"] == "Alice"
        assert live_states[0]["type"] == "live"
        assert live_states[0]["session_kind"] == "race"
    finally:
        client.disconnect_from_broadcaster()
        _wait_until(qapp, lambda: not client.is_connected(), timeout_ms=2000)


def test_hello_message_identifies_receiver(qapp, broadcast_server):
    server, port = broadcast_server
    expected_name = socket.gethostname()

    client = BroadcastClient(host="127.0.0.1", port=port)
    try:
        client.connect_to_broadcaster()
        assert _wait_until(qapp, lambda: client.is_connected())
        assert _wait_until(
            qapp,
            lambda: expected_name in server.connected_receiver_names(),
        )
        assert server.connected_receiver_names() == [expected_name]
    finally:
        client.disconnect_from_broadcaster()
        _wait_until(qapp, lambda: not client.is_connected(), timeout_ms=2000)


def test_receiver_driver_patch_reaches_broadcaster(qapp, broadcast_server):
    server, port = broadcast_server
    patches: list[dict] = []
    server.receiver_patch_received.connect(patches.append)

    client = BroadcastClient(host="127.0.0.1", port=port)
    try:
        client.connect_to_broadcaster()
        assert _wait_until(qapp, lambda: client.is_connected())

        assert client.send_driver_patch(42, notes="Watch late braking")
        assert _wait_until(qapp, lambda: len(patches) >= 1)

        assert patches[0]["type"] == "driver_patch"
        assert patches[0]["cust_id"] == 42
        assert patches[0]["notes"] == "Watch late braking"
    finally:
        client.disconnect_from_broadcaster()
        _wait_until(qapp, lambda: not client.is_connected(), timeout_ms=2000)


def test_broadcaster_relays_driver_patch_to_client(qapp, broadcast_server):
    server, port = broadcast_server
    patch = driver_patch_message(99, race_preference=1)
    received: list[dict] = []

    client = BroadcastClient(host="127.0.0.1", port=port)
    client.driver_patch_received.connect(received.append)

    try:
        client.connect_to_broadcaster()
        assert _wait_until(qapp, lambda: client.is_connected())

        server.relay_driver_patch(patch)
        assert _wait_until(qapp, lambda: len(received) >= 1)

        assert received[0]["cust_id"] == 99
        assert received[0]["race_preference"] == 1
    finally:
        client.disconnect_from_broadcaster()
        _wait_until(qapp, lambda: not client.is_connected(), timeout_ms=2000)


def test_live_state_broadcast_after_client_connected(qapp, broadcast_server):
    server, port = broadcast_server
    live_states: list[dict] = []

    client = BroadcastClient(host="127.0.0.1", port=port)
    client.live_state_received.connect(live_states.append)

    try:
        client.connect_to_broadcaster()
        assert _wait_until(qapp, lambda: client.is_connected())
        live_states.clear()

        server.set_live_state(
            LiveStatePayload(
                connected=True,
                subsession_id=555,
                session_kind="qualify",
                drivers=[{"cust_id": 1, "name": "Alice"}],
            )
        )
        assert _wait_until(qapp, lambda: len(live_states) >= 1)
        assert live_states[-1]["subsession_id"] == 555
        assert live_states[-1]["session_kind"] == "qualify"
    finally:
        client.disconnect_from_broadcaster()
        _wait_until(qapp, lambda: not client.is_connected(), timeout_ms=2000)
