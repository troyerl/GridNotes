"""Application-wide visual theme (Qt stylesheets)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QAbstractScrollArea, QApplication, QScrollArea, QScrollBar, QWidget

from .appearance import THEME_DARK_ID, THEME_LIGHT_ID, get_theme_id
from .theme_tokens import THEME_DARK, THEME_LIGHT, theme_tokens

STYLESHEET_TEMPLATE = """

QMainWindow, QWidget {
    background-color: {{bg_window}};
    color: {{text_primary}};
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QLabel {
    background: transparent;
}

QLabel#appTitle {
    font-size: 20px;
    font-weight: 700;
    color: {{text_heading}};
}

QLabel#appSubtitle {
    font-size: 12px;
    color: {{text_secondary}};
}

QLabel#sectionHint {
    font-size: 12px;
    color: {{text_secondary}};
    padding: 2px 0 6px 0;
}

QLabel#emptyState {
    font-size: 13px;
    color: {{text_secondary}};
    padding: 4px 0;
}

QLabel#statusBadge {
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 14px;
}

QLabel#statusBadge[status="connected"] {
    background-color: {{success_bg}};
    color: {{success_text}};
}

QLabel#statusBadge[status="waiting"] {
    background-color: {{warning_bg}};
    color: {{warning_text}};
}

QLabel#statusBadge[status="offline"] {
    background-color: {{bg_header}};
    color: {{text_secondary}};
}

QGroupBox {
    font-size: 12px;
    font-weight: 600;
    color: {{text_group}};
    border: 1px solid {{border}};
    border-radius: 8px;
    margin-top: 10px;
    padding: 14px 12px 10px 12px;
    background-color: {{bg_elevated}};
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}

QFrame#panel {
    background-color: {{bg_elevated}};
    border: 1px solid {{border}};
    border-radius: 10px;
}

QLineEdit, QTextEdit {
    background-color: {{bg_window}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {{selection_bg}};
}

QLineEdit:focus, QTextEdit:focus {
    border: 2px solid {{focus_ring}};
}

QPushButton:focus {
    border: 2px solid {{focus_ring}};
    outline: none;
}

QPushButton#chipBtn:focus {
    border: 2px solid {{focus_ring}};
}

QCheckBox:focus {
    outline: none;
}

QCheckBox::indicator:focus {
    border: 2px solid {{focus_ring}};
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: {{bg_scroll_track}};
    color: {{text_disabled}};
}

QPushButton {
    background-color: {{bg_button}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
    min-height: 18px;
}

QPushButton:hover {
    background-color: {{bg_button_hover}};
    border-color: {{scrollbar_handle}};
}

/* "Chip" buttons used for tags/templates */
QPushButton#chipBtn {
    padding: 2px 8px;
    min-height: 26px;
    border-radius: 14px;
    background-color: {{bg_header}};
    border: 1px solid {{bg_button_pressed}};
    font-weight: 600;
}

QPushButton#chipBtn:hover {
    background-color: {{bg_header_hover}};
    border-color: {{scrollbar_handle_hover}};
}

QPushButton#chipBtn:pressed {
    background-color: {{live_card_border}};
}

QPushButton:pressed {
    background-color: {{live_card_border}};
}

QPushButton:disabled {
    color: {{text_disabled}};
    background-color: {{bg_elevated}};
}

QPushButton#primaryBtn {
    background-color: {{accent}};
    border-color: {{accent_border_light}};
    color: {{text_on_accent}};
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: {{accent_hover}};
}

QPushButton#primaryBtn:disabled,
QPushButton#primaryBtn:disabled:hover {
    background-color: {{bg_elevated}};
    border-color: {{border}};
    color: {{text_disabled}};
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: {{danger_text}};
    border-color: {{dislike_border}};
}

QPushButton#dangerBtn:hover {
    background-color: {{danger_btn_hover}};
}

QPushButton#prefLike[selected="true"] {
    background-color: {{like_border}};
    border-color: {{success_btn}};
    color: {{live_verdict_low}};
    font-weight: 600;
}

QPushButton#prefDislike[selected="true"] {
    background-color: {{danger_btn_border}};
    border-color: {{danger_border}};
    color: {{danger_text_light}};
    font-weight: 600;
}

QCheckBox {
    spacing: 8px;
    color: {{text_tab}};
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {{scrollbar_handle}};
    background-color: {{bg_window}};
}

