"""Application-wide visual theme (Qt stylesheets)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractScrollArea, QScrollArea, QScrollBar, QWidget

APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1a1e24;
    color: #e8eaed;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QLabel#appTitle {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#appSubtitle {
    font-size: 12px;
    color: #9aa3b2;
}

QLabel#sectionHint {
    font-size: 12px;
    color: #9aa3b2;
    padding: 2px 0 6px 0;
}

QLabel#emptyState {
    font-size: 13px;
    color: #9aa3b2;
    padding: 4px 0;
}

QLabel#statusBadge {
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 14px;
}

QLabel#statusBadge[status="connected"] {
    background-color: #1e3d32;
    color: #6ee7a8;
}

QLabel#statusBadge[status="waiting"] {
    background-color: #3d3420;
    color: #f5c26b;
}

QLabel#statusBadge[status="offline"] {
    background-color: #2a3038;
    color: #9aa3b2;
}

QGroupBox {
    font-size: 12px;
    font-weight: 600;
    color: #b8c0cc;
    border: 1px solid #323a46;
    border-radius: 8px;
    margin-top: 10px;
    padding: 14px 12px 10px 12px;
    background-color: #232831;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}

QFrame#panel {
    background-color: #232831;
    border: 1px solid #323a46;
    border-radius: 10px;
}

QLineEdit, QTextEdit, QTableWidget {
    background-color: #1a1e24;
    color: #e8eaed;
    border: 1px solid #3d4654;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: #3d6ebf;
}

QLineEdit:focus, QTextEdit:focus {
    border-color: #4a8af4;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #1e2228;
    color: #6b7280;
}

QPushButton {
    background-color: #2f3642;
    color: #e8eaed;
    border: 1px solid #3d4654;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #3a424f;
    border-color: #4d5868;
}

/* "Chip" buttons used for tags/templates */
QPushButton#chipBtn {
    padding: 2px 8px;
    min-height: 26px;
    border-radius: 14px;
    background-color: #2a3038;
    border: 1px solid #424b5a;
    font-weight: 600;
}

QPushButton#chipBtn:hover {
    background-color: #353d4a;
    border-color: #556377;
}

QPushButton#chipBtn:pressed {
    background-color: #252b34;
}

QPushButton:pressed {
    background-color: #252b34;
}

QPushButton:disabled {
    color: #6b7280;
    background-color: #232831;
}

QPushButton#primaryBtn {
    background-color: #2d6cdf;
    border-color: #3d7ef0;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #3a7aef;
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: #f08080;
    border-color: #5c3a3a;
}

QPushButton#dangerBtn:hover {
    background-color: #3a2525;
}

QPushButton#prefLike[selected="true"] {
    background-color: #2d5a3d;
    border-color: #4a9a62;
    color: #b8f0c8;
    font-weight: 600;
}

QPushButton#prefDislike[selected="true"] {
    background-color: #5a2d2d;
    border-color: #9a4a4a;
    color: #f0b8b8;
    font-weight: 600;
}

QCheckBox {
    spacing: 8px;
    color: #c8ced8;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4d5868;
    background-color: #1a1e24;
}

QCheckBox::indicator:checked {
    background-color: #2d6cdf;
    border-color: #3d7ef0;
}

QCheckBox:disabled {
    color: #6b7280;
}

QLabel#driverName {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#driverMeta {
    font-size: 12px;
    color: #9aa3b2;
    padding: 0;
    margin: 0;
}

QLabel#statLabel {
    font-size: 12px;
    font-weight: 600;
    color: #b8c0cc;
    padding: 8px 0 2px 0;
}

QLabel#statInlineLabel {
    font-size: 13px;
    font-weight: 600;
    color: #b8c0cc;
    padding: 0;
}

QLabel#seriesValue {
    font-size: 13px;
    font-weight: 500;
    color: #e8eaed;
    padding: 0 0 10px 0;
}

QLabel#statValue {
    font-size: 13px;
    font-weight: 500;
    color: #e8eaed;
    padding: 0;
    margin: 0;
}

QScrollArea#driverDetailScroll {
    background: transparent;
    border: none;
}

QScrollArea#driverDetailScroll > QWidget > QWidget {
    background: transparent;
}

QTableWidget {
    gridline-color: #2e3642;
    alternate-background-color: #1e232b;
}

QTableWidget#driverTable {
    font-size: 14px;
}

QTableWidget::item {
    padding: 4px 6px;
}

QTableWidget#driverTable::item {
    padding: 8px 10px;
}

/* Row hover is applied in code across the full row */
QTableWidget::item:focus,
QTableView::item:focus {
    outline: none;
}

QTableWidget::item:selected {
    background-color: #2d4a7a;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #2a3038;
    color: #b8c0cc;
    padding: 8px 6px;
    border: none;
    border-bottom: 2px solid #3d6ebf;
    font-weight: 600;
    font-size: 11px;
}

QTableWidget#driverTable QHeaderView::section {
    font-size: 12px;
    padding: 10px 8px;
    min-height: 32px;
}

QTableWidget#driverTable QHeaderView::section:hover {
    background-color: #353d4a;
    color: #ffffff;
    border-bottom: 2px solid #5a9af4;
}

QTableWidget#driverTable QHeaderView::section:pressed {
    background-color: #2d4a7a;
    color: #ffffff;
    border-bottom: 2px solid #4a8af4;
}

QSplitter::handle {
    background-color: #323a46;
    width: 2px;
}

/* Scrollbars — wider track and handle for easier grabbing */
QScrollBar:vertical {
    background: #1e2228;
    width: 16px;
    margin: 2px 0;
    border: none;
}

QScrollBar:horizontal {
    background: #1e2228;
    height: 16px;
    margin: 0 2px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #4d5868;
    border-radius: 7px;
    min-height: 48px;
    margin: 2px 3px;
}

QScrollBar::handle:horizontal {
    background: #4d5868;
    border-radius: 7px;
    min-width: 48px;
    margin: 3px 2px;
}

QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {
    background: #5c6a7d;
}

QScrollBar::handle:vertical:pressed,
QScrollBar::handle:horizontal:pressed {
    background: #6b7a90;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    background: #2a3038;
    border: none;
}

QScrollBar::sub-line:vertical {
    height: 14px;
    subcontrol-position: top;
}

QScrollBar::add-line:vertical {
    height: 14px;
    subcontrol-position: bottom;
}

QScrollBar::sub-line:horizontal {
    width: 14px;
    subcontrol-position: left;
}

QScrollBar::add-line:horizontal {
    width: 14px;
    subcontrol-position: right;
}

QScrollBar::add-line:vertical:hover,
QScrollBar::sub-line:vertical:hover,
QScrollBar::add-line:horizontal:hover,
QScrollBar::sub-line:horizontal:hover {
    background: #3a424f;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: #1a1e24;
}

QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical,
QScrollBar::left-arrow:horizontal,
QScrollBar::right-arrow:horizontal {
    width: 10px;
    height: 10px;
    background: transparent;
}

/* --- Live Mode --- */
QWidget#liveSessionRoot {
    background-color: #080a0c;
}

QFrame#liveSessionHeader {
    background-color: #0f1218;
    border-bottom: 1px solid #2a3038;
}

QLabel#liveSessionTitle {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
}

QLabel#liveSessionMeta {
    font-size: 14px;
    color: #9aa3b2;
    padding-left: 12px;
}

QLabel#liveOfflineHint {
    font-size: 16px;
    color: #9aa3b2;
    padding: 48px 32px;
}

QScrollArea#liveSessionScroll {
    background: transparent;
    border: none;
}

QWidget#liveCardsContainer {
    background: transparent;
}

QFrame#liveDriverCard {
    background-color: #12161c;
    border: 1px solid #2a3038;
    border-radius: 10px;
}

QFrame#liveDriverCard[risk="high"] {
    border-left: 5px solid #f5c26b;
    background-color: #1a1408;
}

QFrame#liveDriverCard[risk="moderate"] {
    border-left: 5px solid #c9a227;
}

QFrame#liveDriverCard[pref="like"] {
    background-color: #0f1a14;
    border-color: #2d5a3d;
}

QFrame#liveDriverCard[pref="dislike"] {
    background-color: #1a0f0f;
    border-color: #5a2d2d;
}

QLabel#liveDriverName {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
}

QLabel#liveVerdict {
    font-size: 15px;
    font-weight: 600;
    color: #f5c26b;
}

QLabel#liveStatTitle {
    font-size: 11px;
    font-weight: 600;
    color: #7a8494;
    text-transform: uppercase;
}

QLabel#liveStatValue {
    font-size: 20px;
    font-weight: 700;
    color: #e8eaed;
}

QLabel#liveScoreValue {
    font-size: 32px;
    font-weight: 800;
    color: #ffffff;
    min-width: 56px;
}

QLabel#liveTierLabel {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QPushButton#liveModeBtn[active="true"] {
    background-color: #3d3420;
    border-color: #c9a227;
    color: #f5c26b;
    font-weight: 700;
}

/* --- Safety Index panel --- */
QLabel#safetyScoreValue {
    font-size: 28px;
    font-weight: 800;
    color: #ffffff;
}

QLabel#safetyTierBadge {
    font-size: 13px;
    font-weight: 700;
}

QLabel#safetyProfile {
    font-size: 14px;
    font-weight: 600;
    color: #f5c26b;
    padding: 2px 0 4px 0;
}

QLabel#safetyComponentLabel {
    font-size: 12px;
    font-weight: 600;
    color: #9aa3b2;
    min-width: 72px;
}

QLabel#safetyComponentValue {
    font-size: 11px;
    color: #b8c0cc;
    min-width: 100px;
}

QProgressBar#safetyComponentBar {
    border: 1px solid #3d4654;
    border-radius: 3px;
    background: #1a1e24;
}

QProgressBar#safetyComponentBar::chunk {
    background-color: #4a8af4;
    border-radius: 2px;
}
"""

