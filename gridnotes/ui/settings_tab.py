"""Settings tab UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..services.app_update import (
    AUTO_CHECK_UPDATES_KEY,
    UpdateCheckResult,
    is_frozen_build,
)
from ..app.app_version import installed_version
from .appearance import (
    THEME_OPTIONS,
    get_theme_id,
    set_theme_id,
)
from ..data.data_retention import DEFAULT_RETENTION, RETENTION_OPTIONS, SETTING_KEY, retention_label
from ..data.db import connect_db, get_data_dir_path, get_db_file_size, get_db_path, get_setting, set_setting
from ..installer.uninstall import resolve_install_root
from ..data.driver_cleanup import count_zero_race_drivers
from ..app.feature_flags import iracing_data_api_auto_import_enabled
from ..iracing.iracing_data_api import package_available, package_unavailable_reason
from ..iracing.iracing_data_api_config import (
    clear_legacy_api_settings,
    get_access_token,
    is_auto_fetch_enabled,
    save_api_settings,
)
from ..iracing.iracing_oauth_guide import (
    OAUTH_REGISTRATION_PAUSED_HTML,
    combined_oauth_guide_html,
    oauth_registration_paused_plain,
)
from .ui_widgets import Accordion, HtmlHintLabel, SettingsSectionNavigator
from .theme import configure_scroll_area, status_message_color
from ..services.user_feedback import log_user_error
from ..core.utils import format_file_size


class SettingsTab(QWidget):
    """Application settings panel."""

    settings_saved = pyqtSignal()
    theme_changed = pyqtSignal(str)
    zero_race_cleanup_requested = pyqtSignal()
    check_updates_requested = pyqtSignal()
    apply_update_requested = pyqtSignal()
    uninstall_requested = pyqtSignal(bool)  # remove_user_data
    api_test_requested = pyqtSignal(str)  # access_token

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        clear_legacy_api_settings()
        self._last_update_check: UpdateCheckResult | None = None
        self._settings_baseline: tuple[str, ...] = ()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("settingsHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 10)
        header_layout.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("appTitle")
        title.setStyleSheet("font-size: 18px;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.btn_save_settings = QPushButton("Save settings")
        self.btn_save_settings.setObjectName("primaryBtn")
        self.btn_save_settings.setToolTip(
            "Save appearance, retention, update, and OAuth token settings"
        )
        self.btn_save_settings.clicked.connect(self._save_settings)
        header_layout.addWidget(self.btn_save_settings)
        root.addWidget(header)

        self._auto_import_page: QWidget | None = None

        self._section_nav = SettingsSectionNavigator()
        if iracing_data_api_auto_import_enabled():
            self._auto_import_page = self._build_auto_import_page()
            self._section_nav.add_section("Auto-import", self._auto_import_page)
        self._section_nav.add_section("Data", self._build_data_page())
        self._section_nav.add_section("Maintenance", self._build_maintenance_page())

        body = QFrame()
        body.setObjectName("settingsBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._section_nav.sidebar)

        self._content_scroll = QScrollArea()
        self._content_scroll.setObjectName("settingsContentScroll")
        self._content_scroll.setWidgetResizable(True)
        self._content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        configure_scroll_area(self._content_scroll, page_step=96)

        content_host = QWidget()
        content_host.setObjectName("settingsContent")
        host_layout = QVBoxLayout(content_host)
        host_layout.setContentsMargins(20, 12, 20, 20)
        host_layout.setSpacing(0)
        host_layout.addWidget(self._section_nav.stack)
        self._content_scroll.setWidget(content_host)

        body_layout.addWidget(self._content_scroll, stretch=1)
        root.addWidget(body, stretch=1)

        self._connect_settings_change_handlers()
        self._capture_settings_baseline()
        self._update_save_button_state()

    def _section_hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionHint")
        label.setWordWrap(True)
        return label

    def _build_auto_import_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(
            self._section_hint(
                "Optional: after a race, auto-import official results via the iRacing "
                "Data API (Windows + live SDK). Requires an OAuth access token."
            )
        )

        self.oauth_paused_notice = HtmlHintLabel(OAUTH_REGISTRATION_PAUSED_HTML)
        self.oauth_paused_notice.setObjectName("settingsOAuthNotice")
        layout.addWidget(self.oauth_paused_notice)

        setup_group = QGroupBox("Connection (optional — needs OAuth token)")
        setup_layout = QVBoxLayout(setup_group)
        setup_layout.setSpacing(10)

        self.chk_auto_fetch = QCheckBox(
            "Automatically fetch results when a race session ends"
        )
        self.chk_auto_fetch.setChecked(is_auto_fetch_enabled())
        self.chk_auto_fetch.setToolTip(oauth_registration_paused_plain())
        setup_layout.addWidget(self.chk_auto_fetch)

        self.api_package_status = QLabel("")
        self.api_package_status.setObjectName("settingsStatusPill")
        self.api_package_status.setWordWrap(True)
        setup_layout.addWidget(self.api_package_status)
        self._update_api_package_status()

        token_label = QLabel("OAuth access token")
        token_label.setObjectName("statInlineLabel")
        setup_layout.addWidget(token_label)

        token_row = QHBoxLayout()
        token_row.setSpacing(8)
        self.api_token_input = QLineEdit()
        self.api_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_token_input.setPlaceholderText("Paste access_token from iRacing OAuth")
        self.api_token_input.setText(get_access_token())
        token_row.addWidget(self.api_token_input, stretch=1)

        self.btn_test_api = QPushButton("Test")
        self.btn_test_api.setToolTip("Test connection with this token")
        self.btn_test_api.setFixedWidth(72)
        self.btn_test_api.clicked.connect(self._request_api_test)
        token_row.addWidget(self.btn_test_api)
        setup_layout.addLayout(token_row)

        self.api_status = QLabel("")
        self.api_status.setObjectName("sectionHint")
        self.api_status.setWordWrap(True)
        setup_layout.addWidget(self.api_status)

        layout.addWidget(setup_group)

        guide_accordion = Accordion(exclusive=True)
        guide_accordion.add_section(
            "OAuth setup guide (when registration is available)",
            combined_oauth_guide_html(),
            expanded=False,
        )
        layout.addWidget(guide_accordion)
        layout.addStretch()
        return page

    def _build_data_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setSpacing(10)

        appearance_layout.addWidget(
            self._section_hint("Choose light or dark colors for the whole application.")
        )

        theme_label = QLabel("Color theme")
        theme_label.setObjectName("statInlineLabel")
        appearance_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("settingsCombo")
        for value, label in THEME_OPTIONS:
            self.theme_combo.addItem(label, value)
        current_theme = get_theme_id()
        theme_idx = self.theme_combo.findData(current_theme)
        self.theme_combo.setCurrentIndex(theme_idx if theme_idx >= 0 else 0)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        appearance_layout.addWidget(self.theme_combo)

        layout.addWidget(appearance_group)

        retention_group = QGroupBox("Race history retention")
        retention_layout = QVBoxLayout(retention_group)
        retention_layout.setSpacing(10)

        retention_layout.addWidget(
            self._section_hint(
                "Remove imported race results older than the selected period. "
                "Notes and like/dislike preferences are kept."
            )
        )

        row_label = QLabel("Keep race data for")
        row_label.setObjectName("statInlineLabel")
        retention_layout.addWidget(row_label)

        self.retention_combo = QComboBox()
        self.retention_combo.setObjectName("settingsCombo")
        for value, label in RETENTION_OPTIONS:
            self.retention_combo.addItem(label, value)
        current = get_setting(SETTING_KEY, DEFAULT_RETENTION) or DEFAULT_RETENTION
        idx = self.retention_combo.findData(current)
        self.retention_combo.setCurrentIndex(idx if idx >= 0 else 0)
        retention_layout.addWidget(self.retention_combo)

        self.retention_status = QLabel("")
        self.retention_status.setObjectName("sectionHint")
        self.retention_status.setWordWrap(True)
        retention_layout.addWidget(self.retention_status)
        self._update_retention_status_label()

        layout.addWidget(retention_group)

        storage_group = QGroupBox("Storage location")
        storage_layout = QVBoxLayout(storage_group)
        storage_layout.setSpacing(8)

        storage_layout.addWidget(
            self._section_hint("Local database and settings on this computer:")
        )

        self.data_dir_label = QLabel(str(get_data_dir_path()))
        self.data_dir_label.setObjectName("sectionHint")
        self.data_dir_label.setWordWrap(True)
        self.data_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        storage_layout.addWidget(self.data_dir_label)

        db_hint = QLabel("Database file")
        db_hint.setObjectName("statInlineLabel")
        storage_layout.addWidget(db_hint)

        self.db_path_label = QLabel("")
        self.db_path_label.setObjectName("statValue")
        self.db_path_label.setWordWrap(True)
        self.db_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        storage_layout.addWidget(self.db_path_label)
        self.refresh_storage_info()

        layout.addWidget(storage_group)
        layout.addStretch()
        return page

    def _build_maintenance_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        cleanup_group = QGroupBox("Driver cleanup")
        cleanup_layout = QVBoxLayout(cleanup_group)
        cleanup_layout.setSpacing(10)

        cleanup_layout.addWidget(
            self._section_hint(
                "Remove drivers with no imported race results, including live-session "
                "placeholders and their scouting notes."
            )
        )

        self.zero_race_status = QLabel("")
        self.zero_race_status.setObjectName("sectionHint")
        self.zero_race_status.setWordWrap(True)
        cleanup_layout.addWidget(self.zero_race_status)
        self._update_zero_race_status_label()

        self.btn_remove_zero_race = QPushButton("Remove drivers with 0 races")
        self.btn_remove_zero_race.clicked.connect(self._request_zero_race_cleanup)
        cleanup_layout.addWidget(self.btn_remove_zero_race)

        layout.addWidget(cleanup_group)

        updates_group = QGroupBox("Application updates")
        updates_layout = QVBoxLayout(updates_group)
        updates_layout.setSpacing(10)

        if is_frozen_build():
            updates_hint = (
                "See if a newer GridNotes installer is available. Your notes and "
                "settings stay on this computer when you update."
            )
        else:
            updates_hint = (
                "See if a newer version is ready. When one is available, Update now "
                "installs it for you — GridNotes closes briefly and reopens. Your "
                "notes and settings are not removed."
            )
        updates_layout.addWidget(self._section_hint(updates_hint))

        self.chk_auto_check_updates = QCheckBox(
            "Check for updates automatically when GridNotes opens"
        )
        self.chk_auto_check_updates.setChecked(
            get_setting(AUTO_CHECK_UPDATES_KEY, "0") == "1"
        )
        self.chk_auto_check_updates.setToolTip(
            "When you open GridNotes, ask if you want to install a newer version. "
            "Save settings for this to take effect."
        )
        updates_layout.addWidget(self.chk_auto_check_updates)

        self.version_label = QLabel()
        self._refresh_installed_version_label()
        self.version_label.setObjectName("statValue")
        updates_layout.addWidget(self.version_label)

        update_btn_row = QHBoxLayout()
        update_btn_row.setSpacing(8)
        self.btn_check_updates = QPushButton("Check for updates")
        self.btn_check_updates.clicked.connect(self._request_update_check)
        update_btn_row.addWidget(self.btn_check_updates)

        self.btn_apply_update = QPushButton("Update now")
        self.btn_apply_update.setObjectName("primaryBtn")
        self.btn_apply_update.setVisible(False)
        self.btn_apply_update.clicked.connect(self._request_apply_update)
        update_btn_row.addWidget(self.btn_apply_update)
        update_btn_row.addStretch()
        updates_layout.addLayout(update_btn_row)

        self.update_status = QLabel("")
        self.update_status.setObjectName("sectionHint")
        self.update_status.setWordWrap(True)
        updates_layout.addWidget(self.update_status)

        layout.addWidget(updates_group)

        uninstall_group = QGroupBox("Uninstall")
        uninstall_layout = QVBoxLayout(uninstall_group)
        uninstall_layout.setSpacing(10)

        uninstall_layout.addWidget(
            self._section_hint(
                "Remove GridNotes from this computer. You can keep your notes and "
                "database, or delete everything — your choice below."
            )
        )

        self.uninstall_install_label = QLabel("")
        self.uninstall_install_label.setObjectName("sectionHint")
        self.uninstall_install_label.setWordWrap(True)
        self.uninstall_install_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        uninstall_layout.addWidget(self.uninstall_install_label)

        self.chk_uninstall_remove_data = QCheckBox(
            "Also delete my notes, database, and settings"
        )
        self.chk_uninstall_remove_data.setToolTip(
            f"Removes everything under:\n{get_data_dir_path()}"
        )
        uninstall_layout.addWidget(self.chk_uninstall_remove_data)

        self.btn_uninstall = QPushButton("Uninstall GridNotes…")
        self.btn_uninstall.setObjectName("dangerBtn")
        self.btn_uninstall.clicked.connect(self._request_uninstall)
        uninstall_layout.addWidget(self.btn_uninstall)

        self.uninstall_status = QLabel("")
        self.uninstall_status.setObjectName("sectionHint")
        self.uninstall_status.setWordWrap(True)
        uninstall_layout.addWidget(self.uninstall_status)

        layout.addWidget(uninstall_group)
        layout.addStretch()
        return page

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh_storage_info()
        self.refresh_uninstall_info()
        self._update_zero_race_status_label()
        if iracing_data_api_auto_import_enabled():
            self._update_api_package_status()

    def refresh_storage_info(self) -> None:
        db_path = get_db_path()
        size_bytes = get_db_file_size()
        if size_bytes is None:
            self.db_path_label.setText(f"{db_path}  ·  —")
        else:
            self.db_path_label.setText(f"{db_path}  ·  {format_file_size(size_bytes)}")

    def current_retention_value(self) -> str:
        value = self.retention_combo.currentData()
        return value if value else DEFAULT_RETENTION

    def current_theme_value(self) -> str:
        value = self.theme_combo.currentData()
        return value if value else get_theme_id()

    def _current_settings_snapshot(self) -> tuple[str, ...]:
        snapshot: list[str] = [
            self.current_retention_value(),
            self.current_theme_value(),
            "1" if self.chk_auto_check_updates.isChecked() else "0",
        ]
        if iracing_data_api_auto_import_enabled():
            snapshot.extend(
                [
                    "1" if self.chk_auto_fetch.isChecked() else "0",
                    self.api_token_input.text().strip(),
                ]
            )
        return tuple(snapshot)

    def _capture_settings_baseline(self) -> None:
        self._settings_baseline = self._current_settings_snapshot()

    def _settings_have_unsaved_changes(self) -> bool:
        return self._current_settings_snapshot() != self._settings_baseline

    def _update_save_button_state(self) -> None:
        self.btn_save_settings.setEnabled(self._settings_have_unsaved_changes())

    def _connect_settings_change_handlers(self) -> None:
        self.retention_combo.currentIndexChanged.connect(self._on_settings_edited)
        self.chk_auto_check_updates.stateChanged.connect(self._on_settings_edited)
        if iracing_data_api_auto_import_enabled():
            self.chk_auto_fetch.stateChanged.connect(self._on_settings_edited)
            self.api_token_input.textChanged.connect(self._on_settings_edited)

    def _on_settings_edited(self, *_args: object) -> None:
        self._update_save_button_state()

    def _on_theme_combo_changed(self) -> None:
        theme_id = self.current_theme_value()
        self.theme_changed.emit(theme_id)
        self._on_settings_edited()

    def _update_retention_status_label(self) -> None:
        self.retention_status.setText(
            f"Current policy: {retention_label(self.current_retention_value())}"
        )

    def _update_zero_race_status_label(self, pending: int | None = None) -> None:
        if pending is None:
            conn = connect_db()
            try:
                pending = count_zero_race_drivers(conn)
            finally:
                conn.close()
        if pending:
            self.zero_race_status.setText(
                f"{pending} driver(s) with 0 races can be removed."
            )
        else:
            self.zero_race_status.setText("No zero-race drivers to remove.")

    def _request_zero_race_cleanup(self) -> None:
        self.zero_race_cleanup_requested.emit()

    def _refresh_installed_version_label(self) -> None:
        self.version_label.setText(f"Your version: {installed_version()}")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_installed_version_label()

    def _request_update_check(self) -> None:
        self.check_updates_requested.emit()

    def _request_apply_update(self) -> None:
        self.apply_update_requested.emit()

    def refresh_uninstall_info(self) -> None:
        install_root = resolve_install_root()
        data_dir = get_data_dir_path()
        self.chk_uninstall_remove_data.setToolTip(
            f"Removes everything under:\n{data_dir}"
        )
        if install_root is not None:
            self.uninstall_install_label.setText(
                "GridNotes is installed on this computer.\n\n"
                f"Your notes and database are stored here:\n{data_dir}"
            )
            self.btn_uninstall.setEnabled(True)
        else:
            self.uninstall_install_label.setText(
                "GridNotes app files were not found, but your personal data is here:\n"
                f"{data_dir}"
            )
            self.btn_uninstall.setEnabled(True)

    def uninstall_remove_user_data(self) -> bool:
        return self.chk_uninstall_remove_data.isChecked()

    def _request_uninstall(self) -> None:
        install_root = resolve_install_root()
        remove_data = self.uninstall_remove_user_data()
        data_dir = get_data_dir_path()

        if install_root is None and not remove_data:
            QMessageBox.information(
                self,
                "Uninstall",
                "Turn on “Also delete my notes, database, and settings” to remove "
                "your GridNotes data, or run Install GridNotes.bat from your download "
                "folder if you need to remove an installed copy.",
            )
            return

        lines = ["This cannot be undone.", ""]
        if install_root is not None:
            lines.append(f"• Remove install folder:\n  {install_root}")
            lines.append("• Remove Desktop shortcut")
        if remove_data:
            lines.append(f"• Delete your data:\n  {data_dir}")
        else:
            lines.append(f"• Keep your data:\n  {data_dir}")
        lines.append("")
        lines.append("GridNotes will close when you continue.")

        if (
            QMessageBox.question(
                self,
                "Uninstall GridNotes?",
                "\n".join(lines),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.uninstall_requested.emit(remove_data)

    def show_uninstall_result(self, ok: bool, message: str) -> None:
        self.uninstall_status.setText(message)
        theme_id = get_theme_id()
        self.uninstall_status.setStyleSheet(
            f"color: {status_message_color(theme_id, ok=ok)};"
        )

    def last_update_check(self) -> UpdateCheckResult | None:
        return self._last_update_check

    def set_update_check_busy(self, busy: bool) -> None:
        self.btn_check_updates.setEnabled(not busy)
        self.btn_apply_update.setEnabled(not busy)
        if busy:
            self.update_status.setText("Checking for updates…")
            self.update_status.setStyleSheet("")

    def set_apply_update_busy(self, busy: bool) -> None:
        self.btn_check_updates.setEnabled(not busy)
        self.btn_apply_update.setEnabled(not busy)
        if busy:
            self.update_status.setText("Updating…")
            self.update_status.setStyleSheet("")

    def show_update_check_result(self, result: UpdateCheckResult) -> None:
        self._last_update_check = result
        self.update_status.setText(result.message)
        theme_id = get_theme_id()
        if result.update_available:
            self.update_status.setStyleSheet(
                f"color: {status_message_color(theme_id, ok=False)};"
            )
        elif result.ok:
            self.update_status.setStyleSheet(
                f"color: {status_message_color(theme_id, ok=True)};"
            )
        else:
            self.update_status.setStyleSheet(
                f"color: {status_message_color(theme_id, ok=False)};"
            )

        if not result.update_available:
            self.btn_apply_update.setVisible(False)
            return

        self.btn_apply_update.setVisible(True)
        if result.can_apply_in_place:
            self.btn_apply_update.setText("Update now")
            if result.apply_method == "portable":
                self.btn_apply_update.setToolTip(
                    "Download and install the update, then reopen GridNotes"
                )
            else:
                self.btn_apply_update.setToolTip(
                    "Install the latest version and restart GridNotes"
                )
        else:
            self.btn_apply_update.setText("Get latest version")
            self.btn_apply_update.setToolTip(
                "Open the download page in your web browser"
            )

    def show_apply_update_result(self, ok: bool, message: str) -> None:
        self.update_status.setText(message)
        theme_id = get_theme_id()
        self.update_status.setStyleSheet(
            f"color: {status_message_color(theme_id, ok=ok)};"
        )

    def _update_api_package_status(self) -> None:
        if package_available():
            self.api_package_status.setText("Package: iracingdataapi installed")
            self.api_package_status.setProperty("status", "ok")
        else:
            self.api_package_status.setText(package_unavailable_reason())
            self.api_package_status.setProperty("status", "error")
        self.api_package_status.style().unpolish(self.api_package_status)
        self.api_package_status.style().polish(self.api_package_status)

    def _focus_auto_import_tab(self) -> None:
        if not iracing_data_api_auto_import_enabled() or self._auto_import_page is None:
            return
        idx = self._section_nav.index_of_page(self._auto_import_page)
        if idx >= 0:
            self._section_nav.set_current_index(idx)

    def _request_api_test(self) -> None:
        self._focus_auto_import_tab()
        self.api_test_requested.emit(self.api_token_input.text().strip())

    def set_api_test_busy(self, busy: bool) -> None:
        self.btn_test_api.setEnabled(not busy)
        self.api_token_input.setEnabled(not busy)
        if busy:
            self.api_status.setText("Testing connection…")
            self.api_status.setStyleSheet("")

    def show_api_test_result(self, ok: bool, message: str) -> None:
        if not iracing_data_api_auto_import_enabled():
            return
        self._focus_auto_import_tab()
        self.api_status.setText(message)
        theme_id = get_theme_id()
        self.api_status.setStyleSheet(
            f"color: {status_message_color(theme_id, ok=ok)};"
        )

    def show_api_fetch_status(self, message: str, *, error: bool = False) -> None:
        if not iracing_data_api_auto_import_enabled():
            return
        self._focus_auto_import_tab()
        if error:
            log_user_error(message, context="iRacing Data API auto-fetch")
        self.api_status.setText(message)
        theme_id = get_theme_id()
        self.api_status.setStyleSheet(
            f"color: {status_message_color(theme_id, ok=not error)};"
        )

    def _save_api_settings(self) -> None:
        if not iracing_data_api_auto_import_enabled():
            return
        save_api_settings(
            enabled=self.chk_auto_fetch.isChecked(),
            access_token=self.api_token_input.text().strip(),
        )

    def _save_settings(self) -> None:
        set_setting(SETTING_KEY, self.current_retention_value())
        set_theme_id(self.current_theme_value())
        set_setting(
            AUTO_CHECK_UPDATES_KEY,
            "1" if self.chk_auto_check_updates.isChecked() else "0",
        )
        if iracing_data_api_auto_import_enabled():
            self._save_api_settings()
        self._update_retention_status_label()
        self._capture_settings_baseline()
        self._update_save_button_state()
        self.settings_saved.emit()

    def show_zero_race_cleanup_result(self, deleted: int) -> None:
        self.refresh_storage_info()
        if deleted:
            self.zero_race_status.setText(
                f"Removed {deleted} driver(s) with no race history."
            )
        else:
            self._update_zero_race_status_label(0)

    def show_purge_result(self, deleted: int) -> None:
        self.refresh_storage_info()
        policy = retention_label(self.current_retention_value())
        if deleted:
            self.retention_status.setText(
                f"Current policy: {policy} — removed {deleted} expired race result(s)."
            )
        else:
            self._update_retention_status_label()