QCheckBox::indicator:checked {
    background-color: {{accent}};
    border-color: {{accent_border_light}};
}

QCheckBox:disabled {
    color: {{text_disabled}};
}

QLabel#driverName {
    font-size: 18px;
    font-weight: 700;
    color: {{text_heading}};
}

QLabel#driverMeta {
    font-size: 12px;
    color: {{text_secondary}};
    padding: 0;
    margin: 0;
}

QLabel#statLabel {
    font-size: 12px;
    font-weight: 600;
    color: {{text_group}};
    padding: 8px 0 2px 0;
}

QLabel#statInlineLabel {
    font-size: 13px;
    font-weight: 600;
    color: {{text_group}};
    padding: 0;
}

QLabel#seriesValue {
    font-size: 13px;
    font-weight: 500;
    color: {{text_primary}};
    padding: 0 0 10px 0;
}

QLabel#statValue {
    font-size: 13px;
    font-weight: 500;
    color: {{text_primary}};
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

QTableWidget#driverTable {
    font-size: 14px;
    background-color: {{bg_window}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 6px;
    padding: 0;
    selection-background-color: {{selection_bg}};
    selection-color: {{text_on_accent}};
    outline: none;
}

QTableWidget#driverTable:focus {
    border: 2px solid {{focus_ring}};
}

QTableWidget::item {
    padding: 4px 6px;
    border: none;
    outline: none;
}

QTableWidget#driverTable::item {
    padding: 8px 10px;
    border: none;
    outline: none;
}

/* Row hover is applied in code across the full row */
QTableWidget::item:focus,
QTableWidget::item:selected:focus,
QTableView::item:focus,
QTableView::item:selected:focus {
    border: none;
    outline: none;
}

QTableWidget::item:selected {
    border: none;
}

QHeaderView::section {
    background-color: {{bg_header}};
    color: {{text_group}};
    padding: 8px 6px;
    border: none;
    border-bottom: 2px solid {{selection_bg}};
    font-weight: 600;
    font-size: 11px;
}

QTableWidget#driverTable QHeaderView::section {
    font-size: 12px;
    padding: 10px 8px;
    min-height: 32px;
}

QTableWidget#driverTable QHeaderView::section:hover {
    background-color: {{bg_header_hover}};
    color: {{text_on_accent}};
    border-bottom: 2px solid {{accent_border_hover}};
}

QTableWidget#driverTable QHeaderView::section:pressed {
    background-color: {{header_pressed_bg}};
    color: {{text_on_accent}};
    border-bottom: 2px solid {{accent_border}};
}

QSplitter::handle {
    background-color: {{border}};
    width: 2px;
}

/* Scrollbars — wider track and handle for easier grabbing */
QScrollBar:vertical {
    background: {{bg_scroll_track}};
    width: 16px;
    margin: 2px 0;
    border: none;
}

QScrollBar:horizontal {
    background: {{bg_scroll_track}};
    height: 16px;
    margin: 0 2px;
    border: none;
}

QScrollBar::handle:vertical {
    background: {{scrollbar_handle}};
    border-radius: 7px;
    min-height: 48px;
    margin: 2px 3px;
}

QScrollBar::handle:horizontal {
    background: {{scrollbar_handle}};
    border-radius: 7px;
    min-width: 48px;
    margin: 3px 2px;
}

QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {
    background: {{scrollbar_pressed}};
}

QScrollBar::handle:vertical:pressed,
QScrollBar::handle:horizontal:pressed {
    background: {{scrollbar_arrow}};
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    background: {{bg_header}};
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
    background: {{bg_button_hover}};
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: {{bg_window}};
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
    background-color: {{live_root_bg}};
}

QFrame#liveSessionHeader {
    background-color: {{live_header_bg}};
    border-bottom: 1px solid {{bg_header}};
}

QLabel#liveSessionTitle {
    font-size: 22px;
    font-weight: 800;
    color: {{text_heading}};
}

QLabel#liveSessionContext {
    font-size: 15px;
    font-weight: 600;
    color: {{text_heading}};
}

QLabel#liveSessionAtGlance {
    font-size: 14px;
    font-weight: 600;
    color: {{text_muted}};
}

