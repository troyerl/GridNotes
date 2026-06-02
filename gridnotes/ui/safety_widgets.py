"""Safety Index breakdown widgets for the driver details panel."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .a11y import set_accessible
from .appearance import get_theme_id
from ..safety.safety_index import MIN_RACES_FOR_SCORE, SafetyIndex, tier_color_hex
from ..safety.safety_trend import SafetyTrend
from .theme import safety_progress_bar_style


def _bar_color(tier: str) -> str:
    return tier_color_hex(tier)


def _tier_label(tier: str) -> str:
    return {
        "low": "LOW",
        "moderate": "MODERATE",
        "high": "HIGH",
        "unknown": "—",
    }.get(tier, "—")


class SafetyIndexPanel(QGroupBox):
    """Visual breakdown of Grid Safety Index in the details panel."""

    guide_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Grid Safety Index", parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.score_label = QLabel("—")
        self.score_label.setObjectName("safetyScoreValue")
        self.tier_label = QLabel("")
        self.tier_label.setObjectName("safetyTierBadge")
        self.trend_label = QLabel("")
        self.trend_label.setObjectName("safetyTrendArrow")
        header.addWidget(self.score_label)
        header.addWidget(self.trend_label)
        header.addWidget(self.tier_label)
        header.addStretch()
        self.btn_guide = QPushButton("Guide")
        self.btn_guide.setObjectName("hintLinkBtn")
        self.btn_guide.setFlat(True)
        self.btn_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guide.setToolTip("Open scouting guide (Safety Index, form arrows, marks)")
        self.btn_guide.clicked.connect(self.guide_requested.emit)
        header.addWidget(self.btn_guide)
        layout.addLayout(header)
        set_accessible(
            self.btn_guide,
            "Scouting guide",
            "Open reference for Safety Index, form arrows, and marks.",
        )

        self.overall_bar = QProgressBar()
        self.overall_bar.setObjectName("safetyOverallBar")
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setTextVisible(True)
        self.overall_bar.setFormat("%v / 100")
        self.overall_bar.setFixedHeight(22)
        layout.addWidget(self.overall_bar)

        self.profile_label = QLabel("—")
        self.profile_label.setObjectName("safetyProfile")
        self.profile_label.setWordWrap(True)
        layout.addWidget(self.profile_label)

        components = QFrame()
        components.setObjectName("safetyComponents")
        grid = QGridLayout(components)
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self._component_bars: dict[str, QProgressBar] = {}
        self._component_values: dict[str, QLabel] = {}

        for row, (key, title) in enumerate(
            [
                ("incidents", "Incidents"),
                ("dnf", "DNF rate"),
                ("pos", "Pos loss"),
            ]
        ):
            name_lbl = QLabel(title)
            name_lbl.setObjectName("safetyComponentLabel")
            grid.addWidget(name_lbl, row, 0)

            bar = QProgressBar()
            bar.setObjectName("safetyComponentBar")
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(14)
            grid.addWidget(bar, row, 1)

            val_lbl = QLabel("—")
            val_lbl.setObjectName("safetyComponentValue")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(val_lbl, row, 2)

            self._component_bars[key] = bar
            self._component_values[key] = val_lbl

        grid.setColumnStretch(1, 1)
        layout.addWidget(components)

        self.reasons_label = QLabel("")
        self.reasons_label.setObjectName("sectionHint")
        self.reasons_label.setWordWrap(True)
        layout.addWidget(self.reasons_label)

        self._last_safety: SafetyIndex | None = None
        self._last_trend: SafetyTrend | None = None

    def refresh_theme(self) -> None:
        if self._last_safety is not None:
            self.update_safety(self._last_safety, self._last_trend)

    def update_safety(
        self,
        safety: SafetyIndex,
        trend: SafetyTrend | None = None,
    ) -> None:
        self._last_safety = safety
        self._last_trend = trend
        color = _bar_color(safety.tier)

        if safety.tier == "unknown":
            self.score_label.setText("—")
            self.tier_label.setText("")
            self.trend_label.setText("")
            self.trend_label.setToolTip("")
            self.overall_bar.setValue(0)
            self.overall_bar.setFormat(f"Need {MIN_RACES_FOR_SCORE}+ races")
            self.profile_label.setText(safety.profile)
            for bar in self._component_bars.values():
                bar.setValue(0)
            self._component_values["incidents"].setText("—")
            self._component_values["dnf"].setText("—")
            self._component_values["pos"].setText("—")
            self.reasons_label.setText("")
            return

        self.score_label.setText(f"{safety.score:.0f}")
        self.score_label.setStyleSheet(f"color: {color};")
        if trend is not None and trend.arrow:
            self.trend_label.setText(trend.arrow)
            trend_color = trend.color_hex if trend.direction in ("improving", "worsening") else color
            self.trend_label.setStyleSheet(
                f"color: {trend_color}; font-size: 18px; font-weight: 700; padding: 0 4px;"
            )
            self.trend_label.setToolTip("\n".join(trend.tooltip_lines()))
        else:
            self.trend_label.setText("")
            self.trend_label.setStyleSheet("")
            self.trend_label.setToolTip("")
        self.tier_label.setText(_tier_label(safety.tier))
        self.tier_label.setStyleSheet(
            f"color: {color}; font-weight: 700; padding-left: 8px;"
        )

        self.overall_bar.setValue(int(round(safety.score)))
        self.overall_bar.setFormat("%v / 100")
        self.overall_bar.setStyleSheet(
            safety_progress_bar_style(get_theme_id(), color)
        )

        self.profile_label.setText(safety.profile)

        inc_pct = int(round(safety.incidents_norm * 100))
        dnf_pct = int(round(safety.dnf_norm * 100))
        pos_pct = int(round(safety.pos_norm * 100))

        self._component_bars["incidents"].setValue(inc_pct)
        self._component_bars["dnf"].setValue(dnf_pct)
        self._component_bars["pos"].setValue(pos_pct)

        inc_text = f"{safety.avg_inc:.1f}/race" if safety.avg_inc is not None else "—"
        self._component_values["incidents"].setText(f"{inc_text} ({inc_pct}%)")

        dnf_text = f"{safety.dnf_rate * 100:.0f}%"
        self._component_values["dnf"].setText(f"{dnf_text} ({dnf_pct}%)")

        if safety.avg_pos_delta is not None:
            pos_text = f"{safety.avg_pos_delta:+.1f}"
        else:
            pos_text = "—"
        self._component_values["pos"].setText(f"{pos_text} ({pos_pct}%)")

        if safety.reasons:
            self.reasons_label.setText(" · ".join(safety.reasons))
        else:
            self.reasons_label.setText("No major risk factors")
