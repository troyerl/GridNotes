import logging

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


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
        active_drivers.append({"cust_id": int(cust_id), "name": str(name)})

    return active_drivers, subsession_id


class IRacingWorker(QThread):
    """
    Polled worker thread using pyirsdk (irsdk) to read iRacing's live session data
    without blocking the main GUI thread.
    """

    drivers_updated = pyqtSignal(list, int)  # (driver_list, subsession_id)
    connection_changed = pyqtSignal(bool, int)  # (connected, subsession_id)

    def __init__(self):
        super().__init__()
        self.running = True
        self.available = False
        self.ir = None
        self._sdk_connected = False
        self._last_emit_key: tuple | None = None
        self._last_connection_emit: bool | None = None

        try:
            import irsdk
        except Exception:
            return

        try:
            self.ir = irsdk.IRSDK()
            self.available = True
        except Exception:
            self.ir = None
            self.available = False

    def _emit_connection(self, connected: bool, subsession_id: int = 0) -> None:
        if self._last_connection_emit == connected:
            return
        self._last_connection_emit = connected
        logger.info("SDK connection_changed=%s subsession_id=%s", connected, subsession_id)
        self.connection_changed.emit(connected, subsession_id)

    def run(self):
        if not self.available or self.ir is None:
            logger.info("pyirsdk unavailable (import/IRSDK init failed).")
            return

        while self.running:
            self.msleep(1000)

            try:
                # pyirsdk uses iRacing shared memory. In some session/UI states, `is_connected`
                # can briefly be false even though the SDK is initialized. For our UI, treat
                # "initialized" as connected-to-SDK, and use `is_connected` as "fully live".
                is_initialized = bool(getattr(self.ir, "is_initialized", False))
                is_connected = bool(getattr(self.ir, "is_connected", False))

                if self._sdk_connected and not is_initialized:
                    self._sdk_connected = False
                    self._last_emit_key = None
                    self.ir.shutdown()
                    self._emit_connection(False)

                elif not self._sdk_connected:
                    # Keep trying startup until the shared memory becomes available.
                    if not self.ir.startup():
                        logger.debug("pyirsdk startup() false (shared memory not ready)")
                        continue
                    is_initialized = bool(getattr(self.ir, "is_initialized", False))
                    is_connected = bool(getattr(self.ir, "is_connected", False))
                    if not is_initialized:
                        logger.debug("pyirsdk not initialized yet")
                        continue
                    self._sdk_connected = True
                    self._last_emit_key = None
                    # Emit "connected" as soon as SDK is initialized.
                    self._emit_connection(True, 0)

                if not self._sdk_connected:
                    continue

                active_drivers, subsession_id = _parse_session_drivers(self.ir)
                logger.debug(
                    "pyirsdk tick init=%s connected=%s subsession=%s drivers=%s",
                    is_initialized,
                    is_connected,
                    subsession_id,
                    len(active_drivers),
                )

                # If the SDK is initialized but not fully connected yet, still surface that to the UI.
                # (Drivers may be empty until session info arrives.)
                if not is_connected and not active_drivers:
                    self._emit_connection(True, subsession_id)
                    continue

                emit_key = (
                    subsession_id,
                    tuple((d["cust_id"], d["name"]) for d in active_drivers),
                )
                if emit_key == self._last_emit_key:
                    continue

                self._last_emit_key = emit_key
                self._emit_connection(True, subsession_id)
                self.drivers_updated.emit(active_drivers, subsession_id)

            except Exception as e:
                logger.exception("Error reading iRacing SDK: %s", e)

    def stop(self):
        self.running = False
        if self.ir is not None and self._sdk_connected:
            try:
                self.ir.shutdown()
            except Exception:
                pass
        self.wait()