QLabel#liveNewBadge {
    font-size: 11px;
    font-weight: 800;
    color: {{accent}};
    background-color: {{selection_bg}};
    border: 1px solid {{accent_border}};
    border-radius: 4px;
    padding: 2px 6px;
}

QLabel#liveSessionMeta {
    font-size: 14px;
    color: {{text_secondary}};
    padding-left: 12px;
}

QLabel#liveOfflineHint {
    font-size: 16px;
    color: {{text_secondary}};
    padding: 48px 32px;
}

QScrollArea#liveSessionScroll {
    background: transparent;
    border: none;
}

QFrame#accordionSection {
    background-color: {{live_card_bg}};
    border: 1px solid {{border}};
    border-radius: 6px;
}

QPushButton#accordionHeader {
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    font-weight: 600;
    color: {{scrollbar_arrow_hover}};
}

QPushButton#accordionHeader:hover {
    background-color: {{bg_header}};
}

QPushButton#accordionHeader:checked {
    background-color: {{bg_header}};
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
}

QFrame#accordionBody {
    background-color: {{bg_window}};
    border-top: 1px solid {{border}};
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
}

QLabel#sectionHint a {
    color: {{link}};
}

QPushButton#hintLinkBtn {
    color: {{link}};
    border: none;
    padding: 2px 8px;
    font-weight: 600;
    background: transparent;
}

QPushButton#hintLinkBtn:hover {
    text-decoration: underline;
    background-color: {{bg_header}};
}

QTextBrowser#scoutingGuideBrowser {
    background-color: {{bg_window}};
    border: 1px solid {{border}};
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 12px;
    color: {{text_secondary}};
}

QTextBrowser#scoutingGuideBrowser h2 {
    color: {{scrollbar_arrow_hover}};
    font-size: 14px;
    margin-top: 14px;
    margin-bottom: 6px;
}

QWidget#liveCardsContainer {
    background: transparent;
}

QFrame#liveDriverCard {
    background-color: {{live_scroll_bg}};
    border: 1px solid {{bg_header}};
    border-radius: 10px;
}

QFrame#liveDriverCard[risk="high"] {
    border-left: 5px solid {{warning_text}};
    background-color: {{risk_card_bg}};
}

QFrame#liveDriverCard[risk="moderate"] {
    border-left: 5px solid {{warning_accent}};
}

QFrame#liveDriverCard[pref="like"] {
    background-color: {{live_like_bg}};
    border-color: {{like_border}};
}

QFrame#liveDriverCard[pref="dislike"] {
    background-color: {{dislike_bg}};
    border-color: {{danger_btn_border}};
}

QLabel#liveDriverName {
    font-size: 26px;
    font-weight: 800;
    color: {{text_heading}};
}

QLabel#liveVerdict {
    font-size: 15px;
    font-weight: 600;
    color: {{warning_text}};
}

QLabel#liveStatTitle {
    font-size: 11px;
    font-weight: 600;
    color: {{text_muted}};
    text-transform: uppercase;
}

QLabel#liveStatValue {
    font-size: 20px;
    font-weight: 700;
    color: {{text_primary}};
}

QLabel#liveScoreValue {
    font-size: 32px;
    font-weight: 800;
    color: {{text_heading}};
    min-width: 56px;
}

QLabel#liveTierLabel {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QPushButton#liveModeBtn[active="true"] {
    background-color: {{warning_bg}};
    border-color: {{warning_accent}};
    color: {{warning_text}};
    font-weight: 700;
}

QPushButton#streamerModeBtn[active="true"] {
    background-color: {{selection_bg}};
    border-color: {{accent_border}};
    color: {{text_heading}};
    font-weight: 700;
}

QPushButton#liveGridWalkBtn[active="true"] {
    background-color: {{accent}};
    border-color: {{accent_border_light}};
    color: {{text_on_accent}};
    font-weight: 700;
}

/* --- Grid Walk --- */
QWidget#gridWalkRoot {
    background-color: {{live_root_bg}};
}

QLabel#gridWalkSummary {
    font-size: 16px;
    font-weight: 700;
    color: {{text_heading}};
}

QLabel#gridWalkAtGlance {
    font-size: 14px;
    font-weight: 600;
    color: {{text_muted}};
}

