import logging
import sys

from PyQt6.QtCore import QThread, pyqtSignal

from .session_context import parse_session_context
from .session_kind import SESSION_KIND_OTHER, current_session_kind, is_race_session
from .grid_walk import parse_starting_grid, slots_to_payload
from .spotter_telemetry import (
    build_car_idx_to_cust_id,
    is_green_flag_run,
    resolve_cust_id_behind,
)

logger = logging.getLogger(__name__)


def parse_driver_car_number(entry: dict) -> str | None:
    """Racing number from DriverInfo (e.g. ``42`` or ``42W``)."""
    for key in ("CarNumber", "CarNumberRaw"):
        raw = entry.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text
    return None

_TICK_MS = 100
_SESSION_INTERVAL_TICKS = 10
_SPOTTER_INTERVAL_TICKS = 2


def _parse_session_drivers(ir) -> tuple[list[dict], int]:
    """Read driver list and subsession id from pyirsdk session YAML."""
    subsession_id = 0
    drivers_raw: list = []

    try:
        weekend = ir["WeekendInfo"]
        if isinstance(weekend, dict):
            subsession_id = int(weekend.get("SubSessionID") or 0)
    except Exception:
        pass

    try:
        driver_info = ir["DriverInfo"]
        if isinstance(driver_info, dict):
            drivers_raw = driver_info.get("Drivers") or []
    except Exception:
        pass

    if not isinstance(drivers_raw, list):
        drivers_raw = []

    active_drivers: list[dict] = []
    for d in drivers_raw:
        if not isinstance(d, dict):
            continue

        if d.get("CarIsPaceCar") or d.get("IsPaceCar") or d.get("UserName") == "Pace Car":
            continue

        cust_id = d.get("UserID")
        if cust_id is None:
            cust_id = d.get("CustID")
        if cust_id is None:
            continue

        name = d.get("UserName") or d.get("UserNameShort") or f"Driver {cust_id}"
        driver: dict = {"cust_id": int(cust_id), "name": str(name)}
        car_number = parse_driver_car_number(d)
        if car_number:
            driver["car_number"] = car_number
        active_drivers.append(driver)

    return active_drivers, subsession_id


def _parse_session(ir) -> tuple[list[dict], int, str, dict]:
    active_drivers, subsession_id = _parse_session_drivers(ir)
    session_kind = current_session_kind(ir)
    context = parse_session_context(ir)
    return active_drivers, subsession_id, session_kind, context


