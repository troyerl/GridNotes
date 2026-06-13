"""Inline driver detail expansion for Live Mode and Grid Walk."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..data.driver_models import format_head_to_head_record
from ..data.note_tags import chip_label, load_note_tags
from ..safety.safety_index import SafetyIndex, empty_safety
from ..safety.safety_trend import SafetyTrend
from .a11y import set_accessible
from .icons import set_button_fa_icon
from .safety_widgets import SafetyIndexPanel
from .theme import configure_widget_scrollbars


class LiveDriverExpandPanel(QFrame):
    """Expanded scouting details shown below a live card or grid row."""

    save_requested = pyqtSignal(str)
    preference_requested = pyqtSignal(object)  # int | None
    scouting_guide_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveDriverExpandPanel")
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("driverMeta")
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        stats = QGridLayout()
        stats.setHorizontalSpacing(16)
        stats.setVerticalSpacing(4)
        self._stat_labels: dict[str, QLabel] = {}
        for row_idx, (key, title) in enumerate(
            [
                ("together", "Raced together"),
                ("vs_you", "You vs them"),
                ("stats_scope", "Stats"),
                ("races", "Races in book"),
                ("avg_finish", "Avg finish"),
                ("last_irating", "Last iRating"),
                ("avg_pos_delta", "Avg +/- pos"),
                ("dnfs", "DNFs"),
            ]
        ):
            title_lbl = QLabel(f"{title}:")
            title_lbl.setObjectName("statInlineLabel")
            stats.addWidget(title_lbl, row_idx // 2, (row_idx % 2) * 2)
            value_lbl = QLabel("—")
            value_lbl.setObjectName("statValue")
            value_lbl.setWordWrap(True)
            stats.addWidget(value_lbl, row_idx // 2, (row_idx % 2) * 2 + 1)
            self._stat_labels[key] = value_lbl
        layout.addLayout(stats)

        self.dnf_breakdown_label = QLabel("")
        self.dnf_breakdown_label.setObjectName("statValue")
        self.dnf_breakdown_label.setWordWrap(True)
        layout.addWidget(self.dnf_breakdown_label)

        self.safety_panel = SafetyIndexPanel()
        self.safety_panel.guide_requested.connect(self.scouting_guide_requested.emit)
        layout.addWidget(self.safety_panel)

        notes_group = QGroupBox("Scouting notes")
        notes_group.setFlat(True)
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setSpacing(8)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "e.g. Aggressive on restarts, gives room, weak under pressure…"
        )
        self.notes_edit.setMinimumHeight(88)
        self.notes_edit.setMaximumHeight(140)
        configure_widget_scrollbars(self.notes_edit, single_step=20, page_step=80)
        notes_layout.addWidget(self.notes_edit)

        self.templates_host = QWidget()
        self.templates_grid = QGridLayout(self.templates_host)
        self.templates_grid.setContentsMargins(0, 0, 0, 0)
        self.templates_grid.setHorizontalSpacing(8)
        self.templates_grid.setVerticalSpacing(8)
        notes_layout.addWidget(self.templates_host)
        layout.addWidget(notes_group)

        pref_group = QGroupBox("How was racing with them?")
        pref_group.setFlat(True)
        pref_layout = QHBoxLayout(pref_group)
        self.btn_like = QPushButton("Liked")
        set_button_fa_icon(self.btn_like, "thumbs-up", text="Liked")
        self.btn_like.setObjectName("prefLike")
        self.btn_like.setCheckable(True)
        self.btn_like.clicked.connect(lambda: self.preference_requested.emit(1))
        pref_layout.addWidget(self.btn_like)
        self.btn_dislike = QPushButton("Didn't like")
        set_button_fa_icon(self.btn_dislike, "thumbs-down", text="Didn't like")
        self.btn_dislike.setObjectName("prefDislike")
        self.btn_dislike.setCheckable(True)
        self.btn_dislike.clicked.connect(lambda: self.preference_requested.emit(-1))
        pref_layout.addWidget(self.btn_dislike)
        self.btn_clear = QPushButton("Clear")
        set_button_fa_icon(self.btn_clear, "eraser", text="Clear")
        self.btn_clear.clicked.connect(lambda: self.preference_requested.emit(None))
        pref_layout.addWidget(self.btn_clear)
        layout.addWidget(pref_group)

        action_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("sectionHint")
        action_row.addWidget(self.status_label, stretch=1)
        self.btn_save = QPushButton("Save notes")
        set_button_fa_icon(self.btn_save, "floppy-disk", text="Save notes")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._emit_save)
        action_row.addWidget(self.btn_save)
        layout.addLayout(action_row)

        set_accessible(self.btn_save, "Save notes", "Save scouting notes for this driver.")
        self._rebuild_template_buttons()

    def _emit_save(self) -> None:
        self.save_requested.emit(self.notes_edit.toPlainText())

    def _rebuild_template_buttons(self) -> None:
        grid = self.templates_grid
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        tags = load_note_tags()
        if not tags:
            self.templates_host.setVisible(False)
            return

        self.templates_host.setVisible(True)
        for i, tag in enumerate(tags[:6]):
            append_text = tag.append_text()
            btn = QPushButton(chip_label(tag.label))
            btn.setObjectName("chipBtn")
            btn.setToolTip(f"Append “{append_text}” to notes")
            btn.clicked.connect(
                lambda _=False, t=append_text: self._append_template(t)
            )
            grid.addWidget(btn, i // 2, i % 2)

    def _append_template(self, text: str) -> None:
        addition = text.strip()
        if not addition:
            return
        existing = self.notes_edit.toPlainText()
        if existing.strip():
            self.notes_edit.setPlainText(existing.rstrip() + "\n" + addition)
        else:
            self.notes_edit.setPlainText(addition)
        self.notes_edit.setFocus()

    def set_stat(self, key: str, value: str) -> None:
        label = self._stat_labels.get(key)
        if label is not None:
            label.setText(value or "—")

    def set_preference(self, pref: int | None) -> None:
        self.btn_like.setChecked(pref == 1)
        self.btn_dislike.setChecked(pref == -1)
        for btn, selected in ((self.btn_like, pref == 1), (self.btn_dislike, pref == -1)):
            btn.setProperty("selected", selected)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_saved_feedback(self, message: str = "Saved") -> None:
        self.status_label.setText(message)

    def clear_saved_feedback(self) -> None:
        self.status_label.clear()

    def populate(
        self,
        *,
        meta_text: str,
        notes: str,
        pref: int | None,
        series: str | None,
        stats_scope: str | None = None,
        avg_finish,
        races: int,
        last_irating,
        avg_pos_delta,
        dnfs: int,
        dnf_breakdown: str,
        safety: SafetyIndex | None,
        safety_trend: SafetyTrend | None = None,
        together_races: int | None = None,
        head_to_head: tuple[int, int, int] | None = None,
    ) -> None:
        self.meta_label.setText(meta_text)
        self.notes_edit.setPlainText(notes or "")
        self.set_preference(pref)
        if together_races is None:
            self.set_stat("together", "—")
        elif together_races <= 0:
            self.set_stat("together", "0")
        else:
            self.set_stat("together", str(together_races))
        if head_to_head is None:
            self.set_stat("vs_you", "—")
        else:
            self.set_stat("vs_you", format_head_to_head_record(*head_to_head))
        if stats_scope:
            self.set_stat("stats_scope", stats_scope)
        elif series:
            self.set_stat("stats_scope", series)
        else:
            self.set_stat("stats_scope", "—")
        self.set_stat("races", str(races) if races else "—")
        self.set_stat(
            "avg_finish",
            f"{avg_finish:.1f}" if avg_finish is not None else "—",
        )
        self.set_stat(
            "last_irating",
            str(last_irating) if last_irating is not None else "—",
        )
        self.set_stat(
            "avg_pos_delta",
            f"{avg_pos_delta:+.1f}" if avg_pos_delta is not None else "—",
        )
        self.set_stat("dnfs", str(dnfs) if dnfs else "—")
        self.dnf_breakdown_label.setText(
            f"DNF breakdown: {dnf_breakdown}" if dnf_breakdown else ""
        )
        self.dnf_breakdown_label.setVisible(bool(dnf_breakdown))
        self.safety_panel.update_safety(safety or empty_safety(), safety_trend)
        self.clear_saved_feedback()
        self._rebuild_template_buttons()
