"""Connect to a GridNotes broadcaster on the LAN."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from ..broadcast.discovery import BroadcastDiscovery, BroadcasterInfo
from ..ui.a11y import set_button_tooltip
from ..ui.icons import BUTTON_ICON_TEXT_GAP, fa_icon, set_button_fa_icon
from ..ui.theme import configure_modal_dialog


class BroadcastConnectDialog(QDialog):
    connect_requested = pyqtSignal(str, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Connect to broadcaster")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        intro = QLabel(
            "Choose a broadcaster on your network. The receiver shows the broadcaster's "
            "scouting book and live session. Notes and likes you change sync back to the "
            "broadcaster and to other receivers, but are not saved on this device."
        )
        intro.setObjectName("sectionHint")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(self._section_label("Broadcasters on this network"))
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self._list)

        refresh_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        set_button_fa_icon(self.btn_refresh, "arrows-rotate", text="Refresh")
        set_button_tooltip(self.btn_refresh, "Search the network again for active broadcasters.")
        self.btn_refresh.clicked.connect(self._restart_discovery)
        refresh_row.addWidget(self.btn_refresh)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        layout.addWidget(self._section_label("Or enter address manually"))
        manual_row = QHBoxLayout()
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("IP address or hostname")
        self.host_input.setClearButtonEnabled(True)
        manual_row.addWidget(self.host_input, stretch=3)
        self.port_input = QLineEdit("8765")
        self.port_input.setMaximumWidth(72)
        manual_row.addWidget(self.port_input)
        layout.addLayout(manual_row)

        self._status = QLabel("Searching…")
        self._status.setObjectName("sectionHint")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        connect_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        connect_btn.setText("Connect")
        from .icons import current_icon_fg

        connect_btn.setIcon(
            fa_icon(
                "plug",
                size=14,
                color_key=current_icon_fg(),
                text_gap=BUTTON_ICON_TEXT_GAP,
            )
        )
        buttons.accepted.connect(self._accept_manual_or_selected)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._discovery = BroadcastDiscovery(self)
        self._discovery.broadcaster_found.connect(self._add_broadcaster)
        self._known: dict[str, BroadcasterInfo] = {}
        configure_modal_dialog(self)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._restart_discovery()

    def closeEvent(self, event) -> None:
        self._discovery.stop()
        super().closeEvent(event)

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("statInlineLabel")
        return label

    def _restart_discovery(self) -> None:
        self._list.clear()
        self._known.clear()
        self._status.setText("Searching for broadcasters…")
        self._discovery.stop()
        self._discovery = BroadcastDiscovery(self)
        self._discovery.broadcaster_found.connect(self._add_broadcaster)
        self._discovery.start()

    def _add_broadcaster(self, info: BroadcasterInfo) -> None:
        key = f"{info.host}:{info.port}"
        if key in self._known:
            return
        self._known[key] = info
        item = QListWidgetItem(f"{info.name} ({info.host}:{info.port})")
        item.setData(Qt.ItemDataRole.UserRole, info)
        self._list.addItem(item)
        self._status.setText(f"Found {len(self._known)} broadcaster(s).")

    def _accept_selection(self, item: QListWidgetItem) -> None:
        info = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(info, BroadcasterInfo):
            self.connect_requested.emit(info.host, info.port)
            self.accept()

    def _accept_manual_or_selected(self) -> None:
        item = self._list.currentItem()
        if item is not None:
            info = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(info, BroadcasterInfo):
                self.connect_requested.emit(info.host, info.port)
                self.accept()
                return
        host = self.host_input.text().strip()
        if not host:
            self._status.setText("Select a broadcaster or enter an IP address.")
            return
        try:
            port = int(self.port_input.text().strip() or "8765")
        except ValueError:
            self._status.setText("Port must be a number.")
            return
        self.connect_requested.emit(host, port)
        self.accept()
