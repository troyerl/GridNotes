import logging
import os
import sys
from pathlib import Path
from typing import NamedTuple

from PyQt6.QtCore import QEvent, QEventLoop, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QKeySequence, QShortcut, QShowEvent, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..services.app_update import (
    AUTO_CHECK_UPDATES_KEY,
    GITHUB_RELEASES_PAGE,
    UpdateCheckResult,
    is_frozen_build,
    restart_application,
)
from ..services.app_update_worker import ApplyAppUpdateWorker, UpdateCheckWorker
from ..ui.appearance import get_theme_id, normalize_theme_id
from ..data.data_retention import DEFAULT_RETENTION, SETTING_KEY, purge_expired_race_results
from ..data.note_tags import chip_label, load_note_tags
from ..data.db import close_sqlite_connection, connect_db, get_setting, init_db, set_setting
from ..data.driver_cleanup import count_zero_race_drivers, purge_zero_race_drivers
from ..data.driver_models import (
    DriverDetailRow,
    DriverTableRow,
    build_live_session_entries,
    format_head_to_head_record,
    head_to_head_tooltip,
    format_live_session_at_glance,
    format_shared_races_label,
)
from ..ui.a11y import driver_mark_label, set_accessible, set_button_tooltip
from ..ui.icons import set_button_fa_icon, set_label_fa_icon, wire_main_tabs
from ..privacy.streamer_mode import (
    STREAMER_MODE_KEY,
    display_driver_name,
    is_streamer_mode_enabled,
    mask_cust_id_display,
    streamer_detail_meta,
    streamer_display_name,
)
from ..ui.driver_table import (
    COL_CUST_ID,
    COL_LEAGUE,
    COL_MARK,
    COL_NAME,
    COL_NOTE,
    COL_SAFETY,
    COL_SERIES,
    COL_VS_YOU,
    COLUMN_COUNT,
    DRIVER_TABLE_HEADERS,
    PREF_DATA_ROLE,
    REAL_NAME_DATA_ROLE,
    RISK_DATA_ROLE,
    configure_driver_table_columns,
    configure_driver_table_theme,
    configure_driver_table_widget,
    save_driver_table_column_widths,
    make_league_item,
    make_mark_item,
    make_note_item,
    make_safety_item,
    make_table_item,
    refresh_driver_table_icon_colors,
    refresh_driver_table_row,
    set_driver_table_hover_row,
    table_row_sort_key,
)
from ..iracing.import_worker import ImportJobResult, ImportWorker
from ..iracing.iracing_api_fetch_worker import (
    ApiConnectionTestWorker,
    SubsessionFetchResult,
    SubsessionFetchWorker,
)
from .feature_flags import iracing_data_api_auto_import_enabled
from ..iracing.iracing_data_api_config import is_auto_fetch_enabled
from ..iracing.iracing_worker import IRacingWorker
from ..iracing.iracing_import import sync_live_session_drivers
from ..ui.live_session import LiveSessionView
from ..ui.scouting_guide_dialog import show_scouting_guide
from ..ui.import_progress_dialog import ImportProgressDialog
from ..ui.import_history_tab import ImportHistoryTab
from ..ui.race_history_tab import RaceHistoryTab
from ..ui.leagues_tab import LeaguesTab
from ..ui.streamer_mode_progress_dialog import StreamerModeProgressDialog
from ..data.leagues import fetch_league_membership_labels
from ..data.queries import (
    driver_detail_sql,
    fetch_head_to_head_records,
    fetch_recent_races_by_cust_ids,
    fetch_shared_race_counts,
    table_data_for_cust_ids_sql,
    table_data_sql,
)
from ..iracing.session_kind import is_live_scouting_session, is_race_session, session_kind_label
from ..safety.safety_index import SafetyIndex, empty_safety, safety_tooltip
from ..safety.safety_trend import (
    SafetyTrend,
    compute_safety_trend,
    compute_safety_trends_for_cust_ids,
)
from ..ui.safety_widgets import SafetyIndexPanel
from ..ui.settings_tab import SettingsTab
from ..core.timestamps import display_timezone_abbrev, format_last_seen
from ..ui.table_pagination import DEFAULT_PAGE_SIZE, TablePaginationBar
from ..ui.theme import (
    STATUS_CONNECTED,
    STATUS_OFFLINE,
    STATUS_WAITING,
    apply_app_theme,
    configure_scroll_area,
    configure_widget_scrollbars,
    refresh_widget_tree,
)
from ..ui.ui_widgets import WrappingLabel
from ..services.user_feedback import log_user_error, show_critical, show_warning
from ..core.utils import display_val, sqlite_row_to_int
from .app_icon import load_app_icon

logger = logging.getLogger(__name__)

MSG_SESSION_NOT_CONNECTED = (
    "Not connected to iRacing yet — start iRacing and join a session to enable."
)

TIP_BROADCAST = (
    "Broadcaster — share your scouting book and live iRacing session with another "
    "device on your local network. This PC keeps running iRacing; the main window "
    "hides while broadcasting."
)
TIP_BROADCAST_DISABLED = (
    "Broadcaster — unavailable while connected as a receiver. Disconnect first."
)
TIP_RECEIVER = (
    "Receiver — connect to a broadcaster on your network to view its scouting book "
    "and live session. Notes and likes you change sync back to the broadcaster "
    "(not saved on this device)."
)
TIP_RECEIVER_DISABLED = (
    "Receiver — unavailable while already connected to a broadcaster. Disconnect first."
)
TIP_DISCONNECT = (
    "Disconnect — stop viewing the broadcaster and return to your local scouting book."
)

SEARCH_FILTER_DEBOUNCE_MS = 150


class _DriverFilterMeta(NamedTuple):
    row: tuple
    name_lc: str
    display_lc: str
    cust_id: int
    race_preference: int | None
    risky: bool


TIP_STREAMER_MODE = (
    "Streamer mode — replace driver names with aliases on screen (e.g. Driver #14). "
    "Your database and notes are not changed."
)
TIP_LIVE_MODE = (
    "Live Mode — switch to a high-contrast live session view with large fonts for "
    "in-race scouting."
)

PLAYER_CUST_ID_KEY = "player_cust_id"

# Full table rebuild when more drivers changed than this after import.

