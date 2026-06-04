"""Emit IRacingWorker-compatible signals from broadcast live payloads."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class BroadcastSessionFeed(QObject):
    """Feeds live session / grid / spotter updates from a remote broadcaster."""

    connection_changed = pyqtSignal(bool, int, str)
    drivers_updated = pyqtSignal(list, int, str, dict)
    grid_updated = pyqtSignal(list, object)
    spotter_car_behind = pyqtSignal(int, float)

    def apply_live_state(self, payload: dict) -> None:
        connected = bool(payload.get("connected"))
        subsession_id = int(payload.get("subsession_id") or 0)
        session_kind = str(payload.get("session_kind") or "")
        session_context = payload.get("session_context") or {}
        if not isinstance(session_context, dict):
            session_context = {}

        self.connection_changed.emit(connected, subsession_id, session_kind)
        if not connected:
            return

        drivers = list(payload.get("drivers") or [])
        self.drivers_updated.emit(
            drivers,
            subsession_id,
            session_kind,
            session_context,
        )

        grid_slots = list(payload.get("grid_slots") or [])
        player_cust_id = payload.get("player_cust_id")
        self.grid_updated.emit(grid_slots, player_cust_id)

        spotter_cust_id = payload.get("spotter_cust_id")
        spotter_gap = payload.get("spotter_gap")
        if spotter_cust_id is not None and spotter_gap is not None:
            try:
                self.spotter_car_behind.emit(int(spotter_cust_id), float(spotter_gap))
            except (TypeError, ValueError):
                pass