QLabel#gridWalkNewBadge {
    font-size: 10px;
    font-weight: 800;
    color: {{accent}};
    background-color: {{selection_bg}};
    border: 1px solid {{accent_border}};
    border-radius: 4px;
    padding: 1px 5px;
}

QLabel#gridWalkScore {
    font-size: 15px;
    font-weight: 800;
    color: {{text_heading}};
}

QScrollArea#gridWalkScroll {
    background: transparent;
    border: none;
}

QFrame#gridWalkPairRow {
    background: transparent;
    border: none;
}

QFrame#gridWalkLane {
    background-color: {{live_card_border}};
    border: none;
    margin: 4px 0;
}

QFrame#gridWalkRow {
    background-color: {{live_card_bg}};
    border: 1px solid {{live_card_border}};
    border-radius: 8px;
}

QFrame#gridWalkRow[role="you"] {
    background-color: {{selection_bg}};
    border: 2px solid {{accent_border}};
}

QFrame#gridWalkRow[role="you"] QLabel#gridWalkName,
QFrame#gridWalkRow[role="you"] QLabel#gridWalkPos {
    color: {{text_on_accent}};
    font-weight: 800;
}

QFrame#gridWalkRow[role="ahead"],
QFrame#gridWalkRow[role="beside"] {
    border: 2px solid {{warning_accent}};
    background-color: {{warning_bg}};
}

QFrame#gridWalkRow[pref="dislike"] {
    background-color: {{dislike_bg}};
    border-color: {{danger_border}};
}

QFrame#gridWalkRow[risky="true"] {
    border-left: 5px solid {{warning_text}};
}

QFrame#gridWalkRow:focus {
    border: 2px solid {{focus_ring}};
    outline: none;
}

QLabel#gridWalkPos {
    font-size: 15px;
    font-weight: 800;
    color: {{text_muted}};
}

QLabel#gridWalkName {
    font-size: 17px;
    font-weight: 700;
    color: {{text_heading}};
}

QLabel#gridWalkMark {
    font-size: 13px;
    font-weight: 700;
    color: {{warning_text}};
    min-width: 88px;
}

/* --- Safety Index panel --- */
QLabel#safetyScoreValue {
    font-size: 28px;
    font-weight: 800;
    color: {{text_heading}};
}

QLabel#safetyTierBadge {
    font-size: 13px;
    font-weight: 700;
}

QLabel#safetyProfile {
    font-size: 14px;
    font-weight: 600;
    color: {{warning_text}};
    padding: 2px 0 4px 0;
}

QLabel#safetyComponentLabel {
    font-size: 12px;
    font-weight: 600;
    color: {{text_secondary}};
    min-width: 72px;
}

QLabel#safetyComponentValue {
    font-size: 11px;
    color: {{text_group}};
    min-width: 100px;
}

QProgressBar#safetyComponentBar {
    border: 1px solid {{border_strong}};
    border-radius: 3px;
    background: {{bg_window}};
}

QProgressBar#safetyComponentBar::chunk {
    background-color: {{accent_border}};
    border-radius: 2px;
}

QTabWidget#mainTabs::pane {
    border: 1px solid {{border}};
    border-radius: 0 8px 8px 8px;
    background-color: {{bg_window}};
    top: -1px;
}

QTabWidget#mainTabs > QTabBar {
    background: transparent;
    border: none;
}

QTabWidget#mainTabs > QTabBar::tab {
    background-color: {{bg_elevated}};
    color: {{text_muted}};
    border: 1px solid {{border}};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 12px 28px;
    margin-right: 6px;
    font-weight: 600;
    font-size: 14px;
    min-width: 108px;
}

QTabWidget#mainTabs > QTabBar::tab:selected {
    background-color: {{accent}};
    color: {{text_on_accent}};
    border-color: {{accent}};
    font-weight: 700;
    font-size: 14px;
}

QTabWidget#mainTabs > QTabBar::tab:selected:hover {
    background-color: {{accent_hover}};
    border-color: {{accent_hover}};
}

QTabWidget#mainTabs > QTabBar::tab:hover:!selected {
    background-color: {{bg_button_hover}};
    color: {{text_primary}};
    border-color: {{border_strong}};
}

QTabWidget#mainTabs > QTabBar::tab:focus {
    border: 2px solid {{focus_ring}};
    outline: none;
}

QWidget#settingsContent QLineEdit {
    background-color: {{bg_window}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 18px;
    selection-background-color: {{selection_bg}};
}

