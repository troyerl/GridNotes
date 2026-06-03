"""High-contrast Live Session view for in-race scouting at a glance."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..iracing.session_context import format_session_context_banner
from ..safety.safety_index import SafetyIndex, empty_safety, tier_color_hex, tier_label
from ..safety.safety_trend import SafetyTrend
from ..iracing.session_kind import session_kind_label
from .a11y import set_accessible
from .grid_walk_view import GridWalkView
from .theme import configure_scroll_area


class LiveDriverCard(QFrame):
    """Single driver card in Live Mode."""

    clicked = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveDriverCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._cust_id: int | None = None
        self._driver_name = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        self.name_label = QLabel("—")
        self.name_label.setObjectName("liveDriverName")
        name_row.addWidget(self.name_label, stretch=1)
        self.new_label = QLabel("New")
        self.new_label.setObjectName("liveNewBadge")
        self.new_label.setVisible(False)
        name_row.addWidget(self.new_label)
        left.addLayout(name_row)

        self.profile_label = QLabel("")
        self.profile_label.setObjectName("liveVerdict")
        self.profile_label.setWordWrap(True)
        left.addWidget(self.profile_label)

        self.pref_label = QLabel("")
        self.pref_label.setObjectName("livePrefLabel")
        left.addWidget(self.pref_label)
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
        safety_trend: SafetyTrend | None = None,
        has_history: bool = True,
    ) -> None:
        self._cust_id = cust_id
        self._driver_name = name or "—"
        self.name_label.setText(self._driver_name)
        self.new_label.setVisible(not has_history)

        if safety.tier == "unknown":
            self.profile_label.setText("")
            self.score_label.setText("")
            self.score_label.setStyleSheet("")
            self.tier_label.setText("")
            self.setProperty("risk", "")
        else:
            self.profile_label.setText(safety.profile)
            color = tier_color_hex(safety.tier)
            score_text = f"{safety.score:.0f}"
            if safety_trend is not None and safety_trend.arrow:
                score_text = f"{score_text} {safety_trend.arrow}"
            self.score_label.setText(score_text)
            if safety_trend is not None and safety_trend.direction in ("improving", "worsening"):
                color = safety_trend.color_hex
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

        self._note_value.setText("Yes" if has_note else "—")

        if pref == 1:
            self.setProperty("pref", "like")
            self.pref_label.setText("Liked")
        elif pref == -1:
            self.setProperty("pref", "dislike")
            self.pref_label.setText("Disliked")
        else:
            self.setProperty("pref", "")
            self.pref_label.setText("")

        tier_text = tier_label(safety.tier) if safety.tier != "unknown" else ""
        a11y_name = (
            f"{self._driver_name}, Safety {tier_text}"
            if tier_text
            else self._driver_name
        )
        set_accessible(
            self,
            a11y_name,
            "Press Enter or Space to open scouting notes for this driver.",
        )

        self.style().unpolish(self)
        self.style().polish(self)


class LiveSessionView(QWidget):
    """Full-width live session panel with large-font driver cards."""

    driver_clicked = pyqtSignal(int)
    audio_spotter_changed = pyqtSignal(bool)
    grid_walk_toggled = pyqtSignal(bool)
    scouting_guide_requested = pyqtSignal()

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

        self.chk_audio_spotter = QCheckBox("Audio spotter")
        self.chk_audio_spotter.setObjectName("liveAudioSpotter")
        self.chk_audio_spotter.setToolTip(
            "Optional — off by default. When enabled, speaks a warning if a "
            "disliked or high-risk driver is within 1.5 seconds behind you "
            "(Windows only, green-flag running)."
        )
        self.chk_audio_spotter.stateChanged.connect(self._on_audio_spotter_changed)
        header_layout.addWidget(self.chk_audio_spotter)

        self.btn_grid_walk = QPushButton("Grid Walk")
        self.btn_grid_walk.setObjectName("liveGridWalkBtn")
        self.btn_grid_walk.setCheckable(True)
        self.btn_grid_walk.setToolTip(
            "Show starting-grid order with risk marks — ideal between qualifying and the race."
        )
        self.btn_grid_walk.clicked.connect(self._on_grid_walk_toggled)
        header_layout.addWidget(self.btn_grid_walk)

        self.btn_scouting_guide = QPushButton("Guide")
        self.btn_scouting_guide.setObjectName("hintLinkBtn")
        self.btn_scouting_guide.setFlat(True)
        self.btn_scouting_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scouting_guide.setToolTip(
            "Safety Index tiers, form arrows (↗ ↘ →), and mark meanings"
        )
        self.btn_scouting_guide.clicked.connect(self.scouting_guide_requested.emit)
        header_layout.addWidget(self.btn_scouting_guide)

        self.count_label = QLabel("")
        self.count_label.setObjectName("liveSessionMeta")
        header_layout.addWidget(self.count_label)
        root.addWidget(header)

        self.context_banner = QLabel("")
        self.context_banner.setObjectName("liveSessionContext")
        self.context_banner.setWordWrap(True)
        self.context_banner.setContentsMargins(20, 0, 20, 4)
        root.addWidget(self.context_banner)

        self.at_glance_label = QLabel("")
        self.at_glance_label.setObjectName("liveSessionAtGlance")
        self.at_glance_label.setWordWrap(True)
        self.at_glance_label.setContentsMargins(20, 0, 20, 8)
        root.addWidget(self.at_glance_label)

        self.offline_label = QLabel(
            "Not connected to iRacing — join a session to see live driver cards."
        )
        self.offline_label.setObjectName("liveOfflineHint")
        self.offline_label.setWordWrap(True)
        self.offline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.offline_label)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("liveContentStack")

        self.cards_page = QWidget()
        cards_page_layout = QVBoxLayout(self.cards_page)
        cards_page_layout.setContentsMargins(0, 0, 0, 0)
        cards_page_layout.setSpacing(0)

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
        cards_page_layout.addWidget(self.scroll)

        self.content_stack.addWidget(self.cards_page)

        self.grid_walk_view = GridWalkView()
        self.grid_walk_view.driver_clicked.connect(self.driver_clicked.emit)
        self.content_stack.addWidget(self.grid_walk_view)

        root.addWidget(self.content_stack, stretch=1)

        self._cards: list[LiveDriverCard] = []
        self._last_entry_key: tuple | None = None
        self._grid_walk_active = False
        set_accessible(
            self.scroll,
            "Live session drivers",
            "Scrollable list of driver cards. Tab to a card and press Enter to open notes.",
        )
        set_accessible(
            self.chk_audio_spotter,
            "Audio spotter",
            "Speak warnings when a flagged driver is close behind during a green-flag run.",
        )
        set_accessible(
            self.btn_grid_walk,
            "Grid Walk",
            "Toggle starting-grid view for pre-race review.",
        )
        set_accessible(
            self.btn_scouting_guide,
            "Scouting guide",
            "Open reference for Safety Index, form arrows, and marks.",
        )

    def _on_audio_spotter_changed(self, _state: int) -> None:
        self.audio_spotter_changed.emit(self.chk_audio_spotter.isChecked())

    def is_audio_spotter_enabled(self) -> bool:
        return self.chk_audio_spotter.isChecked()

    def set_audio_spotter_enabled(self, enabled: bool) -> None:
        self.chk_audio_spotter.blockSignals(True)
        self.chk_audio_spotter.setChecked(enabled)
        self.chk_audio_spotter.blockSignals(False)

    def _on_grid_walk_toggled(self) -> None:
        self.set_grid_walk_mode(self.btn_grid_walk.isChecked())

    def is_grid_walk_mode(self) -> bool:
        return self._grid_walk_active

    def set_grid_walk_mode(self, active: bool, *, emit: bool = True) -> None:
        self._grid_walk_active = active
        self.btn_grid_walk.blockSignals(True)
        self.btn_grid_walk.setChecked(active)
        self.btn_grid_walk.blockSignals(False)
        self.btn_grid_walk.setProperty("active", active)
        self.btn_grid_walk.style().unpolish(self.btn_grid_walk)
        self.btn_grid_walk.style().polish(self.btn_grid_walk)
        self.content_stack.setCurrentIndex(1 if active else 0)
        if emit:
            self.grid_walk_toggled.emit(active)

    def update_grid(
        self,
        slots: list[dict],
        player_cust_id: int | None,
        entries_by_cust: dict[int, dict],
        *,
        streamer_mode: bool = False,
    ) -> None:
        if not self._grid_walk_active:
            return
        self.grid_walk_view.rebuild(
            slots,
            player_cust_id,
            entries_by_cust,
            streamer_mode=streamer_mode,
        )

    def set_session_info(
        self,
        *,
        connected: bool,
        subsession_id: int,
        driver_count: int,
        session_kind: str = "race",
        persist_drivers: bool = True,
        context: dict[str, str] | None = None,
        at_glance: str = "",
    ) -> None:
        if connected:
            self.offline_label.setVisible(False)
            self.content_stack.setVisible(True)
            label = session_kind_label(session_kind)
            if subsession_id:
                self.session_label.setText(f"Session #{subsession_id} · {label}")
            else:
                self.session_label.setText(label)
            if persist_drivers:
                self.count_label.setText(f"{driver_count} drivers")
            else:
                self.count_label.setText(f"{driver_count} drivers · scouting only (not saved yet)")

            banner = format_session_context_banner(session_kind, context)
            self.context_banner.setText(banner)
            self.context_banner.setVisible(bool(banner))

            self.at_glance_label.setText(at_glance or "")
            self.at_glance_label.setVisible(bool(at_glance))
        else:
            self.offline_label.setVisible(True)
            self.content_stack.setVisible(False)
            self.session_label.setText("")
            self.count_label.setText("")
            self.context_banner.setText("")
            self.context_banner.setVisible(False)
            self.at_glance_label.setText("")
            self.at_glance_label.setVisible(False)

    def rebuild_if_changed(self, entries: list[dict]) -> None:
        if self._grid_walk_active:
            return
        entry_key = tuple(
            (
                e.get("cust_id"),
                e.get("name"),
                e.get("total_races"),
                e.get("pref"),
                e.get("has_history"),
                round(getattr(e.get("safety"), "score", -1), 1)
                if e.get("safety") is not None
                else -1,
                (e.get("safety_trend") or SafetyTrend("unknown", None, None, 0)).direction,
            )
            for e in entries
        )
        # Names change when streamer mode toggles; entry_key includes display name.
        if entry_key == self._last_entry_key:
            return
        self._last_entry_key = entry_key
        self.rebuild(entries)

    def rebuild(self, entries: list[dict]) -> None:
        if self._grid_walk_active:
            return
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
            trend = entry.get("safety_trend")
            if trend is not None and not isinstance(trend, SafetyTrend):
                trend = None
            card.set_driver(
                cust_id=entry["cust_id"],
                name=entry.get("name") or "—",
                safety=safety,
                avg_inc=entry.get("avg_inc"),
                last_sr=entry.get("last_sr"),
                has_note=bool(entry.get("has_note")),
                pref=entry.get("pref"),
                safety_trend=trend,
                has_history=bool(entry.get("has_history")),
            )
            card.clicked.connect(self.driver_clicked.emit)
            self.cards_layout.addWidget(card)
            self._cards.append(card)

        self.cards_layout.addStretch()
