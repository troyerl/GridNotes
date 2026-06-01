"""High-contrast Live Session view for in-race scouting at a glance."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .safety_index import SafetyIndex, empty_safety, tier_color_hex, tier_label, unknown_history_message
from .session_kind import session_kind_label
from .theme import configure_scroll_area


class LiveDriverCard(QFrame):
    """Single driver card in Live Mode."""

    clicked = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveDriverCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cust_id: int | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)
        self.name_label = QLabel("—")
        self.name_label.setObjectName("liveDriverName")
        left.addWidget(self.name_label)

        self.profile_label = QLabel("")
        self.profile_label.setObjectName("liveVerdict")
        self.profile_label.setWordWrap(True)
        left.addWidget(self.profile_label)
        layout.addLayout(left, stretch=3)

        stats = QGridLayout()
        stats.setHorizontalSpacing(20)
        stats.setVerticalSpacing(2)

        for col, (key, title) in enumerate(
            [("inc", "Avg Inc"), ("dnf", "DNF"), ("sr", "Last SR"), ("note", "Note")]
        ):
            title_lbl = QLabel(title)
            title_lbl.setObjectName("liveStatTitle")
            stats.addWidget(title_lbl, 0, col)

            val_lbl = QLabel("—")
            val_lbl.setObjectName("liveStatValue")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stats.addWidget(val_lbl, 1, col)
            setattr(self, f"_{key}_value", val_lbl)

        layout.addLayout(stats, stretch=2)

        score_col = QVBoxLayout()
        score_col.setSpacing(2)
        score_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        score_title = QLabel("Safety Index")
        score_title.setObjectName("liveStatTitle")
        score_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_col.addWidget(score_title)

        self.score_label = QLabel("—")
        self.score_label.setObjectName("liveScoreValue")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_col.addWidget(self.score_label)

        self.tier_label = QLabel("")
        self.tier_label.setObjectName("liveTierLabel")
        self.tier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_col.addWidget(self.tier_label)
        layout.addLayout(score_col)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._cust_id is not None:
            self.clicked.emit(self._cust_id)
        super().mousePressEvent(event)

    def set_driver(
        self,
        *,
        cust_id: int,
        name: str,
        safety: SafetyIndex,
        avg_inc,
        last_sr,
        has_note: bool,
        pref: int | None,
    ) -> None:
        self._cust_id = cust_id
        self.name_label.setText(name or "Unknown")

        if safety.tier == "unknown":
            self.profile_label.setText(unknown_history_message(safety.total_races))
            self.score_label.setText("—")
            self.score_label.setStyleSheet("")
            self.tier_label.setText("")
            self.setProperty("risk", "unknown")
        else:
            self.profile_label.setText(safety.profile)
            color = tier_color_hex(safety.tier)
            self.score_label.setText(f"{safety.score:.0f}")
            self.score_label.setStyleSheet(f"color: {color};")
            self.tier_label.setText(tier_label(safety.tier))
            self.tier_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")
            risk_prop = (
                "high" if safety.risky else ("moderate" if safety.tier == "moderate" else "low")
            )
            self.setProperty("risk", risk_prop)

        inc_text = f"{avg_inc:.1f}" if avg_inc is not None else "—"
        self._inc_value.setText(inc_text)

        if safety.total_races > 0:
            self._dnf_value.setText(f"{safety.dnf_rate * 100:.0f}%")
        else:
            self._dnf_value.setText("—")

        sr_val = last_sr
        if sr_val is not None:
            try:
                self._sr_value.setText(f"{float(sr_val):.2f}")
            except (TypeError, ValueError):
                self._sr_value.setText("—")
        else:
            self._sr_value.setText("—")

        self._note_value.setText("+" if has_note else "")

        if pref == 1:
            self.setProperty("pref", "like")
        elif pref == -1:
            self.setProperty("pref", "dislike")
        else:
            self.setProperty("pref", "")

        self.style().unpolish(self)
        self.style().polish(self)


class LiveSessionView(QWidget):
    """Full-width live session panel with large-font driver cards."""

    driver_clicked = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveSessionRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("liveSessionHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 12)

        title = QLabel("Live Session")
        title.setObjectName("liveSessionTitle")
        header_layout.addWidget(title)

        self.session_label = QLabel("")
        self.session_label.setObjectName("liveSessionMeta")
        header_layout.addWidget(self.session_label)
        header_layout.addStretch()

        self.count_label = QLabel("")
        self.count_label.setObjectName("liveSessionMeta")
        header_layout.addWidget(self.count_label)
        root.addWidget(header)

        self.offline_label = QLabel(
            "Not connected to iRacing — join a session to see live driver cards."
        )
        self.offline_label.setObjectName("liveOfflineHint")
        self.offline_label.setWordWrap(True)
        self.offline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.offline_label)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("liveSessionScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_container.setObjectName("liveCardsContainer")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(16, 8, 16, 16)
        self.cards_layout.setSpacing(10)

        self.scroll.setWidget(self.cards_container)
        configure_scroll_area(self.scroll, page_step=120)
        root.addWidget(self.scroll, stretch=1)

        self._cards: list[LiveDriverCard] = []
        self._last_entry_key: tuple | None = None

    def set_session_info(
        self,
        *,
        connected: bool,
        subsession_id: int,
        driver_count: int,
        session_kind: str = "race",
        persist_drivers: bool = True,
    ) -> None:
        if connected:
            self.offline_label.setVisible(False)
            self.scroll.setVisible(True)
            label = session_kind_label(session_kind)
            if subsession_id:
                self.session_label.setText(f"Session #{subsession_id} · {label}")
            else:
                self.session_label.setText(label)
            if persist_drivers:
                self.count_label.setText(f"{driver_count} drivers")
            else:
                self.count_label.setText(f"{driver_count} drivers · scouting only (not saved yet)")
        else:
            self.offline_label.setVisible(True)
            self.scroll.setVisible(False)
            self.session_label.setText("")
            self.count_label.setText("")

    def rebuild_if_changed(self, entries: list[dict]) -> None:
        entry_key = tuple(
            (
                e.get("cust_id"),
                e.get("name"),
                e.get("total_races"),
                e.get("pref"),
                round(getattr(e.get("safety"), "score", -1), 1)
                if e.get("safety") is not None
                else -1,
            )
            for e in entries
        )
        if entry_key == self._last_entry_key:
            return
        self._last_entry_key = entry_key
        self.rebuild(entries)

    def rebuild(self, entries: list[dict]) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        if not entries:
            empty = QLabel("No drivers detected in this session.")
            empty.setObjectName("liveOfflineHint")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.cards_layout.addWidget(empty)
            self.cards_layout.addStretch()
            return

        for entry in entries:
            safety = entry.get("safety")
            if not isinstance(safety, SafetyIndex):
                safety = empty_safety()
            card = LiveDriverCard()
            card.set_driver(
                cust_id=entry["cust_id"],
                name=entry.get("name") or "Unknown",
                safety=safety,
                avg_inc=entry.get("avg_inc"),
                last_sr=entry.get("last_sr"),
                has_note=bool(entry.get("has_note")),
                pref=entry.get("pref"),
            )
            card.clicked.connect(self.driver_clicked.emit)
            self.cards_layout.addWidget(card)
            self._cards.append(card)

        self.cards_layout.addStretch()
