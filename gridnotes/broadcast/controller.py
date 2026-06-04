"""Orchestrate broadcaster mode on the sender device."""

from __future__ import annotations

import logging
import socket

from PyQt6.QtCore import QObject, QTimer

from .discovery import DiscoveryBeacon
from .protocol import BROADCAST_WS_PORT, LiveStatePayload
from .server import BroadcastServer
from .snapshot import export_database_snapshot

logger = logging.getLogger(__name__)


class BroadcastController(QObject):
    """Attach to a running GridNotesApp and stream DB + live SDK data."""

    def __init__(self, app, *, broadcaster_name: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._name = broadcaster_name or socket.gethostname()
        self._server = BroadcastServer(
            broadcaster_name=self._name,
            port=BROADCAST_WS_PORT,
            parent=self,
        )
        self._beacon = DiscoveryBeacon(
            broadcaster_name=self._name,
            ws_port=BROADCAST_WS_PORT,
            parent=self,
        )
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5000)
        self._refresh_timer.timeout.connect(self._push_database_snapshot)
        self._latest_grid_slots: list = []
        self._latest_player_cust_id = None
        self._latest_spotter: tuple[int, float] | None = None

    def start(self) -> bool:
        if not self._server.start():
            return False
        self._server.receiver_patch_received.connect(self._on_receiver_patch)
        self._beacon.start()
        self._wire_app_signals()
        self._push_database_snapshot()
        self._push_live_state(connected=self._app._sdk_connected)
        self._refresh_timer.start()
        return True

    def stop(self) -> None:
        self._refresh_timer.stop()
        try:
            self._server.receiver_patch_received.disconnect(self._on_receiver_patch)
        except TypeError:
            pass
        self._unwire_app_signals()
        self._beacon.stop()
        self._server.stop()

    def receiver_count(self) -> int:
        return len(self._server._clients)

    def server_port(self) -> int:
        return self._server.port()

    def _wire_app_signals(self) -> None:
        app = self._app
        if getattr(app, "worker", None) is not None:
            app.worker.connection_changed.connect(self._on_sdk_connection)
            app.worker.drivers_updated.connect(self._on_sdk_drivers)
            app.worker.grid_updated.connect(self._on_grid_updated)
            app.worker.spotter_car_behind.connect(self._on_spotter)

    def _unwire_app_signals(self) -> None:
        app = self._app
        if getattr(app, "worker", None) is not None:
            try:
                app.worker.connection_changed.disconnect(self._on_sdk_connection)
                app.worker.drivers_updated.disconnect(self._on_sdk_drivers)
                app.worker.grid_updated.disconnect(self._on_grid_updated)
                app.worker.spotter_car_behind.disconnect(self._on_spotter)
            except TypeError:
                pass

    def _push_database_snapshot(self, *, broadcast: bool = False) -> None:
        snapshot = export_database_snapshot(
            self._app._db_conn,
            broadcaster_name=self._name,
        )
        self._server.set_snapshot(snapshot, broadcast=broadcast)

    def _on_receiver_patch(self, patch: dict) -> None:
        from .patches import apply_driver_patch
        from .protocol import PROTOCOL_VERSION

        if not apply_driver_patch(self._app._db_conn, patch):
            logger.warning("Receiver patch did not match a driver: %s", patch.get("cust_id"))
            return
        self._app._db_conn.commit()
        self._push_database_snapshot(broadcast=False)
        try:
            cust_id = int(patch["cust_id"])
        except (KeyError, TypeError, ValueError):
            cust_id = None
        if cust_id is not None:
            self._app._apply_driver_patch_ui(cust_id, patch)
        relay = dict(patch)
        relay["type"] = "driver_patch"
        relay["version"] = PROTOCOL_VERSION
        self._server.relay_driver_patch(relay)

    def _on_sdk_connection(self, connected: bool, subsession_id: int, session_kind: str) -> None:
        self._push_live_state(
            connected=connected,
            subsession_id=subsession_id,
            session_kind=session_kind,
        )

    def _on_sdk_drivers(
        self,
        active_drivers: list,
        subsession_id: int,
        session_kind: str,
        session_context=None,
    ) -> None:
        context = session_context if isinstance(session_context, dict) else {}
        self._push_live_state(
            connected=True,
            subsession_id=subsession_id,
            session_kind=session_kind,
            session_context=context,
            drivers=active_drivers,
        )

    def _on_grid_updated(self, slots: list, player_cust_id) -> None:
        self._latest_grid_slots = slots
        self._latest_player_cust_id = player_cust_id
        self._push_live_state(connected=self._app._sdk_connected)

    def _on_spotter(self, cust_id: int, gap: float) -> None:
        self._latest_spotter = (int(cust_id), float(gap))
        self._push_live_state(connected=self._app._sdk_connected)

    def _push_live_state(
        self,
        *,
        connected: bool,
        subsession_id: int | None = None,
        session_kind: str | None = None,
        session_context: dict | None = None,
        drivers: list | None = None,
    ) -> None:
        app = self._app
        live = LiveStatePayload(
            connected=connected,
            subsession_id=int(
                subsession_id if subsession_id is not None else app.current_subsession_id
            ),
            session_kind=str(
                session_kind if session_kind is not None else app.current_session_kind
            ),
            session_context=dict(
                session_context
                if session_context is not None
                else getattr(app, "current_session_context", {})
            ),
            drivers=list(
                drivers
                if drivers is not None
                else [
                    {
                        "cust_id": cust_id,
                        "name": app.active_driver_names.get(cust_id),
                        "car_number": app.active_driver_car_numbers.get(cust_id),
                    }
                    for cust_id in sorted(app.active_cust_ids)
                ]
            ),
            grid_slots=list(self._latest_grid_slots),
            player_cust_id=self._latest_player_cust_id,
        )
        if self._latest_spotter is not None:
            live.spotter_cust_id, live.spotter_gap = self._latest_spotter
        self._server.set_live_state(live)