class GridNotesApp(QMainWindow):
    def __init__(self, splash=None):
        super().__init__()
        self._splash = splash
        self.setWindowTitle("GridNotes")
        self.setMinimumSize(1280, 760)
        self.resize(1440, 860)

        window_icon = load_app_icon()
        if window_icon is not None:
            self.setWindowIcon(window_icon)
        self._taskbar_identity_applied = False

        self.current_subsession_id = 0
        self.current_session_kind = ""
        self.current_session_context: dict[str, str] = {}
        self.selected_cust_id = None
        self.worker = None
        self._import_worker: ImportWorker | None = None
        self._import_progress_dialog: ImportProgressDialog | None = None
        self._api_test_worker: ApiConnectionTestWorker | None = None
        self._update_check_worker: UpdateCheckWorker | None = None
        self._apply_update_worker: ApplyAppUpdateWorker | None = None
        self._update_progress_dialog = None
        self._update_exit_timer: QTimer | None = None
        self._update_check_on_startup = False
        self._api_fetch_worker: SubsessionFetchWorker | None = None
        self._api_fetch_queue: list[int] = []
        self._api_fetched_subsession_ids: set[int] = set()
        self._tracked_race_subsession_id: int = 0
        self._table_refresh_timer = QTimer(self)
        self._table_refresh_timer.setSingleShot(True)
        self._table_refresh_timer.setInterval(750)
        self._table_refresh_timer.timeout.connect(self._refresh_ui_table_now)
        self._last_table_fingerprint: tuple | None = None
        self._table_rows_cache: list[tuple] = []
        self._table_filter_index: list[_DriverFilterMeta] = []
        self._filtered_table_rows: list[tuple] = []
        self._filtered_mark_stats: tuple[int, int, int] = (0, 0, 0)
        self._head_to_head_by_cust: dict[int, tuple[int, int, int]] = {}
        self._search_filter_timer = QTimer(self)
        self._search_filter_timer.setSingleShot(True)
        self._search_filter_timer.setInterval(SEARCH_FILTER_DEBOUNCE_MS)
        self._search_filter_timer.timeout.connect(self.apply_driver_filters)
        self._table_page = 0
        self._table_page_size = DEFAULT_PAGE_SIZE
        self._table_sort_column = COL_NAME
        self._table_sort_order = Qt.SortOrder.AscendingOrder
        self.active_cust_ids: set[int] = set()
        self.active_driver_names: dict[int, str] = {}
        self.active_driver_car_numbers: dict[int, str] = {}
        self._hover_row: int | None = None
        self._live_mode_active = get_setting("live_mode", "0") == "1"
        self._streamer_mode = is_streamer_mode_enabled(get_setting(STREAMER_MODE_KEY))
        self._streamer_refresh_busy = False
        self._streamer_progress_dialog: StreamerModeProgressDialog | None = None
        self._sdk_connected = False
        self._latest_grid_slots: list[dict] = []
        self._latest_grid_player_cust_id: int | None = None
        from ..services.audio_spotter import (
            AUDIO_SPOTTER_KEY,
            AudioSpotterService,
            is_audio_spotter_setting_enabled,
        )

        self._audio_spotter_enabled = is_audio_spotter_setting_enabled(
            get_setting(AUDIO_SPOTTER_KEY)
        )
        self._audio_spotter = AudioSpotterService()
        self._broadcast_controller = None
        self._broadcast_status_dialog = None
        self._broadcast_audio_spotter_enabled = False
        self._broadcast_client = None
        self._broadcast_session_feed = None
        self._using_broadcast_db = False
        self._local_db_conn = None
        self._broadcast_source_name = ""
        self._broadcast_connect_host = ""
        self._broadcast_receiver_ws_connected = False
        self._ignore_broadcast_disconnect_signal = False
        self._broadcast_connect_timer = QTimer(self)
        self._broadcast_connect_timer.setSingleShot(True)
        self._broadcast_connect_timer.timeout.connect(self._on_broadcast_connect_timeout)
        self._shutting_down = False

        self._splash_message("Loading database…")
        self._splash_pulse()
        init_db()
        try:
            from ..installer.update_paths import prune_old_update_workspaces

            prune_old_update_workspaces()
        except Exception:
            pass
        self._db_conn = connect_db()
        self._run_data_retention_purge()
        self._splash_message("Building interface…")
        self._splash_pulse()
        self.init_ui()
        self._sync_windows_install_metadata()
        self.start_sdk_worker()
        if get_setting(AUTO_CHECK_UPDATES_KEY, "0") == "1":
            QTimer.singleShot(800, self._check_for_app_updates_on_startup)

    def _splash_message(self, message: str) -> None:
        splash = getattr(self, "_splash", None)
        if splash is None:
            return
        splash.set_message(message)

    def _splash_pulse(self) -> None:
        splash = getattr(self, "_splash", None)
        if splash is not None:
            splash.pulse()

    def _sync_windows_install_metadata(self) -> None:
        """Keep Settings → Apps and the version label in sync with the installed release."""
        try:
            from ..app.app_version import effective_install_root, reconcile_installed_version
            from ..installer.logic import save_install_location
            from ..services.app_update import is_frozen_build

            install_root = effective_install_root()
            if install_root is not None:
                reconcile_installed_version(install_root)
                if is_frozen_build():
                    save_install_location(install_root)
        except Exception:
            pass
        if sys.platform != "win32":
            return
        try:
            from ..app.app_version import effective_install_root
            from ..platform.windows.windows_apps import register_windows_uninstall

            install_root = effective_install_root()
            if install_root is not None:
                register_windows_uninstall(install_root)
        except Exception:
            pass

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if self._taskbar_identity_applied or sys.platform != "win32":
            return
        self._taskbar_identity_applied = True
        try:
            from ..app.app_icon import set_windows_app_user_model_id, shell_icon_path
            from ..installer.logic import VENV_DIR_NAME, preferred_shortcut_target
            from ..installer.shortcuts import ensure_windows_shortcuts_for_taskbar
            from ..installer.uninstall import resolve_install_root
            from ..platform.windows.windows_shell import (
                apply_window_taskbar_identity,
                build_relaunch_command,
            )

            set_windows_app_user_model_id()
            icon = shell_icon_path()
            install_root = resolve_install_root()
            relaunch = build_relaunch_command(install_root) if install_root else None
            if install_root is not None:
                venv_dir = install_root / VENV_DIR_NAME
                from ..installer.logic import ensure_windows_launcher

                ensure_windows_launcher(install_root, venv_dir)
                target, working_dir, arguments = preferred_shortcut_target(
                    install_root,
                    venv_dir,
                )
                from ..installer.logic import resolve_shortcut_icon

                shortcut_icon = resolve_shortcut_icon(
                    install_root,
                    launch_target=target,
                )
                ensure_windows_shortcuts_for_taskbar(
                    install_root,
                    target=target,
                    working_dir=working_dir,
                    arguments=arguments,
                    icon=shortcut_icon or icon,
                )
            apply_window_taskbar_identity(
                self,
                icon,
                relaunch_command=relaunch,
                display_name="GridNotes",
            )
            QTimer.singleShot(750, self._retry_windows_taskbar_branding)
        except Exception:
            pass

    def _retry_windows_taskbar_branding(self) -> None:
        if sys.platform != "win32":
            return
        try:
            from ..app.app_icon import shell_icon_path
            from ..installer.uninstall import resolve_install_root
            from ..platform.windows.windows_shell import (
                apply_window_taskbar_identity,
                build_relaunch_command,
            )

            install_root = resolve_install_root()
            relaunch = build_relaunch_command(install_root) if install_root else None
            apply_window_taskbar_identity(
                self,
                shell_icon_path(),
                relaunch_command=relaunch,
                display_name="GridNotes",
            )
        except Exception:
            pass

    def _polish_property(self, widget: QWidget, name: str, value) -> None:
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_status(
        self, status: str, message: str, *, user_error: bool = False
    ) -> None:
        if user_error:
            log_user_error(message, context="status")
        self.status_label.setText(message)
        self._polish_property(self.status_label, "status", status)

    def _configure_driver_table(self) -> None:
        self.table.setObjectName("driverTable")

        body_font = QFont()
        body_font.setPointSize(12)
        self.table.setFont(body_font)

        header_font = QFont(body_font)
        header_font.setPointSize(11)
        header_font.setBold(True)
        header = self.table.horizontalHeader()
        header.setFont(header_font)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.setToolTip("Click a column header to sort · drag the edge to resize")
        header.setMinimumSectionSize(48)
        header.setDefaultSectionSize(100)
        header.setStretchLastSection(False)
        header.sectionResized.connect(self._on_driver_table_column_resized)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)

        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        row_h = self.table.verticalHeader().defaultSectionSize()
        self._configure_driver_table_scroll_steps(row_h)

        configure_driver_table_columns(self.table)
        self.table.setColumnHidden(COL_CUST_ID, True)

        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item is not None:
                label = header_item.text()
                header_item.setToolTip(
                    f"Click to sort by {label} · drag the column edge to resize"
                )

        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.entered.connect(self._on_table_row_entered)
        self.table.installEventFilter(self)
        self.table.viewport().installEventFilter(self)

    def _configure_driver_table_scroll_steps(self, row_h: int) -> None:
        configure_widget_scrollbars(
            self.table,
            single_step=row_h,
            page_step=row_h * 4,
            horizontal_single=72,
            horizontal_page=240,
            always_show=True,
        )

    def _on_driver_table_column_resized(
        self, _index: int, _old_size: int, _new_size: int
    ) -> None:
        save_driver_table_column_widths(self.table)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.table.viewport() and event.type() == QEvent.Type.Leave:
            self._clear_table_row_hover()
        if (
            obj is self.table
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and self.selected_cust_id is not None
        ):
            self.notes_edit.setFocus()
            return True
        return super().eventFilter(obj, event)

    def _pref_for_row(self, row_idx: int) -> int | None:
        name_item = self.table.item(row_idx, COL_NAME)
        if name_item is None:
            return None
        return sqlite_row_to_int(name_item.data(PREF_DATA_ROLE))

    def _restore_row_background(self, row_idx: int) -> None:
        refresh_driver_table_row(self.table, row_idx)

    def _apply_row_hover(self, row_idx: int) -> None:
        selected = self.table.selectionModel().selectedRows()
        if selected and selected[0].row() == row_idx:
            return
        set_driver_table_hover_row(self.table, row_idx)

    def _clear_table_row_hover(self) -> None:
        if self._hover_row is None:
            return
        set_driver_table_hover_row(self.table, None)
        self._hover_row = None

    def _on_table_row_entered(self, index) -> None:
        if not index.isValid():
            return
        row = index.row()
        if row == self._hover_row:
            return
        self._clear_table_row_hover()
        self._hover_row = row
        self._apply_row_hover(row)

    def _update_live_session_filter(self, *, active: bool, hint: str) -> None:
        self.chk_current_race_only.setVisible(active)
        self.chk_current_race_only.setEnabled(active)
        self.live_session_note.setVisible(not active)
        self.live_session_note.setText(hint)
        if not active:
            self.chk_current_race_only.setChecked(False)

    def _show_scouting_guide(self) -> None:
        show_scouting_guide(self)

    def _toggle_streamer_mode(self) -> None:
        if self._streamer_refresh_busy:
            return
        active = self.btn_streamer_mode.isChecked()
        self._streamer_mode = active
        set_setting(STREAMER_MODE_KEY, "1" if active else "0")
        self._polish_property(self.btn_streamer_mode, "active", active)
        self.app_subtitle.setText(
            "Streamer mode — names hidden on screen"
            if active
            else "Driver scouting notes & race history"
        )
        if active:
            self.search_input.setPlaceholderText("Search by alias (#14) or real name…")
        else:
            self.search_input.setPlaceholderText("Search drivers by name…")
        self._begin_streamer_mode_refresh(enabling=active)
        QTimer.singleShot(0, self._complete_streamer_mode_toggle)

    def _begin_streamer_mode_refresh(self, *, enabling: bool) -> None:
        self._streamer_refresh_busy = True
        self.btn_streamer_mode.setEnabled(False)
        self._streamer_progress_dialog = StreamerModeProgressDialog(
            self, enabling=enabling
        )
        self._streamer_progress_dialog.show()
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def _end_streamer_mode_refresh(self) -> None:
        if self._streamer_progress_dialog is not None:
            self._streamer_progress_dialog.close()
            self._streamer_progress_dialog.deleteLater()
            self._streamer_progress_dialog = None
        self.btn_streamer_mode.setEnabled(True)
        self._streamer_refresh_busy = False

    def _complete_streamer_mode_toggle(self) -> None:
        try:
            self._refresh_streamer_displays()
        finally:
            self._end_streamer_mode_refresh()

    def _refresh_streamer_displays(self) -> None:
        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)
        if self.selected_cust_id is not None:
            self._populate_driver_details(self.selected_cust_id)
        self._refresh_live_session_view()

    def _toggle_live_mode(self) -> None:
        self._set_live_mode(self.btn_live_mode.isChecked())

    def _set_live_mode(self, active: bool, *, persist: bool = True) -> None:
        self._live_mode_active = active
        if hasattr(self, "btn_live_mode"):
            self.btn_live_mode.blockSignals(True)
            self.btn_live_mode.setChecked(active)
            self.btn_live_mode.blockSignals(False)
            self._polish_property(self.btn_live_mode, "active", active)
        if hasattr(self, "view_stack"):
            self.view_stack.setCurrentIndex(1 if active else 0)
        if persist:
            set_setting("live_mode", "1" if active else "0")
        if active:
            self._refresh_live_session_view()
        self._sync_audio_spotter_worker()
        if not active:
            self._audio_spotter.reset_tracking()
            if hasattr(self, "live_session_view"):
                self.live_session_view.set_grid_walk_mode(False, emit=False)
            self._sync_grid_walk_worker()

    def _on_grid_walk_toggled(self, active: bool) -> None:
        self._sync_grid_walk_worker()
        if active:
            if self.worker is not None:
                self.worker.request_grid_refresh()
            self._refresh_grid_walk_view()
        else:
            self._refresh_live_session_view()

    def _sync_grid_walk_worker(self) -> None:
        if self.worker is None:
            return
        enabled = self._live_mode_active and self.live_session_view.is_grid_walk_mode()
        self.worker.set_grid_walk_enabled(enabled)

    def _push_grid_walk_view(
        self,
        slots: list | None = None,
        player_cust_id: int | None = None,
    ) -> None:
        if not hasattr(self, "live_session_view") or not self.live_session_view.is_grid_walk_mode():
            return
        if slots is None:
            slots = self._latest_grid_slots
        if player_cust_id is None:
            player_cust_id = self._latest_grid_player_cust_id
        entries = self._build_live_session_entries()
        by_cust = {int(e["cust_id"]): e for e in entries}
        cust_id = int(player_cust_id) if player_cust_id is not None else None
        self.live_session_view.update_grid(
            list(slots),
            cust_id,
            by_cust,
            streamer_mode=self._streamer_mode,
        )

    def _refresh_grid_walk_view(self) -> None:
        if not hasattr(self, "live_session_view") or not self.live_session_view.is_grid_walk_mode():
            return
        self._push_grid_walk_view()
        if self.worker is not None and self._sdk_connected:
            self.worker.request_grid_refresh()

    def _on_grid_updated(self, slots: list, player_cust_id) -> None:
        self._latest_grid_slots = list(slots)
        if player_cust_id is not None:
            try:
                self._remember_player_cust_id(int(player_cust_id))
            except (TypeError, ValueError):
                pass
        if not self._live_mode_active or not self.live_session_view.is_grid_walk_mode():
            return
        self._push_grid_walk_view(slots, player_cust_id)

    def _on_audio_spotter_setting_changed(self, enabled: bool) -> None:
        if self._audio_spotter_enabled == enabled:
            return
        self._audio_spotter_enabled = enabled
        set_setting(AUDIO_SPOTTER_KEY, "1" if enabled else "0")
        if hasattr(self, "settings_tab"):
            self.settings_tab.set_audio_spotter_enabled(enabled)
        if hasattr(self, "live_session_view"):
            self.live_session_view.set_audio_spotter_enabled(enabled)
        self._sync_audio_spotter_worker()
        if not enabled:
            self._audio_spotter.reset_tracking()

    def _on_broadcast_audio_spotter_changed(self, enabled: bool) -> None:
        if self._broadcast_audio_spotter_enabled == enabled:
            return
        self._broadcast_audio_spotter_enabled = enabled
        self._sync_audio_spotter_worker()
        if not enabled:
            self._audio_spotter.reset_tracking()

    def _audio_spotter_should_run(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._broadcast_controller is not None and self._broadcast_audio_spotter_enabled:
            return True
        return self._live_mode_active and self._audio_spotter_enabled

    def _sync_audio_spotter_worker(self) -> None:
        if self.worker is None:
            return
        self.worker.set_spotter_enabled(self._audio_spotter_should_run())

    def _on_spotter_car_behind(self, cust_id: int, gap: float) -> None:
        from ..services.audio_spotter import load_spotter_driver

        if not self._audio_spotter_should_run():
            return
        info = load_spotter_driver(self._db_conn, int(cust_id))
        if info is None:
            return
        logger.info(
            "Spotter: car behind cust_id=%s gap=%.2fs name=%s",
            cust_id,
            gap,
            info.name,
        )
        announce_name = None
        if self._streamer_mode:
            announce_name = self._streamer_session_display_name(
                int(cust_id), info.safety
            )
        self._audio_spotter.maybe_announce(
            int(cust_id), info, announce_name=announce_name
        )

    def _current_session_drivers_for_leagues(self) -> list[tuple[int, str]]:
        return [
            (
                int(cust_id),
                self.active_driver_names.get(int(cust_id), f"Driver #{cust_id}"),
            )
            for cust_id in sorted(self.active_cust_ids)
        ]

    def _remember_player_cust_id(self, cust_id: int | None) -> None:
        if cust_id is None:
            return
        try:
            resolved = int(cust_id)
        except (TypeError, ValueError):
            return
        if resolved <= 0:
            return
        self._latest_grid_player_cust_id = resolved
        set_setting(PLAYER_CUST_ID_KEY, str(resolved))
        if self._table_rows_cache:
            self._refresh_head_to_head_cache()
            if hasattr(self, "table"):
                self._render_table_page()
        if self._live_mode_active and self.active_cust_ids:
            self._refresh_live_session_view()

    def _resolve_player_cust_id(self) -> int | None:
        """Your iRacing cust_id when known (SDK, saved setting, or hidden name)."""
        if self._latest_grid_player_cust_id is not None:
            return int(self._latest_grid_player_cust_id)

        ctx_player = (self.current_session_context or {}).get("player_cust_id")
        if ctx_player is not None:
            try:
                return int(ctx_player)
            except (TypeError, ValueError):
                pass

        stored = (get_setting(PLAYER_CUST_ID_KEY, "") or "").strip()
        if stored.isdigit():
            return int(stored)

        ignore_name = self._hidden_driver_name_lc()
        if not ignore_name:
            return None

        for cust_id, name in self.active_driver_names.items():
            if str(name or "").strip().lower() == ignore_name:
                return int(cust_id)
        return None

    def _build_live_session_entries(self) -> list[dict]:
        if not self.active_cust_ids:
            return []
        cursor = self._db_conn.cursor()
        sql, params = table_data_for_cust_ids_sql(sorted(self.active_cust_ids))
        cursor.execute(sql, params)
        rows = [DriverTableRow.from_sql_row(row) for row in cursor.fetchall()]
        entries = build_live_session_entries(
            self.active_cust_ids,
            self.active_driver_names,
            rows,
        )
        lifetime_by_cust = {
            int(e["cust_id"]): e["safety"]
            for e in entries
            if isinstance(e.get("safety"), SafetyIndex) and e["safety"].tier != "unknown"
        }
        trends = compute_safety_trends_for_cust_ids(self._db_conn, lifetime_by_cust)
        league_labels = fetch_league_membership_labels(
            self._db_conn,
            self.active_cust_ids,
        )
        for entry in entries:
            entry["safety_trend"] = trends.get(int(entry["cust_id"]))
            entry["league_label"] = league_labels.get(int(entry["cust_id"]), "")

        player_cust_id = self._resolve_player_cust_id()
        shared_counts: dict[int, int] = {}
        head_to_head: dict[int, tuple[int, int, int]] = {}
        if player_cust_id is not None:
            active_ids = sorted(self.active_cust_ids)
            shared_counts = fetch_shared_race_counts(
                self._db_conn,
                player_cust_id,
                active_ids,
            )
            head_to_head = fetch_head_to_head_records(
                self._db_conn,
                player_cust_id,
                active_ids,
            )
        for entry in entries:
            cid = int(entry["cust_id"])
            if player_cust_id is None or cid == player_cust_id:
                entry["together_races"] = None
                entry["head_to_head"] = None
            else:
                entry["together_races"] = int(shared_counts.get(cid, 0))
                entry["head_to_head"] = head_to_head.get(cid)

        if self._streamer_mode:
            for entry in entries:
                cid = int(entry["cust_id"])
                safety = entry.get("safety")
                if not isinstance(safety, SafetyIndex):
                    safety = None
                entry["name"] = self._streamer_session_display_name(cid, safety)
        return entries

    def _streamer_session_display_name(
        self,
        cust_id: int,
        safety: SafetyIndex | None,
        *,
        compact: bool = False,
    ) -> str:
        """Streamer alias; uses session car number in Live Mode when available."""
        car_number = self.active_driver_car_numbers.get(int(cust_id))
        return streamer_display_name(
            int(cust_id),
            safety,
            compact=compact,
            car_number=car_number,
        )

    def _refresh_live_session_view(self) -> None:
        if not hasattr(self, "live_session_view"):
            return
        driver_count = len(self.active_cust_ids)
        scouting = is_live_scouting_session(self.current_session_kind)
        entries: list[dict] = []
        at_glance = ""
        if scouting and self.active_cust_ids:
            entries = self._build_live_session_entries()
            at_glance = format_live_session_at_glance(entries)
        self.live_session_view.set_session_info(
            connected=self._sdk_connected,
            subsession_id=self.current_subsession_id,
            driver_count=driver_count,
            session_kind=self.current_session_kind,
            persist_drivers=is_race_session(self.current_session_kind),
            context=self.current_session_context,
            at_glance=at_glance,
        )
        if self._sdk_connected and scouting and self.active_cust_ids:
            if self.live_session_view.is_grid_walk_mode():
                self._refresh_grid_walk_view()
            else:
                self.live_session_view.rebuild_if_changed(entries)
                expanded = self.live_session_view.expanded_cust_id()
                if expanded is not None:
                    self._populate_live_expanded_detail(expanded, entries=entries)

    def _on_live_driver_expand_requested(self, cust_id: int) -> None:
        self._populate_live_expanded_detail(int(cust_id))

    def _live_entry_for_cust_id(
        self,
        cust_id: int,
        entries: list[dict] | None = None,
    ) -> dict | None:
        source = entries if entries is not None else self._build_live_session_entries()
        for entry in source:
            if int(entry.get("cust_id", -1)) == int(cust_id):
                return entry
        return None

    def _populate_live_expanded_detail(
        self,
        cust_id: int,
        *,
        entries: list[dict] | None = None,
    ) -> None:
        if not hasattr(self, "live_session_view"):
            return
        _, notes, pref = self._fetch_driver_notes_meta(cust_id)
        row = self._fetch_driver_detail_row(cust_id)
        entry = self._live_entry_for_cust_id(cust_id, entries)
        safety = entry.get("safety") if entry else None
        safety_trend = entry.get("safety_trend") if entry else None
        together_races = (entry or {}).get("together_races")
        head_to_head = (entry or {}).get("head_to_head")
        together_line = format_shared_races_label(together_races)

        if row:
            detail = DriverDetailRow.from_sql_row(row)
            last_seen_fmt = format_last_seen(detail.last_seen_at)
            tz_label = display_timezone_abbrev()
            if self._streamer_mode:
                meta_text = streamer_detail_meta(
                    last_seen_fmt=last_seen_fmt, tz_label=tz_label
                )
            else:
                meta_text = (
                    f"ID {cust_id}  ·  Last raced {last_seen_fmt} {tz_label}"
                )
            if together_line:
                meta_text = f"{meta_text}\n{together_line}"
            if head_to_head is not None:
                h2h_line = format_head_to_head_record(*head_to_head)
                if h2h_line != "—":
                    meta_text = f"{meta_text}\n{h2h_line}"
            recent = fetch_recent_races_by_cust_ids(self._db_conn, [cust_id], limit=5)
            trend = compute_safety_trend(detail.safety, recent.get(cust_id, []))
            safety = detail.safety
            safety_trend = trend
            self.live_session_view.populate_expanded_detail(
                cust_id,
                meta_text=meta_text,
                notes=notes,
                pref=pref,
                series=detail.last_series,
                avg_finish=detail.avg_fin,
                races=detail.total_races,
                last_irating=detail.last_ir,
                avg_pos_delta=detail.avg_pos_delta,
                dnfs=detail.dnf_total,
                dnf_breakdown=detail.dnf_breakdown,
                safety=safety,
                safety_trend=safety_trend,
                together_races=together_races,
                head_to_head=head_to_head,
            )
            return

        name = (
            (entry or {}).get("name")
            or self.active_driver_names.get(cust_id, f"Driver {cust_id}")
        )
        if self._streamer_mode and entry:
            safety_obj = safety if isinstance(safety, SafetyIndex) else None
            name = self._streamer_session_display_name(cust_id, safety_obj)
        meta_text = (
            f"ID {cust_id}  ·  Not in your book yet — notes save after the race starts."
            if not self._streamer_mode
            else "New to your book — notes save after the race starts."
        )
        if together_line:
            meta_text = f"{meta_text}\n{together_line}"
        if head_to_head is not None:
            h2h_line = format_head_to_head_record(*head_to_head)
            if h2h_line != "—":
                meta_text = f"{meta_text}\n{h2h_line}"
        self.live_session_view.populate_expanded_detail(
            cust_id,
            meta_text=meta_text,
            notes=notes,
            pref=pref,
            series=None,
            avg_finish=None,
            races=int((entry or {}).get("total_races") or 0),
            last_irating=(entry or {}).get("last_ir"),
            avg_pos_delta=(entry or {}).get("avg_pos_delta"),
            dnfs=int((entry or {}).get("dnf_total") or 0),
            dnf_breakdown="",
            safety=safety if isinstance(safety, SafetyIndex) else empty_safety(),
            safety_trend=safety_trend if isinstance(safety_trend, SafetyTrend) else None,
            together_races=together_races,
            head_to_head=head_to_head,
        )

    def _on_live_expand_save_requested(self, cust_id: int, notes_text: str) -> None:
        message = self._save_notes_for_cust_id(cust_id, notes_text, quiet=True)
        self.live_session_view.show_expand_saved(cust_id, message)
        self._refresh_live_session_view()

    def _on_live_expand_preference_requested(self, cust_id: int, pref) -> None:
        self._set_preference_for_cust_id(cust_id, pref)
        self.live_session_view.update_expanded_preference(cust_id, pref)
        self._refresh_live_session_view()

    def _save_notes_for_cust_id(
        self,
        cust_id: int,
        notes_text: str,
        *,
        quiet: bool = False,
    ) -> str:
        cursor = self._db_conn.cursor()
        cursor.execute(
            "UPDATE drivers SET notes = ? WHERE cust_id = ?",
            (notes_text, cust_id),
        )
        if cursor.rowcount == 0:
            return "Driver not in book yet"
        self._db_conn.commit()
        self._set_note_indicator(cust_id, bool(notes_text.strip()))
        if self._broadcast_controller is not None:
            self._broadcast_controller._push_database_snapshot(broadcast=True)
        if self._using_broadcast_db:
            synced = self._sync_driver_patch_to_broadcaster(cust_id, notes=notes_text)
            if not quiet:
                if synced:
                    QMessageBox.information(
                        self,
                        "Saved",
                        "Note saved and synced to the broadcaster.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Saved on this device only",
                        "Note saved here but could not reach the broadcaster to sync.",
                    )
                return "Saved"
            if synced:
                return "Saved and synced"
            return "Saved on this device only"
        if not quiet:
            QMessageBox.information(self, "Saved", "Driver notebook updated successfully.")
        return "Saved"

    def _set_preference_for_cust_id(self, cust_id: int, pref: int | None) -> None:
        cursor = self._db_conn.cursor()
        cursor.execute(
            "UPDATE drivers SET race_preference = ? WHERE cust_id = ?",
            (pref, cust_id),
        )
        if cursor.rowcount == 0:
            return
        self._db_conn.commit()
        if self.selected_cust_id == cust_id:
            self._update_preference_buttons(pref)
        if self._broadcast_controller is not None:
            self._broadcast_controller._push_database_snapshot(broadcast=True)
        if self._using_broadcast_db:
            self._sync_driver_patch_to_broadcaster(cust_id, race_preference=pref)

        row_idx = self._row_for_cust_id(cust_id)
        if row_idx is not None:
            name_item = self.table.item(row_idx, COL_NAME)
            if name_item is not None:
                name_item.setData(PREF_DATA_ROLE, pref)
            refresh_driver_table_row(self.table, row_idx)

    def _set_detail_field(self, key: str, value) -> None:
        label = self._detail_fields.get(key)
        if label is None:
            return
        text = display_val(value)
        label.setText(text)
        if key in ("series", "dnf_breakdown"):
            label.setToolTip(text if text != "—" else "")
            label.updateGeometry()

    def _clear_driver_details(self) -> None:
        self.driver_name_label.clear()
        self.driver_meta_label.clear()
        self._update_driver_pref_badge(None)
        for label in self._detail_fields.values():
            label.setText("—")
        if hasattr(self, "safety_index_panel"):
            self.safety_index_panel.update_safety(empty_safety())

    def _fetch_driver_detail_row(self, cust_id: int) -> tuple | None:
        cursor = self._db_conn.cursor()
        # driver_detail_sql uses cust_id twice (agg CTE + final WHERE)
        cursor.execute(driver_detail_sql(), (cust_id, cust_id))
        return cursor.fetchone()

    def _populate_driver_details(self, cust_id: int) -> None:
        row = self._fetch_driver_detail_row(cust_id)
        if not row:
            return

        detail = DriverDetailRow.from_sql_row(row)
        last_seen_fmt = format_last_seen(detail.last_seen_at)
        tz_label = display_timezone_abbrev()
        breakdown = detail.dnf_breakdown

        if self._streamer_mode:
            self.driver_name_label.setText(
                self._streamer_session_display_name(cust_id, detail.safety)
            )
            self.driver_meta_label.setText(
                streamer_detail_meta(last_seen_fmt=last_seen_fmt, tz_label=tz_label)
            )
        else:
            self.driver_name_label.setText(detail.name or "—")
            self.driver_meta_label.setText(
                f"ID {cust_id}  ·  Last raced {last_seen_fmt} {tz_label}"
            )
        self._set_detail_field("series", detail.last_series)
        self._set_detail_field("avg_finish", detail.avg_fin)
        self._set_detail_field("avg_incidents", detail.avg_inc)
        self._set_detail_field("races", detail.total_races)
        self._set_detail_field("last_irating", detail.last_ir)
        self._set_detail_field("last_sr", detail.last_sr)
        self._set_detail_field("avg_pos_delta", detail.avg_pos_delta)
        self._set_detail_field("dnfs", detail.dnf_total)
        self._set_detail_field("dnf_breakdown", breakdown if breakdown else None)
        recent = fetch_recent_races_by_cust_ids(
            self._db_conn, [cust_id], limit=5
        )
        trend = compute_safety_trend(detail.safety, recent.get(cust_id, []))
        self.safety_index_panel.update_safety(detail.safety, trend)
        _, _, pref = self._fetch_driver_notes_meta(cust_id)
        self._update_driver_pref_badge(pref, risky=detail.safety.risky)

    def _set_driver_panel_enabled(self, enabled: bool) -> None:
        self._empty_state_card.setVisible(not enabled)
        self._driver_header_widget.setVisible(enabled)
        self._pref_row_widget.setVisible(enabled)
        self.driver_detail_scroll.setVisible(enabled)
        self._notes_group.setVisible(enabled)
        self.btn_save_notes.setVisible(enabled)
        self.notes_edit.setEnabled(enabled)
        self.btn_pref_like.setEnabled(enabled)
        self.btn_pref_dislike.setEnabled(enabled)
        self.btn_pref_clear.setEnabled(enabled)
        self.btn_save_notes.setEnabled(enabled)

    def _update_driver_pref_badge(
        self, pref: int | None, *, risky: bool = False
    ) -> None:
        if pref == 1:
            self.driver_pref_badge.setText("LIKED")
            self._polish_property(self.driver_pref_badge, "status", "liked")
            self.driver_pref_badge.setVisible(True)
        elif pref == -1:
            self.driver_pref_badge.setText("DISLIKED")
            self._polish_property(self.driver_pref_badge, "status", "disliked")
            self.driver_pref_badge.setVisible(True)
        elif risky:
            self.driver_pref_badge.setText("RISK")
            self._polish_property(self.driver_pref_badge, "status", "risk")
            self.driver_pref_badge.setVisible(True)
        else:
            self.driver_pref_badge.clear()
            self.driver_pref_badge.setVisible(False)

    def _driver_mark_stats(self) -> tuple[int, int, int]:
        return self._filtered_mark_stats

    def _filter_meta_for_row(self, row: tuple) -> _DriverFilterMeta:
        driver = DriverTableRow.from_sql_row(row)
        name_lc = (driver.name or "").lower()
        if self._streamer_mode:
            display = self._streamer_session_display_name(
                driver.cust_id, driver.safety, compact=True
            )
        else:
            display = driver.name or ""
        return _DriverFilterMeta(
            row=row,
            name_lc=name_lc,
            display_lc=display.lower(),
            cust_id=driver.cust_id,
            race_preference=driver.race_preference,
            risky=driver.safety.risky,
        )

    def _rebuild_table_filter_index(self) -> None:
        self._table_filter_index = [
            self._filter_meta_for_row(row) for row in self._table_rows_cache
        ]
        self._refresh_head_to_head_cache()

    def _refresh_head_to_head_cache(self) -> None:
        player_cust_id = self._resolve_player_cust_id()
        if player_cust_id is None or not self._table_rows_cache:
            self._head_to_head_by_cust = {}
            return
        other_ids = [
            DriverTableRow.from_sql_row(row).cust_id
            for row in self._table_rows_cache
            if DriverTableRow.from_sql_row(row).cust_id != player_cust_id
        ]
        self._head_to_head_by_cust = fetch_head_to_head_records(
            self._db_conn,
            player_cust_id,
            other_ids,
        )

    def _schedule_search_filter(self, *_args: object) -> None:
        self._search_filter_timer.start()

    def init_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)
        self.setCentralWidget(root)

        self.broadcast_receiver_banner = QLabel("")
        self.broadcast_receiver_banner.setObjectName("broadcastReceiverBanner")
        self.broadcast_receiver_banner.setWordWrap(True)
        self.broadcast_receiver_banner.setVisible(False)
        root_layout.addWidget(self.broadcast_receiver_banner)

        header_frame = QFrame()
        header_frame.setObjectName("topHeaderBar")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(12, 8, 12, 8)
        header.setSpacing(10)

        app_title = QLabel("GridNotes")
        app_title.setObjectName("appTitle")
        header.addWidget(app_title)

        self.app_subtitle = QLabel("Driver scouting notes & race history")
        self.app_subtitle.setObjectName("appSubtitle")
        self.app_subtitle.setVisible(False)

        header.addSpacing(16)
        self.btn_start_broadcast = QPushButton("Broadcast")
        self.btn_start_broadcast.setObjectName("headerBtn")
        set_button_tooltip(self.btn_start_broadcast, TIP_BROADCAST)
        self.btn_start_broadcast.clicked.connect(self._start_broadcasting)
        header.addWidget(self.btn_start_broadcast)
        self.btn_connect_broadcast = QPushButton("Receiver")
        self.btn_connect_broadcast.setObjectName("headerBtn")
        set_button_tooltip(self.btn_connect_broadcast, TIP_RECEIVER)
        self.btn_connect_broadcast.clicked.connect(self._connect_as_broadcast_receiver)
        header.addWidget(self.btn_connect_broadcast)
        self.btn_disconnect_broadcast = QPushButton("Disconnect")
        self.btn_disconnect_broadcast.setObjectName("headerBtn")
        set_button_tooltip(self.btn_disconnect_broadcast, TIP_DISCONNECT)
        self.btn_disconnect_broadcast.clicked.connect(self._disconnect_broadcast_receiver)
        self.btn_disconnect_broadcast.setVisible(False)
        header.addWidget(self.btn_disconnect_broadcast)
        self.btn_streamer_mode = QPushButton("Streamer mode")
        self.btn_streamer_mode.setObjectName("streamerModeBtn")
        self.btn_streamer_mode.setCheckable(True)
        self.btn_streamer_mode.setChecked(self._streamer_mode)
        set_button_tooltip(self.btn_streamer_mode, TIP_STREAMER_MODE)
        self.btn_streamer_mode.clicked.connect(self._toggle_streamer_mode)
        self._polish_property(self.btn_streamer_mode, "active", self._streamer_mode)
        if self._streamer_mode:
            self.app_subtitle.setText("Streamer mode — names hidden on screen")
        header.addWidget(self.btn_streamer_mode)
        self.btn_live_mode = QPushButton("Live Mode")
        self.btn_live_mode.setObjectName("liveModeBtn")
        self.btn_live_mode.setCheckable(True)
        set_button_tooltip(self.btn_live_mode, TIP_LIVE_MODE)
        self.btn_live_mode.clicked.connect(self._toggle_live_mode)
        header.addWidget(self.btn_live_mode)

        header.addStretch()

        self.status_label = QLabel("Waiting for iRacing…")
        self.status_label.setObjectName("statusBadge")
        self._set_status(STATUS_WAITING, "Waiting for iRacing…")
        header.addWidget(self.status_label)

        root_layout.addWidget(header_frame)

        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("mainTabs")
        self.main_tabs.setDocumentMode(True)
        main_tab_bar = self.main_tabs.tabBar()
        main_tab_bar.setDrawBase(False)
        main_tab_bar.setExpanding(False)
        root_layout.addWidget(self.main_tabs, stretch=1)

        drivers_tab = QWidget()
        drivers_tab_layout = QVBoxLayout(drivers_tab)
        drivers_tab_layout.setContentsMargins(0, 0, 0, 0)
        drivers_tab_layout.setSpacing(0)

        self.view_stack = QStackedWidget()
        drivers_tab_layout.addWidget(self.view_stack)
        self.main_tabs.addTab(drivers_tab, "Drivers")

        self.import_history_tab = ImportHistoryTab()

        self.race_history_tab = RaceHistoryTab()
        self.race_history_tab.set_player_cust_id_provider(self._resolve_player_cust_id)
        self.main_tabs.addTab(self.race_history_tab, "Race History")

        self.leagues_tab = LeaguesTab(
            session_drivers_provider=self._current_session_drivers_for_leagues,
        )
        self.main_tabs.addTab(self.leagues_tab, "Leagues")

        self.main_tabs.addTab(self.import_history_tab, "Import History")

        self.settings_tab = SettingsTab()
        self.settings_tab.settings_saved.connect(self._on_settings_saved)
        self.settings_tab.theme_changed.connect(self.apply_theme)
        self.settings_tab.check_updates_requested.connect(self._check_for_app_updates)
        self.settings_tab.apply_update_requested.connect(self._apply_app_update)
        self.settings_tab.zero_race_cleanup_requested.connect(self._cleanup_zero_race_drivers)
        self.settings_tab.reset_database_requested.connect(self.reset_database)
        self.settings_tab.uninstall_requested.connect(self._uninstall_application)
        self.settings_tab.backup_export_requested.connect(self._export_database_backup)
        self.settings_tab.backup_import_requested.connect(self._import_database_backup)
        self.settings_tab.support_bundle_requested.connect(self._save_support_bundle)
        self.settings_tab.open_logs_folder_requested.connect(self._open_logs_folder)
        if iracing_data_api_auto_import_enabled():
            self.settings_tab.api_test_requested.connect(self._test_iracing_api_connection)
        self.main_tabs.addTab(self.settings_tab, "Settings")
        self._splash_pulse()

        database_panel = QWidget()
        database_layout = QVBoxLayout(database_panel)
        database_layout.setContentsMargins(0, 0, 0, 0)
        database_layout.setSpacing(0)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter = main_splitter
        database_layout.addWidget(main_splitter)

        # --- Left: drivers ---
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("driversToolbar")
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_wrapper = QFrame()
        search_wrapper.setObjectName("searchInputWrapper")
        search_inner = QHBoxLayout(search_wrapper)
        search_inner.setContentsMargins(0, 0, 4, 0)
        search_inner.setSpacing(0)
        search_icon = QLabel()
        search_icon.setObjectName("searchInputIcon")
        self._search_icon_label = search_icon
        set_label_fa_icon(search_icon, "magnifying-glass", pixel_size=14, muted=True)
        search_inner.addWidget(search_icon)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("driverSearchInput")
        self.search_input.setPlaceholderText(
            "Search by alias (#14) or real name…"
            if self._streamer_mode
            else "Search drivers by name…"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._schedule_search_filter)
        search_inner.addWidget(self.search_input, stretch=1)
        search_row.addWidget(search_wrapper, stretch=1)

        self.btn_import = QPushButton("Import Race JSON")
        self.btn_import.setObjectName("headerBtn")
        self.btn_import.setToolTip("Import iRacing event_result JSON or custom race logs")
        self.btn_import.clicked.connect(self.import_json_data)
        search_row.addWidget(self.btn_import)

        self.btn_scouting_guide = QPushButton("Scouting Guide")
        self.btn_scouting_guide.setObjectName("headerBtn")
        self.btn_scouting_guide.setToolTip(
            "Safety Index, form arrows (↗ ↘ →), liked/disliked/risk marks, and risk factors"
        )
        self.btn_scouting_guide.clicked.connect(self._show_scouting_guide)
        search_row.addWidget(self.btn_scouting_guide)
        toolbar_layout.addLayout(search_row)

        filters_bar = QFrame()
        filters_bar.setObjectName("filtersBar")
        filters_layout = QHBoxLayout(filters_bar)
        filters_layout.setContentsMargins(8, 4, 8, 4)
        filters_layout.setSpacing(10)

        filters_label = QLabel("Active filters")
        filters_label.setObjectName("statInlineLabel")
        filters_layout.addWidget(filters_label)

        self.chk_current_race_only = QCheckBox("Current session only")
        self.chk_current_race_only.setChecked(False)
        self.chk_current_race_only.setToolTip(
            "Show only drivers in the current iRacing session. "
            "During practice and qualifying this is scouting only — drivers are saved when the race starts."
        )
        self.chk_current_race_only.stateChanged.connect(self.apply_driver_filters)
        filters_layout.addWidget(self.chk_current_race_only)

        self.live_session_note = QLabel(MSG_SESSION_NOT_CONNECTED)
        self.live_session_note.setObjectName("sectionHint")
        self.live_session_note.setWordWrap(True)
        filters_layout.addWidget(self.live_session_note, stretch=1)

        toolbar_layout.addWidget(filters_bar)
        left_layout.addWidget(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(COLUMN_COUNT)
        self.table.setHorizontalHeaderLabels(DRIVER_TABLE_HEADERS)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().sectionClicked.connect(self._on_table_header_clicked)
        configure_driver_table_widget(self.table)
        self.table.setToolTip("Click a row to open scouting notes")
        self.table.itemSelectionChanged.connect(self.on_driver_selected)
        self.table.itemSelectionChanged.connect(lambda: self.table.viewport().update())
        self._configure_driver_table()
        self.table.horizontalHeader().setSortIndicator(
            self._table_sort_column, self._table_sort_order
        )
        left_layout.addWidget(self.table, stretch=1)

        self.table_pagination = TablePaginationBar()
        self.table_pagination.set_page_size(self._table_page_size)
        self.table_pagination.previous_clicked.connect(self._go_to_previous_table_page)
        self.table_pagination.next_clicked.connect(self._go_to_next_table_page)
        self.table_pagination.page_size_changed.connect(self._set_table_page_size)
        left_layout.addWidget(self.table_pagination)

        main_splitter.addWidget(left_panel)

        # --- Right: driver detail / scouting sidebar ---
        right_panel = QFrame()
        right_panel.setObjectName("scoutingSidebar")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        empty_state_card = QFrame()
        empty_state_card.setObjectName("emptyStateCard")
        empty_state_layout = QVBoxLayout(empty_state_card)
        empty_state_layout.setContentsMargins(20, 28, 20, 28)
        empty_state_layout.setSpacing(10)
        empty_state_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon = QLabel()
        empty_icon.setObjectName("emptyStateIcon")
        self._empty_icon_label = empty_icon
        set_label_fa_icon(empty_icon, "user-circle", pixel_size=32, muted=True)
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_state_layout.addWidget(empty_icon)
        self.empty_state_label = QLabel(
            "Select a driver from the list to view stats and add scouting notes."
        )
        self.empty_state_label.setObjectName("emptyState")
        self.empty_state_label.setWordWrap(True)
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_state_layout.addWidget(self.empty_state_label)
        self._empty_state_card = empty_state_card
        right_layout.addWidget(empty_state_card)

        driver_header_row = QHBoxLayout()
        driver_header_row.setSpacing(10)
        self.driver_name_label = QLabel()
        self.driver_name_label.setObjectName("driverName")
        self.driver_name_label.setWordWrap(True)
        driver_header_row.addWidget(self.driver_name_label, stretch=1)
        self.driver_pref_badge = QLabel("")
        self.driver_pref_badge.setObjectName("prefBadge")
        self.driver_pref_badge.setVisible(False)
        driver_header_row.addWidget(
            self.driver_pref_badge,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )
        self._driver_header_widget = QWidget()
        self._driver_header_widget.setLayout(driver_header_row)
        self._driver_header_widget.setVisible(False)
        right_layout.addWidget(self._driver_header_widget)

        pref_row = QHBoxLayout()
        pref_row.setSpacing(8)
        self.btn_pref_like = QPushButton("Liked")
        self.btn_pref_like.setObjectName("prefLikeBtn")
        self.btn_pref_like.setCheckable(True)
        self.btn_pref_like.setToolTip("Highlight row green in the driver list")
        self.btn_pref_like.clicked.connect(lambda: self.set_race_preference(1))
        pref_row.addWidget(self.btn_pref_like)
        self.btn_pref_dislike = QPushButton("Disliked")
        self.btn_pref_dislike.setObjectName("prefDislikeBtn")
        self.btn_pref_dislike.setCheckable(True)
        self.btn_pref_dislike.setToolTip("Highlight row red in the driver list")
        self.btn_pref_dislike.clicked.connect(lambda: self.set_race_preference(-1))
        pref_row.addWidget(self.btn_pref_dislike)
        self.btn_pref_clear = QPushButton("Clear")
        self.btn_pref_clear.setObjectName("prefClearBtn")
        self.btn_pref_clear.setToolTip("Remove like/dislike highlight")
        self.btn_pref_clear.clicked.connect(lambda: self.set_race_preference(None))
        pref_row.addWidget(self.btn_pref_clear)
        self._pref_row_widget = QWidget()
        self._pref_row_widget.setLayout(pref_row)
        self._pref_row_widget.setVisible(False)
        right_layout.addWidget(self._pref_row_widget)

        self.driver_detail_scroll = QScrollArea()
        self.driver_detail_scroll.setObjectName("driverDetailScroll")
        self.driver_detail_scroll.setWidgetResizable(True)
        self.driver_detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.driver_detail_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.driver_detail_frame = QFrame()
        self.driver_detail_frame.setStyleSheet("background: transparent;")
        detail_layout = QVBoxLayout(self.driver_detail_frame)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(4)

        self.driver_meta_label = QLabel()
        self.driver_meta_label.setObjectName("driverMeta")
        self.driver_meta_label.setWordWrap(True)
        detail_layout.addWidget(self.driver_meta_label)

        self.safety_index_panel = SafetyIndexPanel()
        self.safety_index_panel.guide_requested.connect(self._show_scouting_guide)
        detail_layout.addWidget(self.safety_index_panel)

        series_title = QLabel("Series")
        series_title.setObjectName("statLabel")
        detail_layout.addWidget(series_title)
        self._detail_fields = {}
        series_value = WrappingLabel("—")
        series_value.setObjectName("seriesValue")
        detail_layout.addWidget(series_value)
        self._detail_fields["series"] = series_value

        stats_block = QVBoxLayout()
        stats_block.setSpacing(4)
        stats_block.setContentsMargins(0, 6, 0, 0)
        for key, title in [
            ("avg_finish", "Avg finish"),
            ("avg_incidents", "Avg incidents"),
            ("races", "Races tracked"),
            ("last_irating", "Last iRating"),
            ("last_sr", "Last SR"),
            ("avg_pos_delta", "Avg +/- pos"),
            ("dnfs", "DNFs"),
            ("dnf_breakdown", "DNF breakdown"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            label = QLabel(f"{title}:")
            label.setObjectName("statInlineLabel")
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            if key == "dnf_breakdown":
                value: QLabel = WrappingLabel("—")
            else:
                value = QLabel("—")
                value.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            value.setObjectName("statValue")
            value.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
            row.addWidget(label, 0)
            row.addWidget(value, 1)
            stats_block.addLayout(row)
            self._detail_fields[key] = value
        detail_layout.addLayout(stats_block)

        self.driver_detail_scroll.setWidget(self.driver_detail_frame)
        configure_scroll_area(self.driver_detail_scroll, page_step=96)
        self.driver_detail_scroll.setVisible(False)
        right_layout.addWidget(self.driver_detail_scroll)

        notes_group = QGroupBox("Scouting Notes")
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setSpacing(10)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Add scouting notes for this driver…"
        )
        self.notes_edit.setMinimumHeight(160)
        configure_widget_scrollbars(self.notes_edit, single_step=20, page_step=100)
        notes_layout.addWidget(self.notes_edit)

        templates_label = QLabel("Note Templates")
        templates_label.setObjectName("statInlineLabel")
        notes_layout.addWidget(templates_label)

        templates_grid = QGridLayout()
        templates_grid.setHorizontalSpacing(8)
        templates_grid.setVerticalSpacing(8)
        templates_grid.setContentsMargins(0, 4, 0, 0)
        self._note_templates_grid = templates_grid
        notes_layout.addLayout(templates_grid)
        self._rebuild_note_template_buttons()

        self._notes_group = notes_group
        self._notes_group.setVisible(False)
        right_layout.addWidget(notes_group, stretch=1)

        self.btn_save_notes = QPushButton("Save Notes")
        self.btn_save_notes.setObjectName("gradientBtn")
        set_button_tooltip(
            self.btn_save_notes,
            "Save scouting notes for the selected driver (Ctrl+S / Cmd+S).",
        )
        self.btn_save_notes.clicked.connect(self.save_driver_notes)
        right_layout.addWidget(self.btn_save_notes)

        main_splitter.addWidget(right_panel)
        right_panel.setMinimumWidth(320)
        right_panel.setMaximumWidth(480)
        main_splitter.setStretchFactor(0, 7)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setSizes([1100, 380])

        self.view_stack.addWidget(database_panel)
        self._splash_pulse()

        self.live_session_view = LiveSessionView()
        self.live_session_view.driver_expand_requested.connect(
            self._on_live_driver_expand_requested
        )
        self.live_session_view.expand_save_requested.connect(
            self._on_live_expand_save_requested
        )
        self.live_session_view.expand_preference_requested.connect(
            self._on_live_expand_preference_requested
        )
        self.live_session_view.audio_spotter_changed.connect(
            self._on_audio_spotter_setting_changed
        )
        self.live_session_view.grid_walk_toggled.connect(self._on_grid_walk_toggled)
        self.live_session_view.scouting_guide_requested.connect(self._show_scouting_guide)
        self.live_session_view.set_audio_spotter_enabled(self._audio_spotter_enabled)
        if sys.platform != "win32":
            self.live_session_view.chk_audio_spotter.setEnabled(False)
        self.view_stack.addWidget(self.live_session_view)

        self.settings_tab.audio_spotter_changed.connect(
            self._on_audio_spotter_setting_changed
        )
        if sys.platform != "win32":
            self.settings_tab.chk_audio_spotter.setEnabled(False)

        self._set_live_mode(self._live_mode_active, persist=False)

        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        self._set_driver_panel_enabled(False)
        self._splash_message("Loading drivers…")
        self._splash_pulse()
        self._refresh_ui_table_now(force=True)
        self._configure_accessibility()
        self._configure_keyboard_shortcuts()
        self._apply_icons()
        self.apply_theme()

    def _apply_icons(self) -> None:
        set_button_fa_icon(self.btn_start_broadcast, "tower-broadcast", text="Broadcast")
        set_button_fa_icon(self.btn_connect_broadcast, "satellite-dish", text="Receiver")
        set_button_fa_icon(self.btn_disconnect_broadcast, "link-slash", text="Disconnect")
        set_button_fa_icon(self.btn_streamer_mode, "eye-slash", text="Streamer mode")
        set_button_fa_icon(self.btn_live_mode, "flag-checkered", text="Live Mode")
        set_button_fa_icon(self.btn_import, "file-import", text="Import Race JSON")
        set_button_fa_icon(
            self.btn_scouting_guide, "book-open", text="Scouting Guide"
        )
        set_button_fa_icon(self.btn_pref_like, "thumbs-up", text="Liked")
        set_button_fa_icon(self.btn_pref_dislike, "thumbs-down", text="Disliked")
        set_button_fa_icon(self.btn_pref_clear, "eraser", text="Clear")
        set_button_fa_icon(
            self.btn_save_notes, "floppy-disk", text="Save Notes", on_accent=True
        )
        wire_main_tabs(self.main_tabs)

    def _configure_accessibility(self) -> None:
        set_accessible(
            self.table,
            "Driver list",
            "Sortable table of drivers. Use arrow keys to move, Enter to open scouting notes.",
        )
        set_accessible(
            self.search_input,
            "Search drivers",
            "Filter the driver list by name.",
        )
        set_accessible(
            self.btn_scouting_guide,
            "Scouting guide",
            "Open reference for Safety Index, form arrows, marks, and risk factors.",
        )
        set_accessible(
            self.btn_import,
            "Import race JSON",
            "Import iRacing event result JSON or custom race logs.",
        )
        set_accessible(
            self.chk_current_race_only,
            "Current session only",
            "Show only drivers in the current iRacing session.",
        )
        set_accessible(
            self.btn_live_mode,
            "Live Mode",
            "Switch to high-contrast live session view for in-race scouting.",
        )
        set_accessible(
            self.btn_streamer_mode,
            "Streamer mode",
            "Replace driver names with aliases on screen. Database unchanged.",
        )
        set_accessible(
            self.btn_start_broadcast,
            "Broadcast",
            "Share scouting book and live iRacing session with another device on your network.",
        )
        set_accessible(
            self.btn_connect_broadcast,
            "Receiver",
            "Connect to a broadcaster and view its scouting book and live session.",
        )
        set_accessible(
            self.btn_disconnect_broadcast,
            "Disconnect receiver",
            "Stop receiving and return to your local scouting book.",
        )
        set_accessible(self.status_label, "iRacing connection status")
        set_accessible(
            self.notes_edit,
            "Scouting notes",
            "Notes for the selected driver.",
        )
        set_accessible(self.btn_pref_like, "Liked", "Mark that you liked racing with this driver.")
        set_accessible(
            self.btn_pref_dislike,
            "Disliked",
            "Mark that you did not like racing with this driver.",
        )
        set_accessible(self.btn_pref_clear, "Clear preference")
        set_accessible(self.btn_save_notes, "Save notes")
        set_accessible(self.main_tabs, "Main sections", "Drivers list and application settings.")

    def _configure_keyboard_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, self.search_input.setFocus)
        QShortcut(QKeySequence("Ctrl+L"), self, self._toggle_live_mode)
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self.save_driver_notes)

    def apply_theme(self, theme_id: str | None = None) -> None:
        """Apply light/dark stylesheet and refresh theme-dependent widgets."""
        tid = normalize_theme_id(theme_id) if theme_id is not None else get_theme_id()
        app = QApplication.instance()
        if app is not None:
            apply_app_theme(app, tid)
        self._apply_icons()
        configure_driver_table_theme(tid)
        refresh_widget_tree(self)
        if hasattr(self, "table"):
            refresh_driver_table_icon_colors(self.table)
            self.table.viewport().update()
        if hasattr(self, "safety_index_panel"):
            self.safety_index_panel.refresh_theme()
        if hasattr(self, "live_session_view"):
            self.live_session_view.update()
        if hasattr(self, "settings_tab"):
            self.settings_tab.refresh_theme()
        if hasattr(self, "leagues_tab"):
            self.leagues_tab._apply_icons()
        if hasattr(self, "import_history_tab"):
            self.import_history_tab.refresh_icons()
        if hasattr(self, "race_history_tab"):
            self.race_history_tab.refresh_icons()
        if hasattr(self, "table_pagination"):
            self.table_pagination.refresh_icons()
        self._refresh_label_icons()

    def _hidden_driver_name_lc(self) -> str:
        return (get_setting("ignore_driver_name", "") or "").strip().lower()

    def _refresh_label_icons(self) -> None:
        for label, name, size, muted in (
            (getattr(self, "_search_icon_label", None), "magnifying-glass", 14, True),
            (getattr(self, "_empty_icon_label", None), "user-circle", 32, True),
        ):
            if label is not None:
                set_label_fa_icon(label, name, pixel_size=size, muted=muted)

    def _run_data_retention_purge(self, *, show_status: bool = False, refresh: bool = True) -> int:
        retention = get_setting(SETTING_KEY, DEFAULT_RETENTION) or DEFAULT_RETENTION
        deleted = purge_expired_race_results(self._db_conn, retention)
        if deleted:
            self._db_conn.commit()
            if self.selected_cust_id is not None:
                self._populate_driver_details(self.selected_cust_id)
            if refresh and hasattr(self, "table"):
                self.refresh_ui_table()
        if show_status and hasattr(self, "settings_tab"):
            self.settings_tab.show_purge_result(deleted)
            if deleted:
                self.import_history_tab.refresh()
        return deleted

    def _on_settings_saved(self) -> None:
        self._rebuild_note_template_buttons()
        self._refresh_head_to_head_cache()
        self.apply_driver_filters()
        deleted = self._run_data_retention_purge(show_status=True)
        if self.selected_cust_id is not None:
            self._populate_driver_details(self.selected_cust_id)
        if deleted and self.selected_cust_id is not None:
            row = self._row_for_cust_id(self.selected_cust_id)
            if row is None:
                self.selected_cust_id = None
                self._clear_driver_details()
                self._set_driver_panel_enabled(False)
                self.table.clearSelection()

    def _cleanup_zero_race_drivers(self) -> None:
        pending = count_zero_race_drivers(self._db_conn)
        if pending == 0:
            QMessageBox.information(
                self,
                "Nothing To Remove",
                "There are no drivers with zero races in the database.",
            )
            self.settings_tab.show_zero_race_cleanup_result(0)
            return

        res = QMessageBox.question(
            self,
            "Remove Zero-Race Drivers?",
            f"Remove {pending} driver(s) who have no imported race results?\n\n"
            "Their scouting notes and like/dislike preferences will also be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        deleted = purge_zero_race_drivers(self._db_conn)
        self._db_conn.commit()

        if self.selected_cust_id is not None:
            row = self._row_for_cust_id(self.selected_cust_id)
            if row is None:
                self.selected_cust_id = None
                self._clear_driver_details()
                self._set_driver_panel_enabled(False)
                self.table.clearSelection()

        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)
        self.settings_tab.show_zero_race_cleanup_result(deleted)

    def apply_driver_filters(self, *_):
        self._recompute_filtered_table_rows(reset_page=True)
        self._render_table_page()

    def _sort_filtered_table_rows(self) -> None:
        if not self._filtered_table_rows:
            return
        reverse = self._table_sort_order == Qt.SortOrder.DescendingOrder
        column = self._table_sort_column
        keyed = [
            (
                table_row_sort_key(
                    row,
                    column,
                    head_to_head=self._head_to_head_by_cust.get(
                        DriverTableRow.from_sql_row(row).cust_id
                    ),
                ),
                row,
            )
            for row in self._filtered_table_rows
        ]
        keyed.sort(reverse=reverse)
        self._filtered_table_rows = [row for _, row in keyed]

    def _table_page_count(self) -> int:
        total = len(self._filtered_table_rows)
        if total <= 0:
            return 1
        return (total + self._table_page_size - 1) // self._table_page_size

    def _recompute_filtered_table_rows(self, *, reset_page: bool = False) -> None:
        if reset_page:
            self._table_page = 0
        q = (self.search_input.text() or "").strip().lower()
        ignore_name = self._hidden_driver_name_lc()
        current_only = (
            hasattr(self, "chk_current_race_only")
            and self.chk_current_race_only.isEnabled()
            and self.chk_current_race_only.isChecked()
        )
        active_ids = self.active_cust_ids

        filtered: list[tuple] = []
        likes = dislikes = risks = 0
        for meta in self._table_filter_index:
            if q and q not in meta.name_lc and q not in meta.display_lc:
                continue
            if ignore_name and meta.name_lc == ignore_name:
                continue
            if current_only and meta.cust_id not in active_ids:
                continue
            filtered.append(meta.row)
            if meta.race_preference == 1:
                likes += 1
            elif meta.race_preference == -1:
                dislikes += 1
            if meta.risky:
                risks += 1

        self._filtered_table_rows = filtered
        self._filtered_mark_stats = (likes, dislikes, risks)
        self._sort_filtered_table_rows()
        page_count = self._table_page_count()
        if self._table_page >= page_count:
            self._table_page = max(0, page_count - 1)

    def _update_table_pagination_bar(self) -> None:
        total = len(self._filtered_table_rows)
        likes, dislikes, risks = self._driver_mark_stats()
        if total <= 0:
            self.table_pagination.update_state(
                page=0,
                page_count=1,
                total=0,
                start=0,
                end=0,
                likes=likes,
                dislikes=dislikes,
                risks=risks,
            )
            return
        start_idx = self._table_page * self._table_page_size
        end_idx = min(start_idx + self._table_page_size, total)
        self.table_pagination.update_state(
            page=self._table_page,
            page_count=self._table_page_count(),
            total=total,
            start=start_idx + 1,
            end=end_idx,
            likes=likes,
            dislikes=dislikes,
            risks=risks,
        )

    def _go_to_previous_table_page(self) -> None:
        if self._table_page <= 0:
            return
        self._table_page -= 1
        self._render_table_page()

    def _go_to_next_table_page(self) -> None:
        if self._table_page >= self._table_page_count() - 1:
            return
        self._table_page += 1
        self._render_table_page()

    def _set_table_page_size(self, page_size: int) -> None:
        if page_size <= 0 or page_size == self._table_page_size:
            return
        self._table_page_size = page_size
        self._table_page = 0
        self._render_table_page()

    def _on_table_header_clicked(self, logical_index: int) -> None:
        if logical_index == COL_CUST_ID:
            return
        if self._table_sort_column == logical_index:
            self._table_sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._table_sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._table_sort_column = logical_index
            self._table_sort_order = Qt.SortOrder.AscendingOrder
        self.table.horizontalHeader().setSortIndicator(
            self._table_sort_column, self._table_sort_order
        )
        self._sort_filtered_table_rows()
        self._render_table_page()

    def _merge_rows_into_table_cache(self, rows: list[tuple]) -> None:
        if not rows:
            return
        index_by_id = {
            DriverTableRow.from_sql_row(row).cust_id: idx
            for idx, row in enumerate(self._table_rows_cache)
        }
        for row in rows:
            cust_id = DriverTableRow.from_sql_row(row).cust_id
            if cust_id in index_by_id:
                self._table_rows_cache[index_by_id[cust_id]] = row
            else:
                index_by_id[cust_id] = len(self._table_rows_cache)
                self._table_rows_cache.append(row)
        self._rebuild_table_filter_index()

    def reset_database(self):
        res = QMessageBox.question(
            self,
            "Reset Database?",
            "This will permanently delete ALL drivers, notes, and race results from the local database.\n\n"
            "Are you sure you want to reset?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        conn = self._db_conn
        cursor = conn.cursor()
        cursor.execute("DELETE FROM race_results")
        cursor.execute("DELETE FROM drivers")
        conn.commit()

        self.current_subsession_id = 0
        self.selected_cust_id = None
        self.active_cust_ids = set()
        self.active_driver_names = {}
        self.active_driver_car_numbers = {}
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        self.notes_edit.clear()
        self._clear_driver_details()
        self._set_driver_panel_enabled(False)
        self.table.clearSelection()
        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)

        QMessageBox.information(self, "Database Reset", "Database cleared successfully.")

    def start_sdk_worker(self):
        if self._shutting_down:
            return
        logger.info("Starting iRacing SDK worker…")

        worker = IRacingWorker()
        if not getattr(worker, "available", False):
            reason = getattr(worker, "unavailable_reason", "") or "pyirsdk unavailable"
            logger.warning("SDK worker not available: %s", reason)
            self._set_status(STATUS_OFFLINE, f"Offline — {reason}", user_error=True)
            self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
            self.worker = None
            return

        logger.info("SDK worker available; starting background thread")
        self.worker = worker
        self.worker.connection_changed.connect(self.handle_sdk_connection)
        self.worker.drivers_updated.connect(self.handle_sdk_update)
        self.worker.spotter_car_behind.connect(self._on_spotter_car_behind)
        self.worker.grid_updated.connect(self._on_grid_updated)
        self.worker.start()
        self._sync_audio_spotter_worker()
        self._sync_grid_walk_worker()
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)

    def _session_status_label(self, driver_count: int) -> str:
        kind_label = session_kind_label(self.current_session_kind)
        if is_race_session(self.current_session_kind):
            if self.current_subsession_id:
                return f"Live — session #{self.current_subsession_id} · {driver_count} drivers"
            return f"Live — race · {driver_count} drivers"
        if self.current_subsession_id:
            return f"Live — session #{self.current_subsession_id} · {kind_label} · {driver_count} drivers (scouting only)"
        return f"Live — {kind_label} · {driver_count} drivers (scouting only)"

    def _session_filter_hint(self) -> str:
        if is_race_session(self.current_session_kind):
            return ""
        kind_label = session_kind_label(self.current_session_kind)
        return (
            f"{kind_label} — live scouting enabled. "
            "Drivers are added to your book when the race starts."
        )

    def _test_iracing_api_connection(self, access_token: str) -> None:
        if not iracing_data_api_auto_import_enabled():
            return
        if self._api_test_worker is not None and self._api_test_worker.isRunning():
            return

        from ..iracing.iracing_data_api_config import get_access_token

        token = access_token.strip() or get_access_token()
        logger.info("User requested iRacing Data API connection test")
        self.settings_tab.set_api_test_busy(True)
        self._api_test_worker = ApiConnectionTestWorker(
            access_token=token,
            parent=self,
        )
        self._api_test_worker.finished.connect(self._on_api_test_finished)
        self._api_test_worker.start()

    def _on_api_test_finished(self, ok: bool, message: str) -> None:
        self.settings_tab.set_api_test_busy(False)
        self.settings_tab.show_api_test_result(ok, message)

    def _check_for_app_updates_on_startup(self) -> None:
        self._check_for_app_updates(on_startup=True)

    def _check_for_app_updates(self, *, on_startup: bool = False) -> None:
        if self._update_check_worker is not None and self._update_check_worker.isRunning():
            return
        self._update_check_on_startup = on_startup
        if on_startup:
            logger.info("Automatic application update check on startup")
        else:
            logger.info("User requested application update check")
            self.settings_tab.set_update_check_busy(True)
        self._update_check_worker = UpdateCheckWorker(parent=self)
        self._update_check_worker.finished.connect(self._on_update_check_finished)
        self._update_check_worker.start()

    def _on_update_check_finished(self, result: UpdateCheckResult) -> None:
        if self._update_check_on_startup:
            self._update_check_on_startup = False
            self._handle_startup_update_check(result)
            return
        self.settings_tab.set_update_check_busy(False)
        self.settings_tab.show_update_check_result(result)

    def _handle_startup_update_check(self, result: UpdateCheckResult) -> None:
        if not result.update_available:
            logger.info("Startup update check: already up to date")
            return

        self.settings_tab.show_update_check_result(result)
        if not self._confirm_update(result):
            logger.info("User declined startup update")
            return

        self._apply_app_update(skip_confirm=True)

    def _confirm_update(self, result: UpdateCheckResult) -> bool:
        version_label = result.latest_version or "newer"

        if result.can_apply_in_place:
            from ..ui.update_confirm_dialog import UpdateConfirmDialog

            dialog = UpdateConfirmDialog(
                self,
                version=version_label,
                release_notes=result.release_notes,
                portable=result.apply_method in ("portable", "frozen", "installer", "git"),
                requires_windows_permission=result.requires_windows_permission,
            )
            return dialog.exec() == dialog.DialogCode.Accepted

        if is_frozen_build():
            prompt = (
                f"Version {version_label.lstrip('v')} of GridNotes is available.\n\n"
                "Open the download page to get the latest installer?"
            )
        else:
            prompt = (
                f"Version {version_label.lstrip('v')} of GridNotes is available.\n\n"
                "Open the download page for update instructions?"
            )
        confirm = QMessageBox.question(
            self,
            "Update available",
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return confirm == QMessageBox.StandardButton.Yes

    def _apply_app_update(self, *, skip_confirm: bool = False) -> None:
        result = self.settings_tab.last_update_check()
        if result is None:
            QMessageBox.information(
                self,
                "Check For Updates First",
                "Click “Check for updates” before applying an update.",
            )
            return

        if result.can_apply_in_place:
            if not skip_confirm and not self._confirm_update(result):
                return
            if self._apply_update_worker is not None and self._apply_update_worker.isRunning():
                return
            logger.info("Applying application update (%s)", result.apply_method or "unknown")
            self.settings_tab.set_apply_update_busy(True)
            self._open_update_progress(
                result.latest_version,
                requires_windows_permission=result.requires_windows_permission,
            )
            self._apply_update_worker = ApplyAppUpdateWorker(
                result,
                wait_pid=os.getpid(),
                parent=self,
            )
            self._apply_update_worker.progress.connect(
                self._on_apply_update_progress,
                Qt.ConnectionType.QueuedConnection,
            )
            self._apply_update_worker.finished.connect(self._on_apply_update_finished)
            self._apply_update_worker.start()
            return

        # Only reached when in-place update is not available (button: Get latest version).
        if result.update_available or result.download_url:
            url = QUrl(result.download_url or GITHUB_RELEASES_PAGE)
            if not QDesktopServices.openUrl(url):
                QMessageBox.warning(
                    self,
                    "Could Not Open Browser",
                    f"Open this link manually:\n\n{url.toString()}",
                )
            return

        QMessageBox.information(
            self,
            "No Update Ready",
            "No update is available to apply right now.",
        )

    def _export_database_backup(self) -> None:
        from datetime import date

        from ..data.backup import export_database_backup

        default_name = f"GridNotes-backup-{date.today().isoformat()}.db"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Back up GridNotes database",
            default_name,
            "SQLite database (*.db);;All files (*)",
        )
        if not path:
            return
        ok, message = export_database_backup(
            Path(path),
            connection=getattr(self, "_db_conn", None),
        )
        self.settings_tab.show_backup_result(ok, message)
        if not ok:
            log_user_error(message, context="database backup")

    def _import_database_backup(self) -> None:
        from ..data.backup import import_database_backup

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore GridNotes database",
            "",
            "SQLite database (*.db);;All files (*)",
        )
        if not path:
            return
        confirm = QMessageBox.warning(
            self,
            "Restore backup?",
            "This replaces your current notes and race history with the backup file.\n\n"
            "A copy of your current database is saved first.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        close_sqlite_connection(getattr(self, "_db_conn", None))
        ok, message = import_database_backup(Path(path))
        self._db_conn = connect_db()
        init_db()
        self.refresh_ui_table()
        self.settings_tab.show_backup_result(ok, message)
        if ok:
            self.import_history_tab.refresh()
        if not ok:
            log_user_error(message, context="database restore")

    def _save_support_bundle(self) -> None:
        from datetime import date

        from ..services.support_bundle import create_support_bundle

        default_name = f"GridNotes-support-{date.today().isoformat()}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save support file",
            default_name,
            "Zip archive (*.zip);;All files (*)",
        )
        if not path:
            return
        dest = Path(path)
        if dest.suffix.lower() != ".zip":
            dest = dest.with_suffix(".zip")
        ok, message = create_support_bundle(dest)
        self.settings_tab.show_support_result(ok, message)
        if not ok:
            log_user_error(message, context="support bundle")

    def _open_logs_folder(self) -> None:
        from ..services.support_bundle import open_logs_folder

        ok, message = open_logs_folder()
        self.settings_tab.show_support_result(ok, message)

    def _open_update_progress(
        self,
        target_version: str | None,
        *,
        requires_windows_permission: bool = False,
    ) -> None:
        from ..ui.update_progress_dialog import UpdateProgressDialog

        self._close_update_progress()
        dialog = UpdateProgressDialog(self)
        dialog.begin(
            target_version=target_version,
            requires_windows_permission=requires_windows_permission,
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._update_progress_dialog = dialog
        self.setEnabled(False)

    def _close_update_progress(self) -> None:
        if self._update_exit_timer is not None:
            self._update_exit_timer.stop()
            self._update_exit_timer = None
        if self._update_progress_dialog is not None:
            self._update_progress_dialog.close()
            self._update_progress_dialog = None
        self.setEnabled(True)

    def _on_apply_update_progress(self, message: str, percent: int) -> None:
        if self._update_progress_dialog is not None:
            self._update_progress_dialog.set_progress(message, percent)

    def _exit_for_background_update(self) -> None:
        logger.info("Portable update scheduled; exiting for background install")
        self._release_resources_before_exit()
        os._exit(0)

    def _on_apply_update_finished(self, ok: bool, message: str, restart: bool) -> None:
        self.settings_tab.set_apply_update_busy(False)
        if not ok:
            self._close_update_progress()
            log_user_error(message, context="application update")
            self.settings_tab.show_apply_update_result(False, message)
            QMessageBox.warning(self, "Update did not finish", message)
            return

        self.settings_tab.show_apply_update_result(True, message)
        if restart:
            if self._update_progress_dialog is not None:
                self._update_progress_dialog.mark_complete("Restarting GridNotes…")
            logger.info("Update applied; restarting application")
            restart_application()
            return

        result = self.settings_tab.last_update_check()
        requires_permission = (
            result.requires_windows_permission if result is not None else False
        )
        if self._update_progress_dialog is not None:
            self._update_progress_dialog.begin_closing_for_update(
                requires_windows_permission=requires_permission
            )
        delay_ms = 3500 if requires_permission else 1800
        self._update_exit_timer = QTimer(self)
        self._update_exit_timer.setSingleShot(True)
        self._update_exit_timer.timeout.connect(self._exit_for_background_update)
        self._update_exit_timer.start(delay_ms)

    def _stop_background_workers(self) -> None:
        """Stop threads that may still hold the database or network open."""
        if self._import_worker is not None and self._import_worker.isRunning():
            self._import_worker.wait(30000)
        if self._api_fetch_worker is not None and self._api_fetch_worker.isRunning():
            self._api_fetch_worker.wait(60000)
        if self._api_test_worker is not None and self._api_test_worker.isRunning():
            self._api_test_worker.wait(10000)
        if self._update_check_worker is not None and self._update_check_worker.isRunning():
            self._update_check_worker.wait(10000)
        if self._apply_update_worker is not None and self._apply_update_worker.isRunning():
            self._apply_update_worker.wait(120000)
        self._stop_sdk_worker()
        if hasattr(self, "_audio_spotter"):
            self._audio_spotter.stop()

    def _release_resources_before_exit(self) -> None:
        """Close DB and log files so uninstall/update can remove user or app data."""
        self._stop_background_workers()
        if hasattr(self, "_db_conn"):
            close_sqlite_connection(self._db_conn)
            del self._db_conn
        try:
            from ..services.log_config import shutdown_logging

            shutdown_logging()
        except Exception:
            pass

    def _uninstall_application(self, remove_user_data: bool) -> None:
        from ..installer.uninstall import perform_uninstall, resolve_install_root

        install_root = resolve_install_root()
        if hasattr(self.settings_tab, "btn_uninstall"):
            self.settings_tab.btn_uninstall.setEnabled(False)

        if remove_user_data:
            self._release_resources_before_exit()
        elif hasattr(self, "_db_conn"):
            close_sqlite_connection(self._db_conn)
            del self._db_conn

        result = perform_uninstall(
            install_root=install_root,
            remove_user_data=remove_user_data,
            defer_user_data_removal=remove_user_data,
            wait_pid=os.getpid(),
        )
        self.settings_tab.show_uninstall_result(result.ok, result.summary())

        if result.ok:
            summary = result.summary()
            if result.install_removal_deferred:
                summary += (
                    "\n\nClick OK to finish. Your install folder "
                    "(for example D:\\GridNotes) will be deleted when GridNotes closes."
                )
            if result.user_data_removal_deferred:
                summary += (
                    "\n\nClick OK to finish. Your notes and database will be "
                    "removed when GridNotes closes."
                )
            QMessageBox.information(self, "Uninstall", summary)
            os._exit(0)

        log_user_error(result.summary(), context="uninstall")
        QMessageBox.warning(self, "Uninstall", result.summary())
        if hasattr(self.settings_tab, "btn_uninstall"):
            self.settings_tab.btn_uninstall.setEnabled(True)
        self._db_conn = connect_db()

    def _maybe_auto_fetch_race_results(self, subsession_id: int) -> None:
        if not iracing_data_api_auto_import_enabled():
            return
        if not is_auto_fetch_enabled():
            return
        if subsession_id <= 0:
            return
        if subsession_id in self._api_fetched_subsession_ids:
            return
        if subsession_id in self._api_fetch_queue:
            return
        self._api_fetch_queue.append(subsession_id)
        self._process_api_fetch_queue()

    def _process_api_fetch_queue(self) -> None:
        if self._api_fetch_worker is not None and self._api_fetch_worker.isRunning():
            return
        if not self._api_fetch_queue:
            return

        subsession_id = self._api_fetch_queue.pop(0)
        self._api_fetch_worker = SubsessionFetchWorker(subsession_id, parent=self)
        self._api_fetch_worker.status.connect(self._on_api_fetch_status)
        self._api_fetch_worker.finished.connect(self._on_api_fetch_finished)
        self._api_fetch_worker.failed.connect(self._on_api_fetch_failed)
        self._api_fetch_worker.start()

    def _on_api_fetch_status(self, message: str) -> None:
        self._set_status(STATUS_CONNECTED, message)
        if hasattr(self, "settings_tab"):
            self.settings_tab.show_api_fetch_status(message)

    def _on_api_fetch_finished(self, result: SubsessionFetchResult) -> None:
        self._api_fetched_subsession_ids.add(result.subsession_id)

        self._refresh_table_after_import(
            affected_cust_ids=result.affected_cust_ids,
            retention_deleted=result.retention_deleted,
        )

        parts: list[str] = []
        if result.results_imported:
            parts.append(f"{result.results_imported} new")
        if result.results_updated:
            parts.append(f"{result.results_updated} updated")
        if result.results_skipped:
            parts.append(f"{result.results_skipped} skipped")

        summary = ", ".join(parts) if parts else "no changes"
        message = (
            f"Imported session #{result.subsession_id} from iRacing API ({summary})."
        )
        self._set_status(STATUS_CONNECTED, message)
        if hasattr(self, "settings_tab"):
            self.settings_tab.show_api_fetch_status(message)
            self.import_history_tab.refresh()

        self._api_fetch_worker = None
        self._process_api_fetch_queue()

    def _on_api_fetch_failed(self, subsession_id: int, message: str) -> None:
        fail_msg = f"Could not fetch session #{subsession_id}: {message}"
        if self._sdk_connected:
            self._set_status(STATUS_CONNECTED, fail_msg, user_error=True)
        else:
            self._set_status(STATUS_WAITING, fail_msg, user_error=True)
        if hasattr(self, "settings_tab"):
            self.settings_tab.show_api_fetch_status(fail_msg, error=True)

        self._api_fetch_worker = None
        self._process_api_fetch_queue()

    def handle_sdk_connection(self, connected: bool, subsession_id: int, session_kind: str) -> None:
        self._sdk_connected = connected
        if connected:
            self.current_session_kind = session_kind
            self.current_subsession_id = subsession_id
            driver_count = len(self.active_cust_ids)
            self._set_status(
                STATUS_CONNECTED,
                self._session_status_label(driver_count) if driver_count else f"Live — {session_kind_label(session_kind)}",
            )
            if is_live_scouting_session(session_kind):
                self._update_live_session_filter(active=True, hint=self._session_filter_hint())
            else:
                self.active_cust_ids = set()
                self.active_driver_names = {}
                self.active_driver_car_numbers = {}
                self._update_live_session_filter(active=False, hint="Unsupported session type for live scouting.")
            self._refresh_live_session_view()
            return

        if self._tracked_race_subsession_id:
            self._maybe_auto_fetch_race_results(self._tracked_race_subsession_id)
        self._tracked_race_subsession_id = 0

        self.current_subsession_id = 0
        self.current_session_kind = ""
        self.current_session_context = {}
        self.active_cust_ids = set()
        self.active_driver_names = {}
        self.active_driver_car_numbers = {}
        self._latest_grid_slots = []
        if hasattr(self, "live_session_view"):
            self.live_session_view.collapse_expanded()
        self._set_status(STATUS_WAITING, "Waiting for iRacing…")
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        if hasattr(self, "chk_current_race_only"):
            self.chk_current_race_only.setChecked(False)
        self._refresh_live_session_view()

    def handle_sdk_update(
        self,
        active_drivers,
        subsession_id,
        session_kind,
        session_context=None,
    ):
        prev_subsession = self.current_subsession_id
        prev_kind = self.current_session_kind

        self.current_subsession_id = subsession_id
        self.current_session_kind = session_kind
        if isinstance(session_context, dict):
            self.current_session_context = session_context
            player_from_ctx = session_context.get("player_cust_id")
            if player_from_ctx is not None:
                try:
                    self._remember_player_cust_id(int(player_from_ctx))
                except (TypeError, ValueError):
                    pass

        if (
            is_race_session(prev_kind)
            and prev_subsession
            and prev_subsession != subsession_id
        ):
            self._maybe_auto_fetch_race_results(prev_subsession)

        if is_race_session(session_kind) and subsession_id:
            self._tracked_race_subsession_id = subsession_id
        elif not is_race_session(session_kind):
            self._tracked_race_subsession_id = 0

        self.active_cust_ids = {
            int(d["cust_id"])
            for d in active_drivers
            if d.get("cust_id") is not None
        }
        self.active_driver_names = {
            int(d["cust_id"]): str(d.get("name") or f"Driver {d['cust_id']}")
            for d in active_drivers
            if d.get("cust_id") is not None
        }
        self.active_driver_car_numbers = {
            int(d["cust_id"]): str(d["car_number"])
            for d in active_drivers
            if d.get("cust_id") is not None and d.get("car_number")
        }
        for driver in active_drivers:
            if driver.get("is_player") and driver.get("cust_id") is not None:
                try:
                    self._remember_player_cust_id(int(driver["cust_id"]))
                except (TypeError, ValueError):
                    pass
                break
        driver_count = len(self.active_cust_ids)

        if not is_live_scouting_session(session_kind):
            self.active_cust_ids = set()
            self.active_driver_names = {}
            self.active_driver_car_numbers = {}
            self._set_status(STATUS_CONNECTED, f"Live — {session_kind_label(session_kind)}")
            self._update_live_session_filter(active=False, hint="Unsupported session type for live scouting.")
            self._refresh_live_session_view()
            return

        self._set_status(STATUS_CONNECTED, self._session_status_label(driver_count))
        self._update_live_session_filter(active=True, hint=self._session_filter_hint())

        if is_race_session(session_kind):
            cursor = self._db_conn.cursor()
            added_ids = sync_live_session_drivers(cursor, active_drivers)
            if added_ids:
                self._db_conn.commit()
                self._insert_table_rows_for_cust_ids(added_ids)

        if (
            hasattr(self, "chk_current_race_only")
            and self.chk_current_race_only.isChecked()
        ):
            self.apply_driver_filters()
        self._refresh_live_session_view()

    def schedule_table_refresh(self) -> None:
        self._table_refresh_timer.start()

    def refresh_ui_table(self) -> None:
        self.schedule_table_refresh()

    def _invalidate_table_fingerprint(self) -> None:
        self._last_table_fingerprint = None

    def _table_data_fingerprint(self, rows: list[tuple]) -> tuple:
        league_meta = self._db_conn.execute(
            "SELECT COUNT(*), COALESCE(MAX(added_at), '') FROM league_memberships"
        ).fetchone()
        return (
            self._streamer_mode,
            league_meta,
            tuple(
            (
                row[8],  # cust_id
                row[0],  # name
                row[3],  # total_races
                row[1],  # avg_inc
                row[2],  # avg_fin
                row[9],  # race_preference
                row[16],  # has_notes
                row[4],  # last_ir
                row[5],  # last_sr
                row[6],  # last_series
            )
            for row in rows
            ),
        )

    def _refresh_ui_table_now(self, *, force: bool = False) -> None:
        rows = self._fetch_table_data()
        fingerprint = self._table_data_fingerprint(rows)
        if not force and fingerprint == self._last_table_fingerprint:
            return
        self._last_table_fingerprint = fingerprint
        self._table_rows_cache = rows
        self._rebuild_table_filter_index()
        self._recompute_filtered_table_rows()
        selected_cust_id = self.selected_cust_id
        self._render_table_page(reselect=selected_cust_id is not None)

    def _render_table_page(self, *, reselect: bool = True) -> None:
        selected_cust_id = self.selected_cust_id
        start = self._table_page * self._table_page_size
        page_rows = self._filtered_table_rows[start : start + self._table_page_size]

        self._clear_table_row_hover()
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            trends = self._safety_trends_for_table_rows(page_rows)
            league_labels = fetch_league_membership_labels(
                self._db_conn,
                [DriverTableRow.from_sql_row(row).cust_id for row in page_rows],
            )
            self.table.setRowCount(len(page_rows))
            for row_idx, row_data in enumerate(page_rows):
                display_row, cust_id, pref, risky, risky_tip, safety, real_name = (
                    self._build_display_row(row_data)
                )
                self._render_table_row(
                    row_idx,
                    display_row,
                    cust_id,
                    pref,
                    risky=risky,
                    safety=safety,
                    trend=trends.get(cust_id),
                    real_name=real_name,
                    league_label=league_labels.get(cust_id, ""),
                )
                if risky:
                    self._apply_risky_row_style(row_idx, risky_tip)
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)
            self.table.viewport().update()

        self._update_table_pagination_bar()
        if reselect and selected_cust_id is not None:
            self._select_driver_row_by_cust_id(selected_cust_id)

    def _insert_table_rows_for_cust_ids(self, cust_ids: list[int]) -> None:
        if not cust_ids:
            return

        cursor = self._db_conn.cursor()
        sql, params = table_data_for_cust_ids_sql(sorted(cust_ids))
        cursor.execute(sql, params)
        new_rows = cursor.fetchall()
        if not new_rows:
            return

        self._merge_rows_into_table_cache(new_rows)
        self._invalidate_table_fingerprint()
        self._recompute_filtered_table_rows()
        selected_cust_id = self.selected_cust_id
        self._render_table_page(reselect=selected_cust_id is not None)

    def _sync_table_rows_for_cust_ids(self, cust_ids: list[int]) -> None:
        """Update or insert table rows for drivers touched by an import."""
        unique = sorted({int(cid) for cid in cust_ids if cid is not None})
        if not unique:
            return

        cursor = self._db_conn.cursor()
        sql, params = table_data_for_cust_ids_sql(unique)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        if not rows:
            return

        self._merge_rows_into_table_cache(rows)
        self._invalidate_table_fingerprint()
        self._recompute_filtered_table_rows()
        selected_cust_id = self.selected_cust_id
        self._render_table_page(reselect=selected_cust_id is not None)

    def _refresh_table_after_import(
        self,
        *,
        affected_cust_ids: set[int],
        retention_deleted: int,
    ) -> None:
        if retention_deleted:
            self._refresh_ui_table_now(force=True)
        elif affected_cust_ids:
            self._sync_table_rows_for_cust_ids(list(affected_cust_ids))

        if self._live_mode_active and self.active_cust_ids:
            self._refresh_live_session_view()
        if hasattr(self, "race_history_tab"):
            self.race_history_tab._reload_driver_list()
            self.race_history_tab.refresh()
        if self.selected_cust_id is not None and int(self.selected_cust_id) in affected_cust_ids:
            self._populate_driver_details(self.selected_cust_id)

    def _fetch_table_data(self) -> list[tuple]:
        cursor = self._db_conn.cursor()
        cursor.execute(table_data_sql())
        return cursor.fetchall()

    def _safety_trends_for_table_rows(
        self, row_data_list: list[tuple]
    ) -> dict[int, SafetyTrend]:
        lifetime_by_cust: dict[int, SafetyIndex] = {}
        for row_data in row_data_list:
            driver = DriverTableRow.from_sql_row(row_data)
            if driver.safety.tier != "unknown":
                lifetime_by_cust[driver.cust_id] = driver.safety
        return compute_safety_trends_for_cust_ids(self._db_conn, lifetime_by_cust)

    def _build_display_row(
        self, row_data: tuple
    ) -> tuple[list, int, int | None, bool, str, SafetyIndex, str]:
        driver = DriverTableRow.from_sql_row(row_data)
        safety = driver.safety
        breakdown = driver.dnf_breakdown or "—"
        risky_tooltip = safety_tooltip(safety) if safety.risky else ""
        display_name = (
            self._streamer_session_display_name(
                driver.cust_id, safety, compact=True
            )
            if self._streamer_mode
            else display_driver_name(
                driver.cust_id,
                driver.name,
                safety,
                streamer_mode=False,
                compact_table=True,
            )
        )
        h2h = self._head_to_head_by_cust.get(driver.cust_id)
        vs_you = format_head_to_head_record(*(h2h or (0, 0, 0)))
        return (
            [
                display_name,
                driver_mark_label(driver.race_preference, safety.risky),
                "",
                driver.total_races,
                vs_you,
                safety.score if safety.tier != "unknown" else None,
                driver.avg_inc,
                driver.avg_fin,
                driver.avg_pos_delta,
                driver.dnf_total,
                driver.last_sr,
                driver.last_ir,
                driver.last_series,
                breakdown,
                driver.has_notes,
                mask_cust_id_display(driver.cust_id, streamer_mode=self._streamer_mode),
            ],
            driver.cust_id,
            driver.race_preference,
            safety.risky,
            risky_tooltip,
            safety,
            driver.name,
        )

    def _render_table_row(
        self,
        row_idx: int,
        display_row: list,
        cust_id: int,
        pref: int | None = None,
        risky: bool = False,
        safety: SafetyIndex | None = None,
        trend: SafetyTrend | None = None,
        real_name: str = "",
        league_label: str = "",
    ) -> None:
        for col_idx, value in enumerate(display_row):
            if col_idx == COL_SAFETY and safety is not None:
                item = make_safety_item(safety, trend)
            elif col_idx == COL_MARK:
                item = make_mark_item(pref, risky)
            elif col_idx == COL_LEAGUE:
                item = make_league_item(league_label)
            elif col_idx == COL_NOTE:
                item = make_note_item(bool(value))
            else:
                item = make_table_item(value)
            if col_idx == COL_VS_YOU:
                h2h = self._head_to_head_by_cust.get(cust_id)
                if h2h and sum(h2h) > 0:
                    item.setToolTip(head_to_head_tooltip(*h2h))
                elif self._resolve_player_cust_id() is None:
                    item.setToolTip(
                        "Set Hide your name in Settings or join iRacing to track your record."
                    )
                else:
                    item.setToolTip(
                        "No shared imported races with this driver yet, "
                        "or none with a finish comparison."
                    )
            if col_idx == COL_NAME:
                item.setData(Qt.ItemDataRole.UserRole, cust_id)
                item.setData(REAL_NAME_DATA_ROLE, real_name or display_row[COL_NAME])
                item.setData(PREF_DATA_ROLE, pref)
                item.setData(RISK_DATA_ROLE, 1 if risky else 0)
                if self._streamer_mode:
                    item.setToolTip("Streamer mode — real name hidden on screen")
            self.table.setItem(row_idx, col_idx, item)

    def _apply_risky_row_style(self, row_idx: int, tooltip: str) -> None:
        if not tooltip:
            return
        for col_idx in range(self.table.columnCount()):
            it = self.table.item(row_idx, col_idx)
            if it is None:
                continue
            existing = it.toolTip() or ""
            it.setToolTip(tooltip if not existing else f"{existing}\n\n{tooltip}")

    def on_driver_selected(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            self.selected_cust_id = None
            self._set_driver_panel_enabled(False)
            return

        row = selected_ranges[0].topRow()
        name_item = self.table.item(row, COL_NAME)
        if not name_item:
            return

        cust_id = name_item.data(Qt.ItemDataRole.UserRole)
        if cust_id is None:
            cust_id_item = self.table.item(row, COL_CUST_ID)
            if not cust_id_item:
                return
            cust_id = int(cust_id_item.text())

        self.selected_cust_id = int(cust_id)
        _, notes, pref = self._fetch_driver_notes_meta(self.selected_cust_id)

        self._update_preference_buttons(pref)
        self._populate_driver_details(self.selected_cust_id)
        self.notes_edit.setText(notes or "")
        self._set_driver_panel_enabled(True)
        if hasattr(self, "race_history_tab"):
            self.race_history_tab.select_driver(self.selected_cust_id)

    def _fetch_driver_notes_meta(self, cust_id: int) -> tuple[str | None, str, int | None]:
        cursor = self._db_conn.cursor()
        cursor.execute(
            "SELECT last_seen_at, notes, race_preference FROM drivers WHERE cust_id = ?",
            (cust_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None, "", None

        last_seen_at = row[0]
        notes = row[1] or ""
        pref = sqlite_row_to_int(row[2])
        return last_seen_at, notes, pref

    def _update_preference_buttons(self, pref: int | None):
        self.btn_pref_like.setChecked(pref == 1)
        self.btn_pref_dislike.setChecked(pref == -1)
        self._polish_property(self.btn_pref_like, "selected", pref == 1)
        self._polish_property(self.btn_pref_dislike, "selected", pref == -1)
        set_button_fa_icon(self.btn_pref_like, "thumbs-up", text="Liked")
        set_button_fa_icon(self.btn_pref_dislike, "thumbs-down", text="Disliked")
        risky = False
        if self.selected_cust_id is not None:
            row = self._fetch_driver_detail_row(self.selected_cust_id)
            if row is not None:
                risky = DriverDetailRow.from_sql_row(row).safety.risky
        self._update_driver_pref_badge(pref, risky=risky)

    def _row_for_cust_id(self, cust_id: int) -> int | None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_NAME)
            if item is None:
                continue
            try:
                if int(item.data(Qt.ItemDataRole.UserRole)) == int(cust_id):
                    return row
            except (TypeError, ValueError):
                continue
        return None

    def _select_driver_row_by_cust_id(self, cust_id: int) -> None:
        for idx, row_data in enumerate(self._filtered_table_rows):
            if DriverTableRow.from_sql_row(row_data).cust_id == int(cust_id):
                target_page = idx // self._table_page_size
                if target_page != self._table_page:
                    self._table_page = target_page
                    self._render_table_page(reselect=False)
                self.table.selectRow(idx % self._table_page_size)
                return

    def _set_note_indicator(self, cust_id: int, has_note: bool) -> None:
        row_idx = self._row_for_cust_id(cust_id)
        if row_idx is None:
            return
        self.table.setItem(row_idx, COL_NOTE, make_note_item(has_note))

    def _clear_row_style(self, row_idx: int) -> None:
        refresh_driver_table_row(self.table, row_idx)

    def _rebuild_note_template_buttons(self) -> None:
        grid = self._note_templates_grid
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        tags = load_note_tags()
        if not tags:
            return

        for i, tag in enumerate(tags):
            append_text = tag.append_text()
            btn = QPushButton(chip_label(tag.label))
            btn.setObjectName("chipBtn")
            if tag.description and tag.description != tag.label:
                btn.setToolTip(
                    f"Append “{append_text}” to notes (chip: {tag.label})"
                )
            else:
                btn.setToolTip(f"Append “{append_text}” to notes")
            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(
                lambda _=False, t=append_text: self._append_note_template(t)
            )
            grid.addWidget(btn, i // 2, i % 2)

        row_count = (len(tags) + 1) // 2
        for r in range(row_count):
            grid.setRowMinimumHeight(r, 40)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    def _append_note_template(self, text: str) -> None:
        existing = self.notes_edit.toPlainText()
        addition = text.strip()
        if not addition:
            return
        if existing.strip():
            new_text = existing.rstrip() + "\n" + addition
        else:
            new_text = addition
        self.notes_edit.setPlainText(new_text)
        self.notes_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.notes_edit.setFocus()

    def save_driver_notes(self):
        if not self.selected_cust_id:
            show_warning(
                self,
                "Selection Required",
                "Please click a driver on the left side first.",
            )
            return

        notes_text = self.notes_edit.toPlainText()
        self._save_notes_for_cust_id(self.selected_cust_id, notes_text)

    def set_race_preference(self, pref: int | None):
        if not self.selected_cust_id:
            show_warning(self, "Selection Required", "Please click a driver first.")
            return

        self._set_preference_for_cust_id(self.selected_cust_id, pref)
        self._update_preference_buttons(pref)

    def import_json_data(self):
        if self._is_receiver_mode_active():
            QMessageBox.information(
                self,
                "Receiver mode",
                "Import is disabled while receiving from a broadcaster.",
            )
            return
        if self._import_worker is not None and self._import_worker.isRunning():
            QMessageBox.information(
                self,
                "Import In Progress",
                "An import is already running. Please wait for it to finish.",
            )
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Historic Race Log(s)", "", "JSON Files (*.json)"
        )
        if not file_paths:
            return

        self.btn_import.setEnabled(False)
        self._set_status(STATUS_WAITING, "Importing race data…")
        self._begin_import_progress(file_paths)

        self._import_worker = ImportWorker(file_paths, self)
        self._import_worker.file_progress.connect(self._on_import_file_progress)
        self._import_worker.finished.connect(self._on_import_finished)
        self._import_worker.failed.connect(self._on_import_failed)
        self._import_worker.start()

    def _begin_import_progress(self, file_paths: list[str]) -> None:
        self._import_progress_dialog = ImportProgressDialog(
            self, file_count=len(file_paths)
        )
        self._import_progress_dialog.show()
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def _on_import_file_progress(self, current: int, total: int, filename: str) -> None:
        if self._import_progress_dialog is not None:
            self._import_progress_dialog.set_file_progress(current, total, filename)

    def _end_import_progress(self) -> None:
        if self._import_progress_dialog is not None:
            self._import_progress_dialog.close()
            self._import_progress_dialog.deleteLater()
            self._import_progress_dialog = None

    def _finish_import_ui(self) -> None:
        self._end_import_progress()
        self.btn_import.setEnabled(True)
        if self._sdk_connected:
            self._set_status(STATUS_CONNECTED, "Connected to iRacing")
        else:
            self._set_status(STATUS_OFFLINE, "Not connected to iRacing")

    def _on_import_failed(self, message: str) -> None:
        try:
            if self._import_progress_dialog is not None:
                self._import_progress_dialog.set_status("Import failed.")
                QApplication.processEvents(
                    QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
                )
            show_critical(
                self,
                "Import Failed",
                f"The import could not be completed.\n\n{message}",
            )
        finally:
            self._finish_import_ui()

    def _on_import_finished(self, result: ImportJobResult) -> None:
        QTimer.singleShot(0, lambda r=result: self._complete_import_finished(r))

    def _complete_import_finished(self, result: ImportJobResult) -> None:
        try:
            if self._import_progress_dialog is not None:
                self._import_progress_dialog.set_finalizing()
                QApplication.processEvents(
                    QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
                )

            try:
                self._db_conn.commit()
            except Exception:
                pass

            if result.retention_deleted and self.selected_cust_id is not None:
                row = self._row_for_cust_id(self.selected_cust_id)
                if row is None:
                    self.selected_cust_id = None
                    self._clear_driver_details()
                    self._set_driver_panel_enabled(False)
                    self.table.clearSelection()
                elif int(self.selected_cust_id) not in result.affected_cust_ids:
                    self._populate_driver_details(self.selected_cust_id)

            self._refresh_table_after_import(
                affected_cust_ids=result.affected_cust_ids,
                retention_deleted=result.retention_deleted,
            )
            if hasattr(self, "settings_tab"):
                self.settings_tab.refresh_storage_info()
            if hasattr(self, "import_history_tab"):
                self.import_history_tab.refresh()

            QApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )

            self._show_import_result_dialogs(result)
        finally:
            self._finish_import_ui()

    def _show_import_result_dialogs(self, result: ImportJobResult) -> None:
        total_files = result.total_files
        total_races_imported = result.total_races_imported
        total_results_imported = result.total_results_imported
        total_results_updated = result.total_results_updated
        total_results_skipped = result.total_results_skipped
        errors = result.errors

        if total_results_imported == 0 and total_results_updated == 0 and total_results_skipped > 0:
            QMessageBox.information(
                self,
                "Import Completed",
                f"No new or updated results — {total_results_skipped} row(s) skipped "
                "(missing subsession ID or duplicate without subsession ID).",
            )
            return

        if total_results_imported == 0 and total_results_updated == 0:
            detail = "\n\nDetails:\n" + "\n".join(errors[:10]) if errors else ""
            for err in errors:
                log_user_error(err, context="Import")
            show_warning(
                self,
                "Import Completed (No Results Found)",
                "No race results were imported from the selected file(s).\n\n"
                "This usually means the JSON structure/keys don't match what the importer expects.\n"
                "Supported:\n"
                "- iRacing 'event_result' JSON (imports Race session), or\n"
                "- custom {'races': [...]} format.\n\n"
                "Results with a subsession ID are updated if that session was already imported.\n\n"
                + detail,
            )
            return

        detail = ""
        if total_results_updated:
            detail += f"\n\nUpdated {total_results_updated} existing result(s) with new session data."
        if total_results_skipped:
            detail += (
                f"\n\n{total_results_skipped} result(s) skipped "
                "(no subsession ID or duplicate without subsession ID)."
            )
        if errors:
            for err in errors:
                log_user_error(err, context="Import")
            detail += "\n\nSome files had issues:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                detail += f"\n... and {len(errors) - 10} more."

        title = "Import Complete"
        if total_results_updated and not total_results_imported:
            title = "Import Complete — Session Updated"
        elif total_results_updated:
            title = "Import Complete — New & Updated"

        parts = []
        if total_results_imported:
            parts.append(f"{total_results_imported} new")
        if total_results_updated:
            parts.append(f"{total_results_updated} updated")
        summary = " and ".join(parts) + " driver result(s)" if parts else "0 driver result(s)"

        QMessageBox.information(
            self,
            title,
            f"Imported {summary} across {total_races_imported} race(s) from {total_files} file(s)."
            + detail,
        )

    def _stop_sdk_worker(self) -> None:
        worker = getattr(self, "worker", None)
        if worker is None:
            return
        try:
            worker.stop()
            worker.wait(5000)
        except Exception:
            pass
        self.worker = None

    def _is_receiver_mode_active(self) -> bool:
        return self._broadcast_client is not None or self._using_broadcast_db

    def _update_receiver_import_controls(self, *, receiving: bool) -> None:
        if not hasattr(self, "btn_import"):
            return
        self.btn_import.setEnabled(not receiving)
        if receiving:
            set_button_tooltip(
                self.btn_import,
                "Import is disabled while connected as a receiver to a broadcaster.",
            )
        else:
            set_button_tooltip(
                self.btn_import,
                "Import iRacing event_result JSON or custom race logs",
            )

    def _set_broadcast_mode_ui(
        self,
        *,
        receiving: bool,
        source_name: str = "",
        connection_state: str = "idle",
        ws_connected: bool = False,
    ) -> None:
        self.btn_start_broadcast.setEnabled(not receiving)
        self.btn_connect_broadcast.setEnabled(not receiving)
        show_disconnect = receiving and connection_state in ("connecting", "connected")
        self.btn_disconnect_broadcast.setVisible(show_disconnect)
        set_button_tooltip(
            self.btn_start_broadcast,
            TIP_BROADCAST_DISABLED if receiving else TIP_BROADCAST,
        )
        set_button_tooltip(
            self.btn_connect_broadcast,
            TIP_RECEIVER_DISABLED if receiving else TIP_RECEIVER,
        )
        self._update_receiver_import_controls(receiving=receiving)
        if not receiving:
            self.broadcast_receiver_banner.setVisible(False)
            self._polish_property(self.broadcast_receiver_banner, "status", "")
            return

        label = source_name or self._broadcast_connect_host or "Broadcaster"
        if connection_state == "connected":
            self.broadcast_receiver_banner.setText(
                f"Connected to {label} — receiving scouting data. "
                "Notes and likes sync to the broadcaster (not saved on this device)."
            )
            self._polish_property(self.broadcast_receiver_banner, "status", "connected")
            self._set_status(STATUS_CONNECTED, f"Receiver · {label}")
        elif connection_state == "connecting":
            target = self._broadcast_connect_host or label
            if ws_connected:
                self.broadcast_receiver_banner.setText(
                    f"Connected to {target} — loading scouting data…"
                )
            else:
                self.broadcast_receiver_banner.setText(
                    f"Connecting to {target}…"
                )
            self._polish_property(self.broadcast_receiver_banner, "status", "connecting")
            status = (
                f"Receiver · loading from {target}…"
                if ws_connected
                else f"Connecting to {target}…"
            )
            self._set_status(STATUS_WAITING, status)
        else:
            self.broadcast_receiver_banner.setVisible(False)
            self._polish_property(self.broadcast_receiver_banner, "status", "")
        self.broadcast_receiver_banner.setVisible(True)

    def _wire_broadcast_session_feed(self) -> None:
        feed = self._broadcast_session_feed
        if feed is None:
            return
        feed.connection_changed.connect(self.handle_sdk_connection)
        feed.drivers_updated.connect(self.handle_sdk_update)
        feed.grid_updated.connect(self._on_grid_updated)
        feed.spotter_car_behind.connect(self._on_spotter_car_behind)

    def _start_broadcasting(self) -> None:
        if self._broadcast_controller is not None:
            return
        if self._using_broadcast_db:
            QMessageBox.information(
                self,
                "Receiver mode",
                "Disconnect from the broadcaster before starting a broadcast from this device.",
            )
            return
        import socket

        from ..broadcast.controller import BroadcastController
        from ..ui.broadcast_status_dialog import BroadcastStatusDialog

        controller = BroadcastController(self, broadcaster_name=socket.gethostname(), parent=self)
        if not controller.start():
            QMessageBox.warning(
                self,
                "Broadcast failed",
                "GridNotes could not start the broadcast server on port 8765.",
            )
            return

        dialog = BroadcastStatusDialog(
            broadcaster_name=controller._name,
            port=controller.server_port(),
            parent=self,
        )
        controller._server.receivers_changed.connect(dialog.set_connected_receivers)
        dialog.set_connected_receivers([])
        dialog.stop_requested.connect(self._on_broadcast_stop_requested)
        dialog.audio_spotter_changed.connect(self._on_broadcast_audio_spotter_changed)
        if sys.platform != "win32":
            dialog.set_audio_spotter_enabled(False)
            dialog.set_audio_spotter_available(False)
        self._broadcast_controller = controller
        self._broadcast_status_dialog = dialog
        self._broadcast_audio_spotter_enabled = False
        self._sync_audio_spotter_worker()
        self.hide()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_broadcast_stop_requested(self) -> None:
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        self._stop_broadcasting()

    def _restore_after_broadcast_stop(self) -> None:
        if self._shutting_down:
            return
        self.main_tabs.setCurrentIndex(0)
        show_live = self._live_mode_active and self._sdk_connected
        self.view_stack.setCurrentIndex(1 if show_live else 0)
        sizes = self.main_splitter.sizes()
        if len(sizes) >= 2 and sizes[0] < 100:
            self.main_splitter.setSizes([1000, 340])
        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)
        if show_live:
            self._refresh_live_session_view()
        self.table.viewport().update()
        self.view_stack.currentWidget().update()

    def _stop_broadcasting(self) -> None:
        dialog = self._broadcast_status_dialog
        if dialog is not None and not dialog.is_stopping():
            dialog.begin_stopping(closing_app=self._shutting_down)
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        if self._broadcast_controller is not None:
            self._broadcast_controller.stop()
            self._broadcast_controller = None
        self._broadcast_audio_spotter_enabled = False
        if not self._shutting_down:
            self._sync_audio_spotter_worker()
        if hasattr(self, "_audio_spotter"):
            self._audio_spotter.reset_tracking()
        if self._broadcast_status_dialog is not None:
            self._broadcast_status_dialog.close()
            self._broadcast_status_dialog = None
        if self._shutting_down:
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(0, self._restore_after_broadcast_stop)

    def _clear_broadcast_live_session_state(self) -> None:
        """Drop live session fields fed by a broadcaster (restore pre-receiver UI)."""
        self._sdk_connected = False
        self.current_subsession_id = 0
        self.current_session_kind = ""
        self.current_session_context = {}
        self.active_cust_ids = set()
        self.active_driver_names = {}
        self.active_driver_car_numbers = {}
        self._latest_grid_slots = []
        self._tracked_race_subsession_id = 0
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        if hasattr(self, "chk_current_race_only"):
            self.chk_current_race_only.setChecked(False)
        if hasattr(self, "live_session_view"):
            self.live_session_view.set_grid_walk_mode(False, emit=False)
            self.live_session_view.collapse_expanded()
        if hasattr(self, "_audio_spotter"):
            self._audio_spotter.reset_tracking()
        self._refresh_live_session_view()

    def _disconnect_broadcast_receiver(
        self,
        *,
        status_message: str = "Waiting for iRacing…",
    ) -> None:
        self._ignore_broadcast_disconnect_signal = True
        self._stop_broadcast_connect_timer()
        self._broadcast_receiver_ws_connected = False
        if self._broadcast_client is not None:
            self._broadcast_client.disconnect_from_broadcaster()
            self._broadcast_client.deleteLater()
            self._broadcast_client = None
        if self._broadcast_session_feed is not None:
            self._broadcast_session_feed.deleteLater()
            self._broadcast_session_feed = None
        if self._using_broadcast_db:
            close_sqlite_connection(self._db_conn)
            if self._local_db_conn is not None:
                self._db_conn = self._local_db_conn
            elif not self._shutting_down:
                self._db_conn = connect_db()
            self._using_broadcast_db = False
            self._local_db_conn = None
        self._broadcast_source_name = ""
        self._broadcast_connect_host = ""
        self._clear_broadcast_live_session_state()
        if self._shutting_down:
            self._ignore_broadcast_disconnect_signal = False
            return
        self._set_broadcast_mode_ui(receiving=False)
        self.settings_tab.set_broadcast_receiver_active(False)
        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)
        self.start_sdk_worker()
        self._set_status(STATUS_WAITING, status_message)
        QTimer.singleShot(0, self._release_broadcast_disconnect_guard)

    def _release_broadcast_disconnect_guard(self) -> None:
        self._ignore_broadcast_disconnect_signal = False

    def _on_broadcaster_connection_lost(self) -> None:
        """Unexpected drop from broadcaster — same cleanup as manual disconnect."""
        had_broadcast_data = self._using_broadcast_db
        message = (
            "Broadcaster disconnected — restored your local scouting book."
            if had_broadcast_data
            else "Disconnected from broadcaster."
        )
        self._disconnect_broadcast_receiver(status_message=message)
        if had_broadcast_data:
            log_user_error(message, context="broadcast receiver")

    def _connect_as_broadcast_receiver(self) -> None:
        if self._broadcast_controller is not None:
            QMessageBox.information(
                self,
                "Broadcasting",
                "Stop broadcasting on this device before connecting as a receiver.",
            )
            return
        from ..ui.broadcast_connect_dialog import BroadcastConnectDialog

        dialog = BroadcastConnectDialog(self)
        target: dict[str, object] = {}

        def _remember_target(host: str, port: int) -> None:
            target["host"] = host
            target["port"] = port

        dialog.connect_requested.connect(_remember_target)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        host = str(target.get("host") or dialog.host_input.text().strip())
        if not host:
            return
        try:
            port = int(target.get("port") or dialog.port_input.text().strip() or "8765")
        except (TypeError, ValueError):
            port = 8765
        self._begin_broadcast_receiver(host, port)

    def _begin_broadcast_receiver(self, host: str, port: int) -> None:
        from ..broadcast.client import BroadcastClient
        from ..broadcast.session_feed import BroadcastSessionFeed

        if self._broadcast_client is not None:
            self._disconnect_broadcast_receiver()

        self._broadcast_client = BroadcastClient(host=host, port=port, parent=self)
        self._broadcast_session_feed = BroadcastSessionFeed(self)
        self._broadcast_connect_host = host
        self._wire_broadcast_session_feed()
        self._broadcast_client.snapshot_received.connect(self._on_broadcast_snapshot)
        self._broadcast_client.live_state_received.connect(self._on_broadcast_live_state)
        self._broadcast_client.driver_patch_received.connect(self._on_broadcast_driver_patch)
        self._broadcast_client.connected_changed.connect(self._on_broadcast_client_connected)
        self._broadcast_client.error_message.connect(self._on_broadcast_client_error)
        self._stop_sdk_worker()
        self._set_broadcast_mode_ui(
            receiving=True,
            connection_state="connecting",
            source_name=host,
        )
        self.settings_tab.set_broadcast_receiver_active(
            True, source_name=host, connecting=True
        )
        self._broadcast_receiver_ws_connected = False
        self._broadcast_connect_timer.start(20_000)
        self._broadcast_client.connect_to_broadcaster()

    def _stop_broadcast_connect_timer(self) -> None:
        if hasattr(self, "_broadcast_connect_timer"):
            self._broadcast_connect_timer.stop()

    def _on_broadcast_connect_timeout(self) -> None:
        if self._using_broadcast_db or self._broadcast_client is None:
            return
        if self._broadcast_client.is_connected():
            target = self._broadcast_connect_host or "broadcaster"
            self._set_broadcast_mode_ui(
                receiving=True,
                connection_state="connecting",
                source_name=target,
                ws_connected=True,
            )
            log_user_error(
                f"Connected to {target} but scouting data has not arrived yet. "
                "Ensure the broadcaster is still running.",
                context="broadcast receiver",
            )
            return
        self._set_broadcast_mode_ui(receiving=False)
        self._set_status(
            STATUS_OFFLINE,
            "Could not reach broadcaster — check the IP and that Broadcast is running.",
            user_error=True,
        )
        self.settings_tab.set_broadcast_receiver_active(False)

    def _on_broadcast_client_connected(self, connected: bool) -> None:
        if connected:
            self._broadcast_receiver_ws_connected = True
            if self._using_broadcast_db:
                name = self._broadcast_source_name or self._broadcast_connect_host
                self._stop_broadcast_connect_timer()
                self._set_broadcast_mode_ui(
                    receiving=True,
                    source_name=name,
                    connection_state="connected",
                )
                self.settings_tab.set_broadcast_receiver_active(
                    True, source_name=name
                )
            else:
                self._set_broadcast_mode_ui(
                    receiving=True,
                    connection_state="connecting",
                    source_name=self._broadcast_connect_host,
                    ws_connected=True,
                )
            return
        if self._ignore_broadcast_disconnect_signal:
            return
        self._broadcast_receiver_ws_connected = False
        self._stop_broadcast_connect_timer()
        QTimer.singleShot(0, self._on_broadcaster_connection_lost)

    def _on_broadcast_client_error(self, message: str) -> None:
        if message:
            log_user_error(message, context="broadcast receiver")
            if not self._using_broadcast_db:
                self._stop_broadcast_connect_timer()
                self._set_status(STATUS_OFFLINE, message, user_error=True)

    def _on_broadcast_snapshot(self, payload: dict) -> None:
        from ..broadcast.snapshot import apply_snapshot_to_memory

        self._stop_broadcast_connect_timer()
        try:
            if not self._using_broadcast_db:
                self._local_db_conn = self._db_conn
            else:
                close_sqlite_connection(self._db_conn)
            self._db_conn = apply_snapshot_to_memory(payload)
        except Exception:
            logger.exception("Failed to apply broadcast snapshot")
            self._set_broadcast_mode_ui(receiving=False)
            self._set_status(
                STATUS_OFFLINE,
                "Received data from broadcaster but could not load it.",
                user_error=True,
            )
            return
        self._using_broadcast_db = True
        self._broadcast_source_name = str(payload.get("broadcaster_name") or "Broadcaster")
        self._set_broadcast_mode_ui(
            receiving=True,
            source_name=self._broadcast_source_name,
            connection_state="connected",
        )
        self.settings_tab.set_broadcast_receiver_active(
            True,
            source_name=self._broadcast_source_name,
        )
        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)
        self._refresh_live_session_view()

    def _on_broadcast_live_state(self, payload: dict) -> None:
        if self._broadcast_session_feed is not None:
            self._broadcast_session_feed.apply_live_state(payload)

    def _sync_driver_patch_to_broadcaster(
        self,
        cust_id: int,
        *,
        notes: str | None = None,
        race_preference: int | None | object = ...,
    ) -> bool:
        client = self._broadcast_client
        if client is None:
            return False
        return client.send_driver_patch(
            cust_id,
            notes=notes,
            race_preference=race_preference,
        )

    def _apply_driver_patch_ui(self, cust_id: int, patch: dict) -> None:
        if "notes" in patch:
            notes_text = str(patch.get("notes") or "")
            self._set_note_indicator(cust_id, bool(notes_text.strip()))
            if self.selected_cust_id == cust_id and not self.notes_edit.hasFocus():
                self.notes_edit.setPlainText(notes_text)
        if "race_preference" in patch:
            pref = patch.get("race_preference")
            row_idx = self._row_for_cust_id(cust_id)
            if row_idx is not None:
                name_item = self.table.item(row_idx, COL_NAME)
                if name_item is not None:
                    name_item.setData(PREF_DATA_ROLE, pref)
                refresh_driver_table_row(self.table, row_idx)
            if self.selected_cust_id == cust_id:
                self._update_preference_buttons(pref)

    def _on_broadcast_driver_patch(self, patch: dict) -> None:
        if not self._using_broadcast_db:
            return
        from ..broadcast.patches import apply_driver_patch

        if not apply_driver_patch(self._db_conn, patch):
            return
        self._db_conn.commit()
        try:
            cust_id = int(patch["cust_id"])
        except (KeyError, TypeError, ValueError):
            return
        self._apply_driver_patch_ui(cust_id, patch)

    def closeEvent(self, event):
        logger.info("Application closing")
        self._shutting_down = True
        self._table_refresh_timer.stop()
        self._stop_broadcasting()
        self._disconnect_broadcast_receiver()
        self._release_resources_before_exit()
        event.accept()