class IRacingWorker(QThread):
    """
    Polled worker thread using pyirsdk (irsdk) to read iRacing's live session data
    without blocking the main GUI thread.
    """

    drivers_updated = pyqtSignal(list, int, str, dict)  # drivers, subsession_id, kind, context
    connection_changed = pyqtSignal(bool, int, str)  # (connected, subsession_id, session_kind)
    spotter_car_behind = pyqtSignal(int, float)  # (cust_id, gap_seconds)
    grid_updated = pyqtSignal(list, object)  # (slot dicts, player_cust_id | None)

    def __init__(self):
        super().__init__()
        self.running = True
        self.available = False
        self.unavailable_reason = ""
        self.ir = None
        self._sdk_connected = False
        self._spotter_enabled = False
        self._grid_walk_enabled = False
        self._car_idx_to_cust: dict[int, int] = {}
        self._last_emit_key: tuple | None = None
        self._last_connection_key: tuple | None = None
        self._last_spotter_cust_id: int | None = None
        self._last_grid_key: tuple | None = None
        self._wait_log_counter = 0
        self._tick = 0

        logger.info("IRacingWorker init (platform=%s)", sys.platform)

        if sys.platform != "win32":
            self.unavailable_reason = "Live SDK only works on Windows with iRacing running."
            logger.warning(self.unavailable_reason)
            return

        try:
            import irsdk  # pyirsdk package

            logger.info("pyirsdk imported (irsdk module: %s)", getattr(irsdk, "__file__", "?"))
        except Exception:
            self.unavailable_reason = "pyirsdk not installed. Run: pip install pyirsdk"
            logger.exception(self.unavailable_reason)
            return

        try:
            self.ir = irsdk.IRSDK()
            self.available = True
            logger.info("IRSDK() created successfully")
        except Exception:
            self.unavailable_reason = "Failed to create IRSDK() instance"
            logger.exception(self.unavailable_reason)
            self.ir = None
            self.available = False

    def set_spotter_enabled(self, enabled: bool) -> None:
        self._spotter_enabled = bool(enabled)
        if not enabled:
            self._last_spotter_cust_id = None

    def set_grid_walk_enabled(self, enabled: bool) -> None:
        self._grid_walk_enabled = bool(enabled)
        if not enabled:
            self._last_grid_key = None

    def request_grid_refresh(self) -> None:
        self._last_grid_key = None
        self._poll_grid()

    def _poll_grid(self) -> None:
        if not self._grid_walk_enabled or self.ir is None or not self._sdk_connected:
            return

        parsed = parse_starting_grid(self.ir)
        if parsed is None:
            return

        slots, player_cust_id = parsed
        payload = slots_to_payload(slots)
        key = (tuple((p["position"], p["cust_id"]) for p in payload), player_cust_id)
        if key == self._last_grid_key:
            return
        self._last_grid_key = key
        self.grid_updated.emit(payload, player_cust_id)

    def _emit_connection(self, connected: bool, subsession_id: int = 0, session_kind: str = SESSION_KIND_OTHER) -> None:
        key = (connected, subsession_id if connected else 0, session_kind if connected else "")
        if self._last_connection_key == key:
            return
        self._last_connection_key = key
        logger.info(
            "SDK connection_changed=%s subsession_id=%s session_kind=%s",
            connected,
            subsession_id,
            session_kind,
        )
        self.connection_changed.emit(connected, subsession_id, session_kind)

    def _poll_spotter(self) -> None:
        if not self._spotter_enabled or self.ir is None or not self._sdk_connected:
            return
        if not self._car_idx_to_cust:
            return
        if not is_green_flag_run(self.ir):
            self._last_spotter_cust_id = None
            return

        resolved = resolve_cust_id_behind(self.ir, self._car_idx_to_cust)
        if resolved is None:
            self._last_spotter_cust_id = None
            return

        cust_id, gap = resolved
        if cust_id == self._last_spotter_cust_id:
            return
        self._last_spotter_cust_id = cust_id
        self.spotter_car_behind.emit(cust_id, gap)

    def _poll_session(self) -> None:
        if self.ir is None or not self._sdk_connected:
            return

        is_connected = bool(getattr(self.ir, "is_connected", False))
        active_drivers, subsession_id, session_kind, session_context = _parse_session(self.ir)
        self._car_idx_to_cust = build_car_idx_to_cust_id(self.ir)

        if not is_connected and not active_drivers:
            self._emit_connection(True, subsession_id, session_kind)
            return

        emit_key = (
            subsession_id,
            session_kind,
            tuple((d["cust_id"], d["name"]) for d in active_drivers),
        )
        if emit_key == self._last_emit_key:
            return

        self._last_emit_key = emit_key
        logger.info(
            "Session update: subsession=%s kind=%s drivers=%s",
            subsession_id,
            session_kind,
            len(active_drivers),
        )
        self._emit_connection(True, subsession_id, session_kind)
        self.drivers_updated.emit(
            active_drivers, subsession_id, session_kind, session_context
        )

    def run(self):
        if not self.available or self.ir is None:
            logger.warning(
                "SDK worker exiting: available=%s reason=%s",
                self.available,
                self.unavailable_reason or "unknown",
            )
            return

        logger.info("SDK worker thread started — polling iRacing shared memory")

        while self.running:
            self.msleep(_TICK_MS)
            self._tick += 1

            try:
                is_initialized = bool(getattr(self.ir, "is_initialized", False))
                is_connected = bool(getattr(self.ir, "is_connected", False))

                if self._sdk_connected and not is_initialized:
                    logger.info("iRacing SDK lost (no longer initialized)")
                    self._sdk_connected = False
                    self._last_emit_key = None
                    self._last_connection_key = None
                    self._last_spotter_cust_id = None
                    self._last_grid_key = None
                    self._car_idx_to_cust = {}
                    self.ir.shutdown()
                    self._emit_connection(False)

                elif not self._sdk_connected:
                    if not self.ir.startup():
                        self._wait_log_counter += 1
                        if self._wait_log_counter % 10 == 1:
                            logger.info(
                                "Waiting for iRacing shared memory (startup() returned false). "
                                "Is iRacing running and are you in a session?"
                            )
                        continue

                    is_initialized = bool(getattr(self.ir, "is_initialized", False))
                    is_connected = bool(getattr(self.ir, "is_connected", False))
                    if not is_initialized:
                        self._wait_log_counter += 1
                        if self._wait_log_counter % 10 == 1:
                            logger.info(
                                "iRacing shared memory found but SDK not initialized yet "
                                "(is_connected=%s)",
                                is_connected,
                            )
                        continue

                    self._sdk_connected = True
                    self._last_emit_key = None
                    self._wait_log_counter = 0
                    logger.info(
                        "iRacing SDK connected (initialized=%s, is_connected=%s)",
                        is_initialized,
                        is_connected,
                    )
                    self._emit_connection(True, 0)

                if not self._sdk_connected:
                    continue

                if self._spotter_enabled and self._tick % _SPOTTER_INTERVAL_TICKS == 0:
                    self._poll_spotter()

                if self._grid_walk_enabled and self._tick % _SESSION_INTERVAL_TICKS == 0:
                    self._poll_grid()

                if self._tick % _SESSION_INTERVAL_TICKS == 0:
                    self._poll_session()

            except Exception:
                logger.exception("Error reading iRacing SDK")

    def stop(self):
        self.running = False
        if self.ir is not None and self._sdk_connected:
            try:
                self.ir.shutdown()
            except Exception:
                pass
        if not self.wait(5000):
            logger.warning("SDK worker thread did not stop within 5s")
        else:
            logger.info("SDK worker thread stopped")
