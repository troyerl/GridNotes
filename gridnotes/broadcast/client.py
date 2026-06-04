"""WebSocket client that receives broadcaster snapshots and live state."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtWebSockets import QWebSocket, QWebSocketProtocol

from .protocol import decode_message, driver_patch_message, encode_message, hello_message

logger = logging.getLogger(__name__)


def _default_websocket_version():
    """PyQt6 6.5+ uses VersionLatest; older bindings expose Version.Version13."""
    version_enum = getattr(QWebSocketProtocol, "Version", None)
    latest = getattr(QWebSocketProtocol, "VersionLatest", None)
    if latest is not None:
        return latest
    if version_enum is not None:
        for name in ("VersionLatest", "Version13", "Version8"):
            candidate = getattr(version_enum, name, None)
            if candidate is not None:
                return candidate
    return None


class BroadcastClient(QObject):
    connected_changed = pyqtSignal(bool)
    snapshot_received = pyqtSignal(object)
    live_state_received = pyqtSignal(object)
    driver_patch_received = pyqtSignal(object)
    error_message = pyqtSignal(str)

    def __init__(self, *, host: str, port: int, parent=None) -> None:
        super().__init__(parent)
        self._host = host.strip()
        self._port = port
        self._socket = QWebSocket("", _default_websocket_version(), self)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.errorOccurred.connect(self._on_error)
        self._socket.textMessageReceived.connect(self._on_message)

    def connect_to_broadcaster(self) -> None:
        url = QUrl(f"ws://{self._host}:{self._port}")
        logger.info("Connecting to broadcaster at %s", url.toString())
        self._socket.open(url)

    def disconnect_from_broadcaster(self) -> None:
        self._socket.close()

    def is_connected(self) -> bool:
        return self._socket.state() == QWebSocket.State.OpenState

    def send_driver_patch(
        self,
        cust_id: int,
        *,
        notes: str | None = None,
        race_preference: int | None | object = ...,
    ) -> bool:
        if not self.is_connected():
            return False
        payload = driver_patch_message(
            cust_id,
            notes=notes,
            race_preference=race_preference,
        )
        if "notes" not in payload and "race_preference" not in payload:
            return False
        self._socket.sendTextMessage(encode_message(payload))
        return True

    def _on_connected(self) -> None:
        import socket

        self._socket.sendTextMessage(encode_message(hello_message(socket.gethostname())))
        self.connected_changed.emit(True)

    def _on_disconnected(self) -> None:
        self.connected_changed.emit(False)

    def _on_error(self, _code) -> None:
        message = self._socket.errorString().strip()
        if message:
            self.error_message.emit(message)

    def _on_message(self, raw: str) -> None:
        payload = decode_message(raw)
        if payload is None:
            return
        msg_type = payload.get("type")
        if msg_type == "snapshot":
            self.snapshot_received.emit(payload)
        elif msg_type == "live":
            self.live_state_received.emit(payload)
        elif msg_type == "driver_patch":
            self.driver_patch_received.emit(payload)
