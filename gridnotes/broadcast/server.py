"""WebSocket server that streams scouting snapshots and live session state."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QHostAddress
from PyQt6.QtWebSockets import QWebSocket, QWebSocketServer

from .protocol import LiveStatePayload, SnapshotPayload, decode_message, encode_message

logger = logging.getLogger(__name__)


class BroadcastServer(QObject):
    receiver_count_changed = pyqtSignal(int)
    receivers_changed = pyqtSignal(object)
    receiver_patch_received = pyqtSignal(object)

    def __init__(
        self,
        *,
        broadcaster_name: str,
        port: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._name = broadcaster_name
        self._port = port
        self._clients: dict[QWebSocket, str] = {}
        self._latest_snapshot: SnapshotPayload | None = None
        self._latest_live = LiveStatePayload()
        self._server = QWebSocketServer(
            "GridNotes Broadcast",
            QWebSocketServer.SslMode.NonSecureMode,
            self,
        )
        self._server.newConnection.connect(self._on_new_connection)

    def start(self) -> bool:
        if self._server.isListening():
            return True
        ok = self._server.listen(QHostAddress.SpecialAddress.Any, self._port)
        if not ok:
            logger.error("Broadcast server failed to listen on port %s", self._port)
        return ok

    def stop(self) -> None:
        for client in list(self._clients):
            client.close()
        self._clients.clear()
        if self._server.isListening():
            self._server.close()
        self._emit_receivers_changed()

    def port(self) -> int:
        return int(self._server.serverPort() or self._port)

    def set_snapshot(self, snapshot: SnapshotPayload, *, broadcast: bool = False) -> None:
        self._latest_snapshot = snapshot
        if broadcast:
            self._broadcast(snapshot.to_dict())

    def set_live_state(self, live: LiveStatePayload) -> None:
        self._latest_live = live
        self._broadcast(live.to_dict())

    def push_database_refresh(self) -> None:
        if self._latest_snapshot is not None:
            self._broadcast(self._latest_snapshot.to_dict())

    def relay_driver_patch(self, patch: dict) -> None:
        """Push a driver edit to all connected receivers."""
        self._broadcast(patch)

    def connected_receiver_names(self) -> list[str]:
        labels: list[str] = []
        for name in self._clients.values():
            labels.append(name if name else "Connecting…")
        return sorted(labels, key=lambda label: (label == "Connecting…", label.lower()))

    def _emit_receivers_changed(self) -> None:
        names = self.connected_receiver_names()
        self.receiver_count_changed.emit(len(self._clients))
        self.receivers_changed.emit(names)

    def _on_new_connection(self) -> None:
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        socket.textMessageReceived.connect(
            lambda msg, sock=socket: self._on_client_message(msg, sock)
        )
        socket.disconnected.connect(lambda sock=socket: self._remove_client(sock))
        self._clients[socket] = ""
        self._emit_receivers_changed()
        if self._latest_snapshot is not None:
            socket.sendTextMessage(encode_message(self._latest_snapshot.to_dict()))
        socket.sendTextMessage(encode_message(self._latest_live.to_dict()))

    def _remove_client(self, socket: QWebSocket) -> None:
        if socket not in self._clients:
            return
        del self._clients[socket]
        socket.deleteLater()
        self._emit_receivers_changed()

    def _on_client_message(self, raw: str, socket: QWebSocket) -> None:
        payload = decode_message(raw)
        if payload is None:
            return
        msg_type = payload.get("type")
        if msg_type == "hello":
            name = str(payload.get("receiver_name") or "").strip() or "Receiver"
            if socket in self._clients:
                self._clients[socket] = name
                logger.info("Receiver identified: %s", name)
                self._emit_receivers_changed()
            return
        if msg_type == "driver_patch":
            self.receiver_patch_received.emit(payload)

    def _broadcast(self, payload: dict) -> None:
        if not self._clients:
            return
        message = encode_message(payload)
        for client in list(self._clients):
            if client.state() == QWebSocket.State.OpenState:
                client.sendTextMessage(message)
