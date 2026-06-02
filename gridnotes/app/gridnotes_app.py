import logging
import os
import sys
from pathlib import Path

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
from ..data.db import close_sqlite_connection, connect_db, get_setting, init_db, set_setting
from ..data.driver_cleanup import count_zero_race_drivers, purge_zero_race_drivers
from ..data.driver_models import DriverDetailRow, DriverTableRow, build_live_session_entries
from ..ui.a11y import driver_mark_label, set_accessible
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
    COL_MARK,
    COL_NAME,
    COL_NOTE,
    COL_SAFETY,
    COL_SERIES,
    COLUMN_COUNT,
    DRIVER_TABLE_HEADERS,
    PREF_DATA_ROLE,
    REAL_NAME_DATA_ROLE,
    RESIZE_TO_CONTENTS_COLUMNS,
    RISK_DATA_ROLE,
    configure_driver_table_theme,
    configure_driver_table_widget,
    make_mark_item,
    make_note_item,
    make_safety_item,
    make_table_item,
    refresh_driver_table_row,
    set_driver_table_hover_row,
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
from ..ui.streamer_mode_progress_dialog import StreamerModeProgressDialog
from ..data.queries import (
    driver_detail_sql,
    fetch_recent_races_by_cust_ids,
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
from ..core.timestamps import format_last_seen_et
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


class GridNotesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GridNotes")
        self.setMinimumSize(1280, 760)
        self.resize(1440, 860)

        window_icon = load_app_icon()
        if window_icon is not None:
            self.setWindowIcon(window_icon)
        self._taskbar_identity_applied = False

        self.current_subsession_id = 0
        self.current_session_kind = ""
        self.selected_cust_id = None
        self.worker = None
        self._import_worker: ImportWorker | None = None
        self._api_test_worker: ApiConnectionTestWorker | None = None
        self._update_check_worker: UpdateCheckWorker | None = None
        self._apply_update_worker: ApplyAppUpdateWorker | None = None
        self._update_progress_dialog = None
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
        self.active_cust_ids: set[int] = set()
        self.active_driver_names: dict[int, str] = {}
        self._hover_row: int | None = None
        self._did_initial_column_resize = False
        self._live_mode_active = get_setting("live_mode", "0") == "1"
        self._streamer_mode = is_streamer_mode_enabled(get_setting(STREAMER_MODE_KEY))
        self._streamer_refresh_busy = False
        self._streamer_progress_dialog: StreamerModeProgressDialog | None = None
        self._sdk_connected = False
        from ..services.audio_spotter import (
            AUDIO_SPOTTER_KEY,
            AudioSpotterService,
            is_audio_spotter_setting_enabled,
        )

        self._audio_spotter_enabled = is_audio_spotter_setting_enabled(
            get_setting(AUDIO_SPOTTER_KEY)
        )
        self._audio_spotter = AudioSpotterService()

        init_db()
        try:
            from ..installer.update_paths import prune_old_update_workspaces

            prune_old_update_workspaces()
        except Exception:
            pass
        self._db_conn = connect_db()
        self._run_data_retention_purge()
        self.init_ui()
        self._sync_windows_install_metadata()
        self.start_sdk_worker()
        if get_setting(AUTO_CHECK_UPDATES_KEY, "0") == "1":
            QTimer.singleShot(800, self._check_for_app_updates_on_startup)

    def _sync_windows_install_metadata(self) -> None:
        """Keep Settings → Apps and the version label in sync with the installed release."""
        try:
            from ..app.app_version import reconcile_installed_version
            from ..installer.uninstall import resolve_install_root

            install_root = resolve_install_root()
            if install_root is not None:
                reconcile_installed_version(install_root)
        except Exception:
            pass
        if sys.platform != "win32":
            return
        try:
            from ..installer.uninstall import resolve_install_root
            from ..platform.windows.windows_apps import register_windows_uninstall

            install_root = resolve_install_root()
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
        header.setToolTip("Click a column header to sort")
        header.setMinimumSectionSize(64)
        header.setDefaultSectionSize(100)
        header.setStretchLastSection(False)

        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        row_h = self.table.verticalHeader().defaultSectionSize()
        configure_widget_scrollbars(
            self.table,
            single_step=row_h,
            page_step=row_h * 4,
            horizontal_single=72,
            horizontal_page=240,
            always_show=True,
        )

        for col in RESIZE_TO_CONTENTS_COLUMNS:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SERIES, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnHidden(COL_CUST_ID, True)
        self.table.setColumnWidth(COL_NAME, 200)
        self.table.setColumnWidth(COL_SERIES, 180)

        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item is not None:
                label = header_item.text()
                header_item.setToolTip(f"Click to sort by {label}")

        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.entered.connect(self._on_table_row_entered)
        self.table.installEventFilter(self)
        self.table.viewport().installEventFilter(self)

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
            self.search_input.setPlaceholderText("Search by name…")
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

    def _refresh_grid_walk_view(self) -> None:
        if not hasattr(self, "live_session_view") or not self.live_session_view.is_grid_walk_mode():
            return
        if self.worker is not None and self._sdk_connected:
            self.worker.request_grid_refresh()
            return
        entries = self._build_live_session_entries()
        by_cust = {int(e["cust_id"]): e for e in entries}
        self.live_session_view.update_grid(
            [], None, by_cust, streamer_mode=self._streamer_mode
        )

    def _on_grid_updated(self, slots: list, player_cust_id) -> None:
        if not self._live_mode_active or not self.live_session_view.is_grid_walk_mode():
            return
        entries = self._build_live_session_entries()
        by_cust = {int(e["cust_id"]): e for e in entries}
        cust_id = int(player_cust_id) if player_cust_id is not None else None
        self.live_session_view.update_grid(
            slots, cust_id, by_cust, streamer_mode=self._streamer_mode
        )

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

    def _sync_audio_spotter_worker(self) -> None:
        if self.worker is None:
            return
        active = (
            self._live_mode_active
            and self._audio_spotter_enabled
            and sys.platform == "win32"
        )
        self.worker.set_spotter_enabled(active)

    def _on_spotter_car_behind(self, cust_id: int, gap: float) -> None:
        from ..services.audio_spotter import load_spotter_driver

        if not self._live_mode_active or not self._audio_spotter_enabled:
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
            announce_name = streamer_display_name(int(cust_id), info.safety)
        self._audio_spotter.maybe_announce(
            int(cust_id), info, announce_name=announce_name
        )

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
        for entry in entries:
            entry["safety_trend"] = trends.get(int(entry["cust_id"]))
        if self._streamer_mode:
            for entry in entries:
                cid = int(entry["cust_id"])
                safety = entry.get("safety")
                if not isinstance(safety, SafetyIndex):
                    safety = None
                entry["name"] = streamer_display_name(cid, safety)
        return entries

    def _refresh_live_session_view(self) -> None:
        if not hasattr(self, "live_session_view"):
            return
        driver_count = len(self.active_cust_ids)
        scouting = is_live_scouting_session(self.current_session_kind)
        self.live_session_view.set_session_info(
            connected=self._sdk_connected,
            subsession_id=self.current_subsession_id,
            driver_count=driver_count,
            session_kind=self.current_session_kind,
            persist_drivers=is_race_session(self.current_session_kind),
        )
        if self._sdk_connected and scouting and self.active_cust_ids:
            if self.live_session_view.is_grid_walk_mode():
                self._refresh_grid_walk_view()
            else:
                self.live_session_view.rebuild_if_changed(self._build_live_session_entries())

    def _on_live_driver_clicked(self, cust_id: int) -> None:
        self._set_live_mode(False)
        self._select_driver_row_by_cust_id(cust_id)

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
        last_seen_fmt = format_last_seen_et(detail.last_seen_at)
        breakdown = detail.dnf_breakdown

        if self._streamer_mode:
            self.driver_name_label.setText(
                streamer_display_name(cust_id, detail.safety)
            )
            self.driver_meta_label.setText(streamer_detail_meta(last_seen_fmt=last_seen_fmt))
        else:
            self.driver_name_label.setText(detail.name or "Unknown driver")
            self.driver_meta_label.setText(
                f"ID {cust_id}  ·  Last raced {last_seen_fmt} ET"
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

    def _set_driver_panel_enabled(self, enabled: bool) -> None:
        self.empty_state_label.setVisible(not enabled)
        self.driver_detail_scroll.setVisible(enabled)
        self.notes_edit.setEnabled(enabled)
        self.btn_pref_like.setEnabled(enabled)
        self.btn_pref_dislike.setEnabled(enabled)
        self.btn_pref_clear.setEnabled(enabled)
        self.btn_save_notes.setEnabled(enabled)

    def init_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        app_title = QLabel("GridNotes")
        app_title.setObjectName("appTitle")
        self.app_subtitle = QLabel("Driver scouting notes & race history")
        self.app_subtitle.setObjectName("appSubtitle")
        title_block.addWidget(app_title)
        title_block.addWidget(self.app_subtitle)
        header.addLayout(title_block)
        header.addStretch()
        self.btn_streamer_mode = QPushButton("Streamer mode")
        self.btn_streamer_mode.setObjectName("streamerModeBtn")
        self.btn_streamer_mode.setCheckable(True)
        self.btn_streamer_mode.setChecked(self._streamer_mode)
        self.btn_streamer_mode.setToolTip(
            "Replace driver names with aliases on screen (e.g. Driver #14). "
            "Your database and notes are not changed."
        )
        self.btn_streamer_mode.clicked.connect(self._toggle_streamer_mode)
        self._polish_property(self.btn_streamer_mode, "active", self._streamer_mode)
        if self._streamer_mode:
            self.app_subtitle.setText("Streamer mode — names hidden on screen")
        header.addWidget(
            self.btn_streamer_mode,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.status_label = QLabel("Waiting for iRacing…")
        self.status_label.setObjectName("statusBadge")
        self._set_status(STATUS_WAITING, "Waiting for iRacing…")
        self.btn_live_mode = QPushButton("Live Mode")
        self.btn_live_mode.setObjectName("liveModeBtn")
        self.btn_live_mode.setCheckable(True)
        self.btn_live_mode.setToolTip(
            "Switch to high-contrast live session view (large fonts for in-race scouting)"
        )
        self.btn_live_mode.clicked.connect(self._toggle_live_mode)
        header.addWidget(self.btn_live_mode, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root_layout.addLayout(header)

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

        self.settings_tab = SettingsTab()
        self.settings_tab.settings_saved.connect(self._on_settings_saved)
        self.settings_tab.theme_changed.connect(self.apply_theme)
        self.settings_tab.check_updates_requested.connect(self._check_for_app_updates)
        self.settings_tab.apply_update_requested.connect(self._apply_app_update)
        self.settings_tab.zero_race_cleanup_requested.connect(self._cleanup_zero_race_drivers)
        self.settings_tab.uninstall_requested.connect(self._uninstall_application)
        self.settings_tab.backup_export_requested.connect(self._export_database_backup)
        self.settings_tab.backup_import_requested.connect(self._import_database_backup)
        self.settings_tab.support_bundle_requested.connect(self._save_support_bundle)
        self.settings_tab.open_logs_folder_requested.connect(self._open_logs_folder)
        if iracing_data_api_auto_import_enabled():
            self.settings_tab.api_test_requested.connect(self._test_iracing_api_connection)
        self.main_tabs.addTab(self.settings_tab, "Settings")

        database_panel = QWidget()
        database_layout = QVBoxLayout(database_panel)
        database_layout.setContentsMargins(0, 0, 0, 0)
        database_layout.setSpacing(0)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        database_layout.addWidget(main_splitter)

        # --- Left: drivers ---
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout(controls_group)
        controls_layout.setHorizontalSpacing(10)
        controls_layout.setVerticalSpacing(8)

        self.btn_import = QPushButton("Import race JSON…")
        self.btn_import.setObjectName("primaryBtn")
        self.btn_import.setToolTip("Import iRacing event_result JSON or custom race logs")
        self.btn_import.clicked.connect(self.import_json_data)
        controls_layout.addWidget(self.btn_import, 0, 0)

        self.btn_reset_db = QPushButton("Reset all data")
        self.btn_reset_db.setObjectName("dangerBtn")
        self.btn_reset_db.setToolTip("Permanently delete all drivers, notes, and race results")
        self.btn_reset_db.clicked.connect(self.reset_database)
        controls_layout.addWidget(self.btn_reset_db, 0, 1)

        live_session_row = QHBoxLayout()
        live_session_row.setSpacing(8)
        self.chk_current_race_only = QCheckBox("Current session only")
        self.chk_current_race_only.setChecked(False)
        self.chk_current_race_only.setToolTip(
            "Show only drivers in the current iRacing session. "
            "During practice and qualifying this is scouting only — drivers are saved when the race starts."
        )
        self.chk_current_race_only.stateChanged.connect(self.apply_driver_filters)
        live_session_row.addWidget(self.chk_current_race_only)
        self.live_session_note = QLabel(MSG_SESSION_NOT_CONNECTED)
        self.live_session_note.setObjectName("sectionHint")
        self.live_session_note.setWordWrap(True)
        live_session_row.addWidget(self.live_session_note, stretch=1)
        controls_layout.addLayout(live_session_row, 0, 2, 1, 2)

        self.search_input = QLineEdit()
        search_label = QLabel("Search drivers")
        search_label.setBuddy(self.search_input)
        self.search_input.setPlaceholderText(
            "Search by alias (#14) or real name…"
            if self._streamer_mode
            else "Search by name…"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.apply_driver_filters)
        controls_layout.addWidget(search_label, 1, 0)
        controls_layout.addWidget(self.search_input, 1, 1)

        self.ignore_name_input = QLineEdit()
        ignore_label = QLabel("Hide your name")
        ignore_label.setBuddy(self.ignore_name_input)
        self.ignore_name_input.setPlaceholderText("Optional")
        self.ignore_name_input.setText(get_setting("ignore_driver_name", "") or "")
        self.ignore_name_input.textChanged.connect(self.apply_driver_filters)
        controls_layout.addWidget(ignore_label, 1, 2)
        controls_layout.addWidget(self.ignore_name_input, 1, 3)

        self.btn_save_ignore = QPushButton("Save hidden name")
        self.btn_save_ignore.setToolTip("Save the hidden name to settings")
        self.btn_save_ignore.clicked.connect(self.save_ignore_name)
        controls_layout.addWidget(self.btn_save_ignore, 2, 2, 1, 2)

        self.btn_scouting_guide = QPushButton("Scouting guide…")
        self.btn_scouting_guide.setToolTip(
            "Safety Index, form arrows (↗ ↘ →), liked/disliked/risk marks, and risk factors"
        )
        self.btn_scouting_guide.clicked.connect(self._show_scouting_guide)
        controls_layout.addWidget(self.btn_scouting_guide, 2, 0, 1, 2)

        left_layout.addWidget(controls_group)

        drivers_label = QLabel(
            "Drivers — select a row for notes (arrow keys, Enter)  ·  "
            "Mark: Liked, Disliked, or Risk  ·  Safety Index may show form arrows (↗ ↘)  ·  "
            "open Scouting guide for details"
        )
        drivers_label.setObjectName("sectionHint")
        left_layout.addWidget(drivers_label)

        self.table = QTableWidget()
        self.table.setColumnCount(COLUMN_COUNT)
        self.table.setHorizontalHeaderLabels(DRIVER_TABLE_HEADERS)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSortingEnabled(True)
        configure_driver_table_widget(self.table)
        self.table.verticalHeader().setVisible(False)
        self.table.setToolTip("Click a row to open scouting notes")
        self.table.itemSelectionChanged.connect(self.on_driver_selected)
        self.table.itemSelectionChanged.connect(lambda: self.table.viewport().update())
        self._configure_driver_table()
        left_layout.addWidget(self.table, stretch=1)

        main_splitter.addWidget(left_panel)

        # --- Right: driver detail ---
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)

        detail_title = QLabel("Driver details")
        detail_title.setObjectName("appTitle")
        detail_title.setStyleSheet("font-size: 16px;")
        right_layout.addWidget(detail_title)

        self.empty_state_label = QLabel(
            "Select a driver from the table to view stats, write scouting notes, "
            "and mark whether you liked racing with them."
        )
        self.empty_state_label.setObjectName("emptyState")
        self.empty_state_label.setWordWrap(True)
        right_layout.addWidget(self.empty_state_label)

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

        self.driver_name_label = QLabel()
        self.driver_name_label.setObjectName("driverName")
        self.driver_name_label.setWordWrap(True)
        detail_layout.addWidget(self.driver_name_label)

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

        notes_group = QGroupBox("Scouting notes")
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setSpacing(12)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "e.g. Aggressive on restarts, gives room on restarts, weak under pressure…"
        )
        self.notes_edit.setMinimumHeight(140)
        configure_widget_scrollbars(self.notes_edit, single_step=20, page_step=100)
        notes_layout.addWidget(self.notes_edit)

        templates_label = QLabel("Quick note templates")
        templates_label.setObjectName("sectionHint")
        notes_layout.addWidget(templates_label)

        templates_grid = QGridLayout()
        templates_grid.setHorizontalSpacing(12)
        templates_grid.setVerticalSpacing(14)
        templates_grid.setContentsMargins(0, 4, 0, 0)
        template_list = [
            ("+ Clean", "Clean racer"),
            ("+ Divebombs", "Divebombs / late sends"),
            ("+ Blocks", "Blocks aggressively"),
            ("+ Good restarts", "Good on restarts"),
            ("+ Unpredictable", "Unpredictable lines / braking"),
        ]
        for i, (label, text) in enumerate(template_list):
            btn = QPushButton(label)
            btn.setObjectName("chipBtn")
            btn.setToolTip("Append to notes")
            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _=False, t=text: self._append_note_template(t))
            templates_grid.addWidget(btn, i // 2, i % 2)
        for r in range((len(template_list) + 1) // 2):
            templates_grid.setRowMinimumHeight(r, 40)
        templates_grid.setColumnStretch(0, 1)
        templates_grid.setColumnStretch(1, 1)
        notes_layout.addLayout(templates_grid)

        right_layout.addWidget(notes_group, stretch=1)

        pref_group = QGroupBox("How was racing with them?")
        pref_layout = QHBoxLayout(pref_group)
        self.btn_pref_like = QPushButton("Liked")
        self.btn_pref_like.setObjectName("prefLike")
        self.btn_pref_like.setCheckable(True)
        self.btn_pref_like.setToolTip("Highlight row green in the driver list")
        self.btn_pref_like.clicked.connect(lambda: self.set_race_preference(1))
        pref_layout.addWidget(self.btn_pref_like)
        self.btn_pref_dislike = QPushButton("Didn't like")
        self.btn_pref_dislike.setObjectName("prefDislike")
        self.btn_pref_dislike.setCheckable(True)
        self.btn_pref_dislike.setToolTip("Highlight row red in the driver list")
        self.btn_pref_dislike.clicked.connect(lambda: self.set_race_preference(-1))
        pref_layout.addWidget(self.btn_pref_dislike)
        self.btn_pref_clear = QPushButton("Clear")
        self.btn_pref_clear.setToolTip("Remove like/dislike highlight")
        self.btn_pref_clear.clicked.connect(lambda: self.set_race_preference(None))
        pref_layout.addWidget(self.btn_pref_clear)
        right_layout.addWidget(pref_group)

        self.btn_save_notes = QPushButton("Save notes")
        self.btn_save_notes.setObjectName("primaryBtn")
        self.btn_save_notes.clicked.connect(self.save_driver_notes)
        right_layout.addWidget(self.btn_save_notes)

        main_splitter.addWidget(right_panel)
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(520)
        main_splitter.setStretchFactor(0, 5)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setSizes([1000, 340])

        self.view_stack.addWidget(database_panel)

        self.live_session_view = LiveSessionView()
        self.live_session_view.driver_clicked.connect(self._on_live_driver_clicked)
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
        self._refresh_ui_table_now(force=True)
        self.apply_driver_filters()
        self._configure_accessibility()
        self._configure_keyboard_shortcuts()
        self.apply_theme()

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
            self.ignore_name_input,
            "Hide your name",
            "Hide a driver row matching this name from the list.",
        )
        set_accessible(self.btn_save_ignore, "Save hidden name")
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
            self.btn_reset_db,
            "Reset all data",
            "Permanently delete all drivers, notes, and race results.",
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
        set_accessible(self.status_label, "iRacing connection status")
        set_accessible(
            self.notes_edit,
            "Scouting notes",
            "Notes for the selected driver.",
        )
        set_accessible(self.btn_pref_like, "Liked", "Mark that you liked racing with this driver.")
        set_accessible(
            self.btn_pref_dislike,
            "Didn't like",
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
        configure_driver_table_theme(tid)
        refresh_widget_tree(self)
        if hasattr(self, "table"):
            self.table.viewport().update()
        if hasattr(self, "safety_index_panel"):
            self.safety_index_panel.refresh_theme()
        if hasattr(self, "live_session_view"):
            self.live_session_view.update()

    def save_ignore_name(self):
        set_setting("ignore_driver_name", (self.ignore_name_input.text() or "").strip() or None)
        self.apply_driver_filters()

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
        return deleted

    def _on_settings_saved(self) -> None:
        deleted = self._run_data_retention_purge(show_status=True)
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
        q = (self.search_input.text() or "").strip().lower()
        ignore_name = (self.ignore_name_input.text() or "").strip().lower()
        current_only = (
            hasattr(self, "chk_current_race_only")
            and self.chk_current_race_only.isEnabled()
            and self.chk_current_race_only.isChecked()
        )

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, COL_NAME)
            display_name = (name_item.text() if name_item else "").strip()
            display_lc = display_name.lower()
            real_name = ""
            if name_item is not None:
                stored = name_item.data(REAL_NAME_DATA_ROLE)
                if stored is not None:
                    real_name = str(stored).strip()
            name_lc = (real_name or display_name).lower()

            hidden = False
            if q and q not in name_lc and q not in display_lc:
                hidden = True
            if ignore_name and name_lc == ignore_name:
                hidden = True
            if current_only:
                cust_id = None
                if name_item is not None:
                    try:
                        cust_id = int(name_item.data(Qt.ItemDataRole.UserRole))
                    except (TypeError, ValueError):
                        cust_id = None
                if cust_id is None or cust_id not in self.active_cust_ids:
                    hidden = True
            self.table.setRowHidden(row, hidden)

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
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        self.notes_edit.clear()
        self._clear_driver_details()
        self._set_driver_panel_enabled(False)
        self.table.clearSelection()
        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)

        QMessageBox.information(self, "Database Reset", "Database cleared successfully.")

    def start_sdk_worker(self):
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
            self._open_update_progress(result.latest_version)
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

    def _open_update_progress(self, target_version: str | None) -> None:
        from ..ui.update_progress_dialog import UpdateProgressDialog

        self._close_update_progress()
        dialog = UpdateProgressDialog(self)
        dialog.begin(target_version=target_version)
        dialog.show()
        self._update_progress_dialog = dialog

    def _close_update_progress(self) -> None:
        if self._update_progress_dialog is not None:
            self._update_progress_dialog.close()
            self._update_progress_dialog = None

    def _on_apply_update_progress(self, message: str, percent: int) -> None:
        if self._update_progress_dialog is not None:
            self._update_progress_dialog.set_progress(message, percent)

    def _on_apply_update_finished(self, ok: bool, message: str, restart: bool) -> None:
        self.settings_tab.set_apply_update_busy(False)
        if not ok:
            self._close_update_progress()
            log_user_error(message, context="application update")
            self.settings_tab.show_apply_update_result(False, message)
            QMessageBox.warning(self, "Update did not finish", message)
            return

        self.settings_tab.show_apply_update_result(True, message)
        if self._update_progress_dialog is not None:
            self._update_progress_dialog.mark_complete(
                "Restarting GridNotes…" if restart else "Closing GridNotes to finish installing…"
            )
        if restart:
            logger.info("Update applied; restarting application")
            restart_application()
            return

        logger.info("Portable update scheduled; exiting for background install")
        self._release_resources_before_exit()
        os._exit(0)

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
        if self.worker is not None:
            self.worker.stop()
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

        self._invalidate_table_fingerprint()
        self._refresh_ui_table_now(force=True)
        if self.selected_cust_id is not None:
            self._populate_driver_details(self.selected_cust_id)

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
                self._update_live_session_filter(active=False, hint="Unsupported session type for live scouting.")
            self._refresh_live_session_view()
            return

        if self._tracked_race_subsession_id:
            self._maybe_auto_fetch_race_results(self._tracked_race_subsession_id)
        self._tracked_race_subsession_id = 0

        self.current_subsession_id = 0
        self.current_session_kind = ""
        self.active_cust_ids = set()
        self.active_driver_names = {}
        self._set_status(STATUS_WAITING, "Waiting for iRacing…")
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        if hasattr(self, "chk_current_race_only"):
            self.chk_current_race_only.setChecked(False)
        self._refresh_live_session_view()

    def handle_sdk_update(self, active_drivers, subsession_id, session_kind):
        prev_subsession = self.current_subsession_id
        prev_kind = self.current_session_kind

        self.current_subsession_id = subsession_id
        self.current_session_kind = session_kind

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
        driver_count = len(self.active_cust_ids)

        if not is_live_scouting_session(session_kind):
            self.active_cust_ids = set()
            self.active_driver_names = {}
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
        return (
            self._streamer_mode,
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

        row_count = len(rows)
        selected_cust_id = self.selected_cust_id

        was_sorting = self.table.isSortingEnabled()
        if was_sorting:
            self.table.setSortingEnabled(False)

        trends = self._safety_trends_for_table_rows(rows)

        self._clear_table_row_hover()
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(row_count)
            for row_idx, row_data in enumerate(rows):
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
                )
                if risky:
                    self._apply_risky_row_style(row_idx, risky_tip)
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)
            self.table.viewport().update()

        if was_sorting:
            self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicator(COL_NAME, Qt.SortOrder.AscendingOrder)
        if not self._did_initial_column_resize:
            self.table.resizeColumnsToContents()
            self._did_initial_column_resize = True
        self.table.setColumnWidth(COL_NAME, max(self.table.columnWidth(COL_NAME), 180))
        self.table.setColumnWidth(COL_SERIES, max(self.table.columnWidth(COL_SERIES), 160))
        self.apply_driver_filters()
        if selected_cust_id is not None:
            self._select_driver_row_by_cust_id(selected_cust_id)

    def _find_insert_row(self, name: str) -> int:
        name_lc = (name or "").lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_NAME)
            row_name = (item.text() if item else "").lower()
            if row_name > name_lc:
                return row
        return self.table.rowCount()

    def _insert_table_rows_for_cust_ids(self, cust_ids: list[int]) -> None:
        if not cust_ids:
            return

        cursor = self._db_conn.cursor()
        sql, params = table_data_for_cust_ids_sql(sorted(cust_ids))
        cursor.execute(sql, params)
        new_rows = cursor.fetchall()
        if not new_rows:
            return

        selected_cust_id = self.selected_cust_id
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        trends = self._safety_trends_for_table_rows(new_rows)
        try:
            for row_data in sorted(new_rows, key=lambda row: (row[0] or "").lower(), reverse=True):
                display_row, cust_id, pref, risky, risky_tip, safety, real_name = (
                    self._build_display_row(row_data)
                )
                insert_at = self._find_insert_row(display_row[COL_NAME])
                self.table.insertRow(insert_at)
                self._render_table_row(
                    insert_at,
                    display_row,
                    cust_id,
                    pref,
                    risky=risky,
                    safety=safety,
                    trend=trends.get(cust_id),
                    real_name=real_name,
                )
                if risky:
                    self._apply_risky_row_style(insert_at, risky_tip)
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)
            self.table.viewport().update()

        self._invalidate_table_fingerprint()
        self.apply_driver_filters()
        if selected_cust_id is not None:
            self._select_driver_row_by_cust_id(selected_cust_id)

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
        display_name = display_driver_name(
            driver.cust_id,
            driver.name,
            safety,
            streamer_mode=self._streamer_mode,
            compact_table=True,
        )
        return (
            [
                display_name,
                driver_mark_label(driver.race_preference, safety.risky),
                driver.total_races,
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
    ) -> None:
        for col_idx, value in enumerate(display_row):
            if col_idx == COL_SAFETY and safety is not None:
                item = make_safety_item(safety, trend)
            elif col_idx == COL_MARK:
                item = make_mark_item(pref, risky)
            elif col_idx == COL_NOTE:
                item = make_note_item(bool(value))
            else:
                item = make_table_item(value)
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

    def _row_for_cust_id(self, cust_id: int) -> int | None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CUST_ID)
            if not item:
                continue
            try:
                if int(item.text()) == cust_id:
                    return row
            except Exception:
                continue
        return None

    def _select_driver_row_by_cust_id(self, cust_id: int):
        row = self._row_for_cust_id(cust_id)
        if row is not None:
            self.table.selectRow(row)

    def _set_note_indicator(self, cust_id: int, has_note: bool) -> None:
        row_idx = self._row_for_cust_id(cust_id)
        if row_idx is None:
            return
        self.table.setItem(row_idx, COL_NOTE, make_note_item(has_note))

    def _clear_row_style(self, row_idx: int) -> None:
        refresh_driver_table_row(self.table, row_idx)

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
        cursor = self._db_conn.cursor()
        cursor.execute(
            "UPDATE drivers SET notes = ? WHERE cust_id = ?",
            (notes_text, self.selected_cust_id),
        )
        self._db_conn.commit()
        self._set_note_indicator(self.selected_cust_id, bool(notes_text.strip()))
        QMessageBox.information(self, "Saved", "Driver notebook updated successfully.")

    def set_race_preference(self, pref: int | None):
        if not self.selected_cust_id:
            show_warning(self, "Selection Required", "Please click a driver first.")
            return

        cust_id = self.selected_cust_id
        cursor = self._db_conn.cursor()
        cursor.execute(
            "UPDATE drivers SET race_preference = ? WHERE cust_id = ?",
            (pref, cust_id),
        )
        self._db_conn.commit()
        self._update_preference_buttons(pref)

        row_idx = self._row_for_cust_id(cust_id)
        if row_idx is not None:
            name_item = self.table.item(row_idx, COL_NAME)
            if name_item is not None:
                name_item.setData(PREF_DATA_ROLE, pref)
            refresh_driver_table_row(self.table, row_idx)

    def import_json_data(self):
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
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self._import_worker = ImportWorker(file_paths, self)
        self._import_worker.finished.connect(self._on_import_finished)
        self._import_worker.failed.connect(self._on_import_failed)
        self._import_worker.start()

    def _finish_import_ui(self) -> None:
        QApplication.restoreOverrideCursor()
        self.btn_import.setEnabled(True)
        if self._sdk_connected:
            self._set_status(STATUS_CONNECTED, "Connected to iRacing")
        else:
            self._set_status(STATUS_OFFLINE, "Not connected to iRacing")

    def _on_import_failed(self, message: str) -> None:
        self._finish_import_ui()
        show_critical(
            self,
            "Import Failed",
            f"The import could not be completed.\n\n{message}",
        )

    def _on_import_finished(self, result: ImportJobResult) -> None:
        self._finish_import_ui()

        if result.retention_deleted and self.selected_cust_id is not None:
            row = self._row_for_cust_id(self.selected_cust_id)
            if row is None:
                self.selected_cust_id = None
                self._clear_driver_details()
                self._set_driver_panel_enabled(False)
                self.table.clearSelection()
            else:
                self._populate_driver_details(self.selected_cust_id)

        self._refresh_ui_table_now(force=True)
        if hasattr(self, "settings_tab"):
            self.settings_tab.refresh_storage_info()

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

    def closeEvent(self, event):
        logger.info("Application closing")
        self._release_resources_before_exit()
        event.accept()