STATUS_CONNECTED = "connected"
STATUS_WAITING = "waiting"
STATUS_OFFLINE = "offline"


def tune_scroll_bar(bar: QScrollBar, *, single_step: int, page_step: int) -> None:
    """Larger wheel/track steps so scrolling feels predictable."""
    bar.setSingleStep(single_step)
    bar.setPageStep(page_step)


def configure_widget_scrollbars(
    widget: QWidget,
    *,
    single_step: int = 24,
    page_step: int = 120,
    horizontal_single: int | None = None,
    horizontal_page: int | None = None,
    always_show: bool = False,
) -> None:
    """Apply scroll tuning to any widget with vertical/horizontal scroll bars."""
    if not isinstance(widget, QAbstractScrollArea) and not hasattr(widget, "verticalScrollBar"):
        return

    if always_show:
        if hasattr(widget, "setVerticalScrollBarPolicy"):
            widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        if hasattr(widget, "setHorizontalScrollBarPolicy"):
            widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

    vbar = widget.verticalScrollBar() if hasattr(widget, "verticalScrollBar") else None
    if vbar is not None:
        tune_scroll_bar(vbar, single_step=single_step, page_step=page_step)

    hbar = widget.horizontalScrollBar() if hasattr(widget, "horizontalScrollBar") else None
    if hbar is not None:
        hs = horizontal_single if horizontal_single is not None else single_step * 2
        hp = horizontal_page if horizontal_page is not None else page_step * 2
        tune_scroll_bar(hbar, single_step=hs, page_step=hp)


def configure_scroll_area(area: QScrollArea, *, page_step: int = 120) -> None:
    configure_widget_scrollbars(area, single_step=24, page_step=page_step)
