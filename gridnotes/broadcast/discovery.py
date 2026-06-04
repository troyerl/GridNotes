"""UDP discovery for GridNotes broadcasters on the local network."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .protocol import BROADCAST_DISCOVERY_PORT, BROADCAST_WS_PORT, DISCOVERY_MAGIC


@dataclass(frozen=True)
class BroadcasterInfo:
    name: str
    host: str
    port: int


class DiscoveryBeacon(QObject):
    """Periodically announce this machine as a broadcaster."""

    def __init__(
        self,
        *,
        broadcaster_name: str,
        ws_port: int = BROADCAST_WS_PORT,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._name = broadcaster_name
        self._ws_port = ws_port
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._send_beacon)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def start(self) -> None:
        self._send_beacon()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        try:
            self._socket.close()
        except OSError:
            pass

    def _send_beacon(self) -> None:
        payload = json.dumps(
            {
                "magic": DISCOVERY_MAGIC,
                "name": self._name,
                "port": self._ws_port,
            }
        ).encode("utf-8")
        try:
            self._socket.sendto(payload, ("<broadcast>", BROADCAST_DISCOVERY_PORT))
        except OSError:
            pass


class BroadcastDiscovery(QObject):
    """Listen for broadcaster UDP beacons on the LAN."""

    broadcaster_found = pyqtSignal(object)  # BroadcasterInfo

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._known: dict[str, BroadcasterInfo] = {}
        self._socket: socket.socket | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        if self._socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        sock.bind(("", BROADCAST_DISCOVERY_PORT))
        sock.setblocking(False)
        self._socket = sock
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def known_broadcasters(self) -> list[BroadcasterInfo]:
        return list(self._known.values())

    def _poll(self) -> None:
        if self._socket is None:
            return
        while True:
            try:
                data, addr = self._socket.recvfrom(4096)
            except BlockingIOError:
                break
            except OSError:
                break
            host = addr[0]
            try:
                payload = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if payload.get("magic") != DISCOVERY_MAGIC:
                continue
            port = int(payload.get("port") or BROADCAST_WS_PORT)
            name = str(payload.get("name") or host)
            key = f"{host}:{port}"
            info = BroadcasterInfo(name=name, host=host, port=port)
            if key not in self._known:
                self._known[key] = info
                self.broadcaster_found.emit(info)