QWidget#settingsContent QLineEdit:focus {
    border-color: {{accent_border}};
}

QComboBox#settingsCombo {
    background-color: {{bg_window}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 8px;
    min-height: 32px;
    padding: 6px 12px;
}

QComboBox#settingsCombo:hover {
    border-color: {{scrollbar_handle}};
}

QComboBox#settingsCombo:focus,
QComboBox#settingsCombo:on {
    border-color: {{accent_border}};
}

QComboBox#settingsCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    border: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    width: 28px;
}

QComboBox#settingsCombo::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox#settingsCombo QAbstractItemView {
    background-color: {{bg_elevated}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {{selection_bg}};
    selection-color: {{text_on_accent}};
    outline: none;
}

QFrame#settingsHeader {
    background-color: {{bg_elevated}};
    border-bottom: 1px solid {{border}};
}

QFrame#settingsBody {
    background-color: {{bg_window}};
}

QScrollArea#settingsContentScroll {
    background: transparent;
    border: none;
}

QWidget#settingsContent {
    background: transparent;
}

QWidget#settingsContent QCheckBox {
    background: transparent;
}

QWidget#settingsContent QCheckBox::indicator {
    background-color: transparent;
}

QWidget#settingsContent QCheckBox::indicator:checked {
    background-color: {{accent}};
}

QDialog#updateProgressDialog {
    background-color: {{bg_window}};
}

QLabel#updateProgressTitle {
    font-size: 15px;
    font-weight: 600;
    color: {{text_heading}};
}

QProgressBar#updateProgressBar {
    border: 1px solid {{border}};
    border-radius: 6px;
    background-color: {{bg_elevated}};
    text-align: center;
    color: {{text_secondary}};
    min-height: 22px;
}

QProgressBar#updateProgressBar::chunk {
    background-color: {{accent}};
    border-radius: 5px;
}

QLabel#updateProgressStatus {
    color: {{text_tab}};
    font-size: 13px;
}

QDialog#importProgressDialog {
    background-color: {{bg_window}};
}

QLabel#importProgressTitle {
    font-size: 15px;
    font-weight: 600;
    color: {{text_heading}};
}

QProgressBar#importProgressBar {
    border: 1px solid {{border}};
    border-radius: 6px;
    background-color: {{bg_elevated}};
    min-height: 22px;
}

QProgressBar#importProgressBar::chunk {
    background-color: {{accent}};
    border-radius: 5px;
}

QLabel#importProgressStatus {
    color: {{text_tab}};
    font-size: 13px;
}

QDialog#streamerModeProgressDialog {
    background-color: {{bg_window}};
}

QLabel#streamerModeProgressTitle {
    font-size: 15px;
    font-weight: 600;
    color: {{text_heading}};
}

QProgressBar#streamerModeProgressBar {
    border: 1px solid {{border}};
    border-radius: 6px;
    background-color: {{bg_elevated}};
    min-height: 22px;
}

QProgressBar#streamerModeProgressBar::chunk {
    background-color: {{accent}};
    border-radius: 5px;
}

QLabel#streamerModeProgressStatus {
    color: {{text_tab}};
    font-size: 13px;
}

QFrame#settingsNavSidebar {
    background-color: {{bg_elevated}};
    border: none;
    border-right: 1px solid {{border}};
}

QLabel#settingsNavTitle {
    font-size: 11px;
    font-weight: 700;
    color: {{text_muted}};
    text-transform: uppercase;
    padding: 12px 14px 4px 14px;
}

QScrollArea#settingsNavScroll {
    background: transparent;
    border: none;
}

QWidget#settingsNavList {
    background: transparent;
}

QPushButton#settingsNavItem {
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    color: {{text_group}};
    font-weight: 600;
}

QPushButton#settingsNavItem:hover:!checked {
    background-color: {{live_card_border}};
    color: {{text_primary}};
}

QPushButton#settingsNavItem:checked {
    background-color: {{bg_header}};
    color: {{text_heading}};
    border-left: 3px solid {{accent_border}};
    padding-left: 9px;
}

QPushButton#settingsNavItem:focus {
    border: 2px solid {{focus_ring}};
    outline: none;
}

QStackedWidget#settingsSectionStack {
    background: transparent;
}

