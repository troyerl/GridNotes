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
        self._clients: set[QWebSocket] = set()
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
        self.receiver_count_changed.emit(0)

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

    def _on_new_connection(self) -> None:
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        socket.textMessageReceived.connect(
            lambda msg, sock=socket: self._on_client_message(msg, sock)
        )
        socket.disconnected.connect(lambda sock=socket: self._remove_client(sock))
        self._clients.add(socket)
        self.receiver_count_changed.emit(len(self._clients))
        if self._latest_snapshot is not None:
            socket.sendTextMessage(encode_message(self._latest_snapshot.to_dict()))
        socket.sendTextMessage(encode_message(self._latest_live.to_dict()))

    def _remove_client(self, socket: QWebSocket) -> None:
        self._clients.discard(socket)
        socket.deleteLater()
        self.receiver_count_changed.emit(len(self._clients))

    def _on_client_message(self, raw: str, _socket: QWebSocket) -> None:
        payload = decode_message(raw)
        if payload is None:
            return
        if payload.get("type") == "driver_patch":
            self.receiver_patch_received.emit(payload)

    def _broadcast(self, payload: dict) -> None:
        if not self._clients:
            return
        message = encode_message(payload)
        for client in list(self._clients):
            if client.state() == QWebSocket.State.OpenState:
                client.sendTextMessage(message)
