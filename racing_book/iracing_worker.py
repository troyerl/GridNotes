import logging
import sys

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
        self.unavailable_reason = ""
        self.ir = None
        self._sdk_connected = False
        self._last_emit_key: tuple | None = None
        self._last_connection_key: tuple | None = None
        self._wait_log_counter = 0

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

    def _emit_connection(self, connected: bool, subsession_id: int = 0) -> None:
        key = (connected, subsession_id if connected else 0)
        if self._last_connection_key == key:
            return
        self._last_connection_key = key
        logger.info("SDK connection_changed=%s subsession_id=%s", connected, subsession_id)
        self.connection_changed.emit(connected, subsession_id)

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
            self.msleep(1000)

            try:
                is_initialized = bool(getattr(self.ir, "is_initialized", False))
                is_connected = bool(getattr(self.ir, "is_connected", False))

                if self._sdk_connected and not is_initialized:
                    logger.info("iRacing SDK lost (no longer initialized)")
                    self._sdk_connected = False
                    self._last_emit_key = None
                    self._last_connection_key = None
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

                active_drivers, subsession_id = _parse_session_drivers(self.ir)

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
                logger.info(
                    "Session update: subsession=%s drivers=%s",
                    subsession_id,
                    len(active_drivers),
                )
                self._emit_connection(True, subsession_id)
                self.drivers_updated.emit(active_drivers, subsession_id)

            except Exception:
                logger.exception("Error reading iRacing SDK")

    def stop(self):
        self.running = False
        if self.ir is not None and self._sdk_connected:
            try:
                self.ir.shutdown()
            except Exception:
                pass
        self.wait()
        logger.info("SDK worker thread stopped")
