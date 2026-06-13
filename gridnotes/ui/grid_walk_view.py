"""Grid Walk — starting-grid layout for pre-race scouting."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..data.leagues import league_membership_tooltip
from ..data.driver_models import format_live_session_at_glance
from ..privacy.streamer_mode import streamer_display_name
from ..safety.safety_index import SafetyIndex, tier_color_hex
from ..safety.safety_trend import SafetyTrend, combined_safety_tooltip
from .a11y import driver_mark_label, set_accessible
from .icons import apply_solid_font, driver_mark_glyphs, set_label_fa_icon, trend_rich_span
from .live_driver_expand import LiveDriverExpandPanel
from .theme import configure_scroll_area

# Even-side cars sit half a row back, like a real staggered grid.
_EVEN_COLUMN_STAGGER_PX = 20


def grid_highlight_positions(player_position: int) -> tuple[int | None, int | None]:
    """
    Grid neighbors to highlight for the player.

    Returns (ahead_in_column, beside_in_row). Example: P5 -> (3, 6).
    """
    beside = (
        player_position + 1
        if player_position % 2 == 1
        else player_position - 1
    )
    ahead = player_position - 2 if player_position > 2 else None
    return ahead, beside


class GridWalkRow(QFrame):
    """One car slot on the starting grid (left = odd, right = even)."""

    toggle_expand = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gridWalkRow")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._cust_id: int | None = None
        self._active = False
        self._expanded = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.summary_frame = QFrame()
        self.summary_frame.setObjectName("gridWalkSummary")
        self.summary_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self.summary_frame)
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

        self.new_label = QLabel("New")
        self.new_label.setObjectName("gridWalkNewBadge")
        self.new_label.setToolTip(
            "Not in your race book yet. Import results or scout this session to build history."
        )
        self.new_label.setVisible(False)
        layout.addWidget(self.new_label)

        self.league_label = QLabel("League")
        self.league_label.setObjectName("gridWalkLeagueBadge")
        self.league_label.setVisible(False)
        layout.addWidget(self.league_label)

        self.score_label = QLabel("")
        self.score_label.setObjectName("gridWalkScore")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.score_label.setFixedWidth(52)
        layout.addWidget(self.score_label)

        self.mark_label = QLabel("")
        self.mark_label.setObjectName("gridWalkMark")
        self.mark_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.mark_label)

        outer.addWidget(self.summary_frame)

        self.expand_panel = LiveDriverExpandPanel()
        outer.addWidget(self.expand_panel)

        self.summary_frame.mousePressEvent = self._summary_mouse_press  # type: ignore[method-assign]

    @property
    def cust_id(self) -> int | None:
        return self._cust_id

    def expand_signals(self) -> LiveDriverExpandPanel:
        return self.expand_panel

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.expand_panel.setVisible(expanded)
        self.setProperty("expanded", expanded)
        self.style().unpolish(self)
        self.style().polish(self)

    def _summary_mouse_press(self, event) -> None:
        if self._active and event.button() == Qt.MouseButton.LeftButton:
            self._activate()
        QFrame.mousePressEvent(self.summary_frame, event)

    def _activate(self) -> None:
        if self._active and self._cust_id is not None:
            self.toggle_expand.emit(self._cust_id)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            self._active
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space)
        ):
            self._activate()
            event.accept()
            return
        super().keyPressEvent(event)

    def clear_slot(self) -> None:
        self._cust_id = None
        self._active = False
        self.pos_label.setText("")
        self.name_label.setText("")
        self.new_label.setVisible(False)
        self.league_label.setVisible(False)
        self.score_label.setText("")
        self.score_label.setStyleSheet("")
        self.mark_label.setText("")
        self.setToolTip("")
        self.setProperty("role", "")
        self.setProperty("pref", "")
        self.setProperty("risky", "false")
        self.setProperty("side", "")
        self.setExpanded(False)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setVisible(False)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_slot(
        self,
        *,
        position: int,
        cust_id: int,
        name: str,
        pref: int | None,
        risky: bool,
        role: str,
        side: str,
        safety: SafetyIndex | None = None,
        safety_trend: SafetyTrend | None = None,
        has_history: bool = True,
        league_label: str = "",
    ) -> None:
        self._cust_id = cust_id
        self._active = True
        self.setVisible(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.pos_label.setText(f"P{position}")
        self.name_label.setText(name)
        self.new_label.setVisible(not has_history)
        if league_label:
            set_label_fa_icon(self.league_label, "trophy", pixel_size=12)
            self.league_label.setToolTip(league_membership_tooltip(league_label))
            self.league_label.setVisible(True)
        else:
            self.league_label.clear()
            self.league_label.setVisible(False)
            self.league_label.setToolTip("")

        if safety is not None and safety.tier != "unknown":
            score_text = f"{safety.score:.0f}"
            color = tier_color_hex(safety.tier)
            if safety_trend is not None and safety_trend.direction in (
                "improving",
                "worsening",
            ):
                color = safety_trend.color_hex
            if safety_trend is not None and safety_trend.icon_name:
                trend_color = (
                    safety_trend.color_hex
                    if safety_trend.direction in ("improving", "worsening")
                    else color
                )
                self.score_label.setTextFormat(Qt.TextFormat.RichText)
                self.score_label.setText(
                    f"{score_text}"
                    f"{trend_rich_span(safety_trend.direction, color=trend_color, pixel_size=12)}"
                )
            else:
                self.score_label.setTextFormat(Qt.TextFormat.PlainText)
                self.score_label.setText(score_text)
            self.score_label.setStyleSheet(f"color: {color}; font-weight: 800;")
            tooltip = combined_safety_tooltip(safety, safety_trend)
        else:
            self.score_label.setText("")
            self.score_label.setStyleSheet("")
            tooltip = (
                "Not in your book yet — tap after the race to add notes."
                if not has_history
                else ""
            )
        if league_label:
            league_tip = league_membership_tooltip(league_label)
            tooltip = f"{tooltip}\n{league_tip}" if tooltip else league_tip

        mark = driver_mark_glyphs(pref, risky)
        self.mark_label.setText(mark)
        if mark:
            apply_solid_font(self.mark_label, pixel_size=13)
            self.mark_label.setToolTip(driver_mark_label(pref, risky) or "")
        else:
            self.mark_label.setToolTip("")
        self.setToolTip(tooltip)

        self.setProperty("role", role)
        self.setProperty("pref", "like" if pref == 1 else ("dislike" if pref == -1 else ""))
        self.setProperty("risky", "true" if risky and pref != -1 else "false")
        self.setProperty("side", side)

        set_accessible(
            self,
            f"Grid position {position}, {side} side, {name}"
            + (f", {mark}" if mark else "")
            + (", league racer" if league_label else ""),
            "Press Enter to expand scouting details.",
        )

        self.style().unpolish(self)
        self.style().polish(self)


class GridWalkPairRow(QFrame):
    """One grid row: odd position on the left, even on the right (staggered)."""

    driver_expand_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gridWalkPairRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.left_row = GridWalkRow()
        self.left_row.toggle_expand.connect(self.driver_expand_requested.emit)
        layout.addWidget(self.left_row, stretch=1)

        lane = QFrame()
        lane.setObjectName("gridWalkLane")
        lane.setFixedWidth(2)
        lane.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        layout.addWidget(lane)

        self.right_host = QWidget()
        right_layout = QVBoxLayout(self.right_host)
        right_layout.setContentsMargins(0, _EVEN_COLUMN_STAGGER_PX, 0, 0)
        right_layout.setSpacing(0)
        self.right_row = GridWalkRow()
        self.right_row.toggle_expand.connect(self.driver_expand_requested.emit)
        right_layout.addWidget(self.right_row)
        right_layout.addStretch()
        layout.addWidget(self.right_host, stretch=1)

    def set_pair(
        self,
        *,
        left: dict | None,
        right: dict | None,
    ) -> None:
        if left is None:
            self.left_row.clear_slot()
        else:
            self.left_row.set_slot(**left, side="left")

        if right is None:
            self.right_row.clear_slot()
            self.right_host.setVisible(False)
        else:
            self.right_host.setVisible(True)
            self.right_row.set_slot(**right, side="right")

    @property
    def rows(self) -> list[GridWalkRow]:
        out: list[GridWalkRow] = []
        if self.left_row._active:
            out.append(self.left_row)
        if self.right_row._active:
            out.append(self.right_row)
        return out


class GridWalkView(QWidget):
    """Staggered starting grid with odd positions on the left."""

    driver_expand_requested = pyqtSignal(int)
    driver_expand_collapsed = pyqtSignal()
    expand_save_requested = pyqtSignal(int, str)
    expand_preference_requested = pyqtSignal(int, object)
    scouting_guide_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gridWalkRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("gridWalkSummary")
        self.summary_label.setWordWrap(True)
        self.summary_label.setContentsMargins(20, 12, 20, 4)
        root.addWidget(self.summary_label)

        self.at_glance_label = QLabel("")
        self.at_glance_label.setObjectName("gridWalkAtGlance")
        self.at_glance_label.setWordWrap(True)
        self.at_glance_label.setContentsMargins(20, 0, 20, 8)
        root.addWidget(self.at_glance_label)

        self.hint_label = QLabel(
            "The car ahead in your column and beside you on the grid are highlighted. "
            "Tap a car to expand scouting details."
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
        self.rows_layout.setSpacing(6)

        self.scroll.setWidget(self.rows_host)
        configure_scroll_area(self.scroll, page_step=96)
        root.addWidget(self.scroll, stretch=1)

        self._pair_rows: list[GridWalkPairRow] = []
        self._rows: list[GridWalkRow] = []
        self._last_key: tuple | None = None

        set_accessible(
            self.scroll,
            "Starting grid",
            "Two-column starting grid with odd positions on the left.",
        )

    def _wire_expand_panel(self, panel: LiveDriverExpandPanel, cust_id: int) -> None:
        panel.save_requested.connect(
            lambda text, cid=cust_id: self.expand_save_requested.emit(cid, text)
        )
        panel.preference_requested.connect(
            lambda pref, cid=cust_id: self.expand_preference_requested.emit(cid, pref)
        )
        panel.scouting_guide_requested.connect(self.scouting_guide_requested.emit)

    def set_row_expanded(self, cust_id: int, expanded: bool) -> None:
        for row in self._rows:
            if expanded:
                row.set_expanded(row.cust_id == cust_id)
            else:
                row.set_expanded(False)
        if expanded:
            for row in self._rows:
                if row.cust_id == cust_id:
                    self.scroll.ensureWidgetVisible(row, 80, 80)
                    break

    def populate_expanded_detail(self, cust_id: int, **payload) -> None:
        for row in self._rows:
            if row.cust_id == cust_id:
                row.expand_signals().populate(**payload)

    def show_expand_saved(self, cust_id: int, message: str = "Saved") -> None:
        for row in self._rows:
            if row.cust_id == cust_id:
                row.expand_signals().set_saved_feedback(message)

    def update_expanded_preference(self, cust_id: int, pref) -> None:
        for row in self._rows:
            if row.cust_id == cust_id:
                row.expand_signals().set_preference(pref)

    def _slot_payload(
        self,
        slot: dict,
        *,
        player_cust_id: int | None,
        player_position: int | None,
        entries_by_cust: dict[int, dict],
        streamer_mode: bool,
    ) -> dict:
        position = int(slot["position"])
        cust_id = int(slot["cust_id"])
        meta = entries_by_cust.get(cust_id, {})
        pref = meta.get("pref")
        safety = meta.get("safety")
        if streamer_mode:
            safety_obj = safety if isinstance(safety, SafetyIndex) else None
            name = str(
                meta.get("name") or streamer_display_name(cust_id, safety_obj)
            )
        else:
            name = str(slot.get("name") or f"Driver {cust_id}")
        risky = False
        if isinstance(safety, SafetyIndex):
            risky = safety.risky or safety.tier == "high"

        role = "default"
        if player_cust_id is not None and cust_id == player_cust_id:
            role = "you"
        elif player_position is not None:
            grid_ahead, grid_beside = grid_highlight_positions(player_position)
            if grid_ahead is not None and position == grid_ahead:
                role = "ahead"
            elif position == grid_beside:
                role = "beside"

        trend = meta.get("safety_trend")
        if trend is not None and not isinstance(trend, SafetyTrend):
            trend = None

        return {
            "position": position,
            "cust_id": cust_id,
            "name": name,
            "pref": pref if pref in (1, -1) else None,
            "risky": risky,
            "role": role,
            "safety": safety if isinstance(safety, SafetyIndex) else None,
            "safety_trend": trend,
            "has_history": bool(meta.get("has_history")),
            "league_label": str(meta.get("league_label") or ""),
        }

    def rebuild(
        self,
        slots: list[dict],
        player_cust_id: int | None,
        entries_by_cust: dict[int, dict],
        *,
        streamer_mode: bool = False,
    ) -> None:
        def _slot_cache_entry(slot: dict) -> tuple:
            cid = int(slot["cust_id"])
            meta = entries_by_cust.get(cid, {})
            safety = meta.get("safety")
            score = (
                round(safety.score, 1)
                if isinstance(safety, SafetyIndex) and safety.tier != "unknown"
                else -1
            )
            trend = meta.get("safety_trend")
            trend_dir = (
                trend.direction
                if isinstance(trend, SafetyTrend)
                else "unknown"
            )
            return (
                slot.get("position"),
                cid,
                player_cust_id,
                meta.get("pref"),
                meta.get("has_history"),
                score,
                trend_dir,
                meta.get("league_label") or "",
            )

        key = (
            streamer_mode,
            tuple(_slot_cache_entry(s) for s in slots),
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

        at_glance = format_live_session_at_glance(list(entries_by_cust.values()))
        self.at_glance_label.setText(at_glance)
        self.at_glance_label.setVisible(bool(at_glance))

        ahead_risk = beside_risk = False
        if player_position is not None:
            grid_ahead, grid_beside = grid_highlight_positions(player_position)
            neighbor_positions = {
                p for p in (grid_ahead, grid_beside) if p is not None
            }
            for slot in slots:
                pos = int(slot["position"])
                if pos not in neighbor_positions:
                    continue
                meta = entries_by_cust.get(int(slot["cust_id"]), {})
                pref = meta.get("pref")
                safety = meta.get("safety")
                risky = (
                    isinstance(safety, SafetyIndex)
                    and (safety.risky or safety.tier == "high")
                )
                if pref == -1 or risky:
                    if pos == grid_ahead:
                        ahead_risk = True
                    elif pos == grid_beside:
                        beside_risk = True

        if ahead_risk and beside_risk:
            self.hint_label.setText(
                "Warning: flagged drivers are ahead in your column and beside you on the grid."
            )
        elif ahead_risk:
            self.hint_label.setText(
                "Warning: a flagged driver is in the row ahead on your side of the grid."
            )
        elif beside_risk:
            self.hint_label.setText(
                "Warning: a flagged driver starts beside you on the grid."
            )
        else:
            self.hint_label.setText(
                "The car ahead in your column and beside you on the grid are highlighted. "
                "Tap a car to expand scouting details."
            )

        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._pair_rows.clear()
        self._rows.clear()

        if not slots:
            empty = QLabel("Starting grid not available yet — wait for the race session to load.")
            empty.setObjectName("liveOfflineHint")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rows_layout.addWidget(empty)
            self.rows_layout.addStretch()
            self.at_glance_label.setText("")
            self.at_glance_label.setVisible(False)
            return

        by_position = {
            int(slot["position"]): slot
            for slot in slots
            if slot.get("position") is not None
        }
        max_pos = max(by_position)
        pair_count = (max_pos + 1) // 2

        for pair_idx in range(pair_count):
            odd_pos = pair_idx * 2 + 1
            even_pos = odd_pos + 1

            left_payload = None
            if odd_pos in by_position:
                left_payload = self._slot_payload(
                    by_position[odd_pos],
                    player_cust_id=player_cust_id,
                    player_position=player_position,
                    entries_by_cust=entries_by_cust,
                    streamer_mode=streamer_mode,
                )

            right_payload = None
            if even_pos in by_position:
                right_payload = self._slot_payload(
                    by_position[even_pos],
                    player_cust_id=player_cust_id,
                    player_position=player_position,
                    entries_by_cust=entries_by_cust,
                    streamer_mode=streamer_mode,
                )

            if left_payload is None and right_payload is None:
                continue

            pair_row = GridWalkPairRow()
            pair_row.set_pair(left=left_payload, right=right_payload)
            pair_row.driver_expand_requested.connect(self.driver_expand_requested.emit)
            for row in pair_row.rows:
                if row.cust_id is not None:
                    self._wire_expand_panel(row.expand_signals(), int(row.cust_id))
            self.rows_layout.addWidget(pair_row)
            self._pair_rows.append(pair_row)
            self._rows.extend(pair_row.rows)

        self.rows_layout.addStretch()

        if player_position is not None:
            for row in self._rows:
                if row.pos_label.text() == f"P{player_position}":
                    self.scroll.ensureWidgetVisible(row, 80, 80)
                    break