QLabel#settingsStatusPill {
    font-size: 12px;
    color: {{text_group}};
    padding: 6px 10px;
    border-radius: 6px;
    background: transparent;
    border: 1px solid {{border}};
}

QLabel#settingsStatusPill[status="ok"] {
    color: {{success_text}};
    border-color: {{success_border}};
}

QLabel#settingsStatusPill[status="error"] {
    color: {{danger_text}};
    border-color: {{error_border}};
}

QLabel#settingsOAuthNotice {
    font-size: 13px;
    color: {{oauth_notice_text}};
    padding: 10px 12px;
    border-radius: 8px;
    background-color: {{oauth_notice_bg}};
    border: 1px solid {{oauth_notice_border}};
}
"""


THEMES = {
    THEME_DARK_ID: THEME_DARK,
    THEME_LIGHT_ID: THEME_LIGHT,
}


def build_stylesheet(theme_id: str | None = None) -> str:
    """Return the application stylesheet for *theme_id* (defaults to saved preference)."""
    if theme_id is None:
        theme_id = get_theme_id()
    tokens = THEMES.get(theme_id, THEME_DARK)
    css = STYLESHEET_TEMPLATE
    for key, value in tokens.items():
        css = css.replace("{{" + key + "}}", value)
    return css


APP_STYLESHEET = build_stylesheet(THEME_DARK_ID)


def apply_app_theme(app: QApplication, theme_id: str | None = None) -> str:
    """Apply stylesheet globally; returns the theme id applied."""
    if theme_id is None:
        theme_id = get_theme_id()
    app.setStyleSheet(build_stylesheet(theme_id))
    return theme_id


def refresh_widget_tree(root: QWidget) -> None:
    """Re-polish widgets after a global stylesheet change."""
    style = root.style()
    if style is None:
        return
    style.unpolish(root)
    style.polish(root)
    for child in root.findChildren(QWidget):
        style.unpolish(child)
        style.polish(child)


TABLE_ROW_COLORS = {
    THEME_DARK_ID: {
        "liked": (42, 72, 52),
        "liked_hover": (54, 96, 66),
        "liked_selected": (50, 88, 98),
        "disliked": (72, 42, 42),
        "disliked_hover": (96, 52, 52),
        "disliked_selected": (92, 52, 82),
        "hover": (45, 52, 64),
        "risky": (72, 62, 32),
        "risky_hover": (92, 80, 44),
        "risky_selected": (78, 72, 58),
        "alternate": (30, 35, 43),
        "base": (26, 30, 36),
        "highlight_fg": (232, 234, 237),
        "selected_bg": (45, 74, 122),
        "selected_fg": (255, 255, 255),
    },
    THEME_LIGHT_ID: {
        "liked": (209, 250, 229),
        "liked_hover": (186, 245, 214),
        "liked_selected": (172, 228, 248),
        "disliked": (254, 226, 226),
        "disliked_hover": (252, 202, 202),
        "disliked_selected": (248, 198, 228),
        "hover": (229, 231, 235),
        "risky": (254, 243, 199),
        "risky_hover": (253, 232, 168),
        "risky_selected": (228, 236, 252),
        "alternate": (249, 250, 251),
        "base": (243, 244, 246),
        "highlight_fg": (17, 24, 39),
        "selected_bg": (59, 130, 246),
        "selected_fg": (255, 255, 255),
    },
}


def table_row_color(theme_id: str, key: str) -> QColor:
    rgb = TABLE_ROW_COLORS.get(theme_id, TABLE_ROW_COLORS[THEME_DARK_ID])[key]
    return QColor(*rgb)


def safety_progress_bar_style(theme_id: str, chunk_color: str) -> str:
    """Inline QProgressBar style for the safety overall bar."""
    t = theme_tokens(theme_id)
    return (
        f"QProgressBar#safetyOverallBar {{ border: 1px solid {t['border_strong']}; "
        f"border-radius: 4px; background: {t['bg_window']}; text-align: center; "
        f"color: {t['text_primary']}; }} "
        f"QProgressBar#safetyOverallBar::chunk {{ background-color: {chunk_color}; "
        f"border-radius: 4px; }}"
    )


def status_message_color(theme_id: str, *, ok: bool) -> str:
    t = theme_tokens(theme_id)
    return t["success_text"] if ok else t["danger_text"]


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
