from PyQt6.QtCore import QThread, pyqtSignal


class IRacingWorker(QThread):
    """
    Polled worker thread that listens to the iRacing SDK API memory map
    to avoid blocking the main GUI thread.
    """

    drivers_updated = pyqtSignal(list, int)  # (driver_list, subsession_id)

    def __init__(self):
        super().__init__()
        self.running = True
        self.available = False
        self.ir = None
        self._last_emit_key: tuple | None = None

        # Delayed import to gracefully handle situations where iRacing isn't installed
        try:
            import iracingdata
        except Exception:
            return

        try:
            self.ir = iracingdata.iracingdata()
            self.available = True
        except Exception:
            self.ir = None
            self.available = False

    def run(self):
        if not self.available or self.ir is None:
            return

        while self.running:
            self.msleep(2000)  # Poll every 2 seconds

            if not self.ir.is_connected:
                if not self.ir.startup():
                    continue

            session_info = self.ir.session_info
            if not session_info:
                continue

            try:
                subsession_id = session_info.get("WeekendInfo", {}).get("SubSessionID", 0)
                driver_info_list = session_info.get("DriverInfo", {}).get("Drivers", [])

                active_drivers = []
                for d in driver_info_list:
                    # Skip pace car (common variants)
                    if d.get("IsPaceCar") or d.get("UserName") == "Pace Car":
                        continue

                    cust_id = d.get("UserID")
                    name = d.get("UserName")
                    if cust_id is None:
                        continue
                    active_drivers.append({"cust_id": cust_id, "name": name})

                if not active_drivers:
                    continue

                emit_key = (
                    subsession_id,
                    tuple((d["cust_id"], d["name"]) for d in active_drivers),
                )
                if emit_key == self._last_emit_key:
                    continue

                self._last_emit_key = emit_key
                self.drivers_updated.emit(active_drivers, subsession_id)

            except Exception as e:
                print(f"Error parsing SDK data: {e}")

    def stop(self):
        self.running = False
        self.wait()
