"""Grid Walk — starting-grid layout for pre-race scouting."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..privacy.streamer_mode import streamer_display_name
from ..safety.safety_index import SafetyIndex
from .a11y import driver_mark_label, set_accessible
from .theme import configure_scroll_area


class GridWalkRow(QFrame):
    """One row on the starting grid."""

    clicked = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gridWalkRow")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cust_id: int | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        self.pos_label = QLabel("P—")
        self.pos_label.setObjectName("gridWalkPos")
        self.pos_label.setFixedWidth(44)
        self.pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pos_label)

        self.name_label = QLabel("—")
        self.name_label.setObjectName("gridWalkName")
        layout.addWidget(self.name_label, stretch=1)

        self.mark_label = QLabel("")
        self.mark_label.setObjectName("gridWalkMark")
        self.mark_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.mark_label)

    def _activate(self) -> None:
        if self._cust_id is not None:
            self.clicked.emit(self._cust_id)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._activate()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._activate()
            event.accept()
            return
        super().keyPressEvent(event)

    def set_slot(
        self,
        *,
        position: int,
        cust_id: int,
        name: str,
        pref: int | None,
        risky: bool,
        role: str,
    ) -> None:
        self._cust_id = cust_id
        self.pos_label.setText(f"P{position}")
        self.name_label.setText(name)

        mark = driver_mark_label(pref, risky) or ""
        self.mark_label.setText(mark)

        self.setProperty("role", role)
        self.setProperty("pref", "like" if pref == 1 else ("dislike" if pref == -1 else ""))
        self.setProperty("risky", "true" if risky and pref != -1 else "false")

        set_accessible(
            self,
            f"Grid position {position}, {name}" + (f", {mark}" if mark else ""),
            "Press Enter to open scouting notes.",
        )

        self.style().unpolish(self)
        self.style().polish(self)


class GridWalkView(QWidget):
    """Vertical starting grid with emphasis on your row and adjacent cars."""

    driver_clicked = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gridWalkRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("gridWalkSummary")
        self.summary_label.setWordWrap(True)
        self.summary_label.setContentsMargins(20, 12, 20, 8)
        root.addWidget(self.summary_label)

        self.hint_label = QLabel(
            "Cars directly ahead and behind you are highlighted. "
            "Tap a row to open notes."
        )
        self.hint_label.setObjectName("sectionHint")
        self.hint_label.setWordWrap(True)
        self.hint_label.setContentsMargins(20, 0, 20, 8)
        root.addWidget(self.hint_label)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("gridWalkScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.rows_host = QWidget()
        self.rows_host.setObjectName("gridWalkRows")
        self.rows_layout = QVBoxLayout(self.rows_host)
        self.rows_layout.setContentsMargins(16, 4, 16, 16)
        self.rows_layout.setSpacing(4)

        self.scroll.setWidget(self.rows_host)
        configure_scroll_area(self.scroll, page_step=96)
        root.addWidget(self.scroll, stretch=1)

        self._rows: list[GridWalkRow] = []
        self._last_key: tuple | None = None

        set_accessible(self.scroll, "Starting grid", "Starting order with risk marks for each driver.")

    def rebuild(
        self,
        slots: list[dict],
        player_cust_id: int | None,
        entries_by_cust: dict[int, dict],
        *,
        streamer_mode: bool = False,
    ) -> None:
        key = (
            streamer_mode,
            tuple(
                (
                    s.get("position"),
                    s.get("cust_id"),
                    player_cust_id,
                    entries_by_cust.get(int(s["cust_id"]), {}).get("pref"),
                )
                for s in slots
            ),
        )
        if key == self._last_key:
            return
        self._last_key = key

        player_position: int | None = None
        for slot in slots:
            if player_cust_id is not None and int(slot["cust_id"]) == int(player_cust_id):
                player_position = int(slot["position"])
                break

        total = len(slots)
        if player_position is not None:
            self.summary_label.setText(
                f"You start P{player_position} of {total} — review neighbors before the green flag."
            )
        else:
            self.summary_label.setText(f"Starting grid — {total} drivers")

        ahead_risk = behind_risk = False
        if player_position is not None:
            for slot in slots:
                pos = int(slot["position"])
                if abs(pos - player_position) != 1:
                    continue
                meta = entries_by_cust.get(int(slot["cust_id"]), {})
                pref = meta.get("pref")
                safety = meta.get("safety")
                risky = (
                    isinstance(safety, SafetyIndex)
                    and (safety.risky or safety.tier == "high")
                )
                if pref == -1 or risky:
                    if pos < player_position:
                        ahead_risk = True
                    else:
                        behind_risk = True

        if ahead_risk and behind_risk:
            self.hint_label.setText(
                "Warning: flagged drivers are starting directly ahead and behind you."
            )
        elif ahead_risk:
            self.hint_label.setText("Warning: a flagged driver starts directly ahead of you.")
        elif behind_risk:
            self.hint_label.setText("Warning: a flagged driver starts directly behind you.")
        else:
            self.hint_label.setText(
                "Cars directly ahead and behind you are highlighted. Tap a row to open notes."
            )

        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()

        if not slots:
            empty = QLabel("Starting grid not available yet — wait for the race session to load.")
            empty.setObjectName("liveOfflineHint")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rows_layout.addWidget(empty)
            self.rows_layout.addStretch()
            return

        for slot in slots:
            position = int(slot["position"])
            cust_id = int(slot["cust_id"])
            meta = entries_by_cust.get(cust_id, {})
            pref = meta.get("pref")
            safety = meta.get("safety")
            if streamer_mode:
                safety_obj = safety if isinstance(safety, SafetyIndex) else None
                name = streamer_display_name(cust_id, safety_obj)
            else:
                name = str(slot.get("name") or f"Driver {cust_id}")
            risky = False
            if isinstance(safety, SafetyIndex):
                risky = safety.risky or safety.tier == "high"

            role = "default"
            if player_cust_id is not None and cust_id == player_cust_id:
                role = "you"
            elif player_position is not None and position == player_position - 1:
                role = "ahead"
            elif player_position is not None and position == player_position + 1:
                role = "behind"

            row = GridWalkRow()
            row.set_slot(
                position=position,
                cust_id=cust_id,
                name=name,
                pref=pref if pref in (1, -1) else None,
                risky=risky,
                role=role,
            )
            row.clicked.connect(self.driver_clicked.emit)
            self.rows_layout.addWidget(row)
            self._rows.append(row)

        self.rows_layout.addStretch()

        if player_position is not None:
            for row in self._rows:
                if row.pos_label.text() == f"P{player_position}":
                    self.scroll.ensureWidgetVisible(row, 80, 80)
                    break
