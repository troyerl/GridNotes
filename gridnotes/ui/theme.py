"""Application-wide visual theme (Qt stylesheets)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QLineEdit,
    QScrollArea,
    QScrollBar,
    QWidget,
)

from .appearance import THEME_DARK_ID, THEME_LIGHT_ID, get_theme_id, set_active_theme_id
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

QToolTip {
    background-color: {{bg_elevated}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 6px;
    padding: 6px 10px;
}

QFrame#topHeaderBar {
    background-color: {{bg_elevated}};
    border: 1px solid {{border}};
    border-radius: 12px;
    padding: 4px 8px;
}

QFrame#driversToolbar {
    background-color: transparent;
    border: none;
}

QFrame#searchInputWrapper {
    background-color: {{bg_window}};
    border: 1px solid {{border_strong}};
    border-radius: 10px;
    padding: 0 4px;
}

QFrame#searchInputWrapper:focus-within {
    border: 2px solid {{focus_ring}};
}

QLineEdit#driverSearchInput {
    background: transparent;
    border: none;
    padding: 8px 6px;
    font-size: 13px;
}

QLineEdit#driverSearchInput:focus {
    border: none;
}

QLabel#searchInputIcon {
    color: {{icon_muted}};
    font-size: 14px;
    padding: 0 4px 0 8px;
    background: transparent;
}

QFrame#filtersBar {
    background-color: {{bg_elevated}};
    border: 1px solid {{border}};
    border-radius: 10px;
    padding: 2px 8px;
}

QComboBox#racingTypeFilter {
    min-width: 120px;
    padding: 4px 8px;
    border: 1px solid {{border}};
    border-radius: 6px;
    background-color: {{bg_window}};
    color: {{text_primary}};
}

QComboBox#racingTypeFilter:hover {
    border-color: {{border_strong}};
}

QComboBox#racingTypeFilter:focus,
QComboBox#racingTypeFilter:on {
    border: 2px solid {{accent_border}};
}

QComboBox#racingTypeFilter::drop-down {
    border: none;
    width: 22px;
}

QComboBox#racingTypeFilter QAbstractItemView {
    background-color: {{bg_elevated}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    selection-background-color: {{selection_bg}};
}

QPushButton#headerBtn {
    background-color: {{bg_button}};
    border: 1px solid {{border_strong}};
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 600;
    min-height: 20px;
    color: {{text_primary}};
}

QPushButton#headerBtn:hover {
    background-color: {{bg_button_hover}};
    border-color: {{scrollbar_handle}};
}

QPushButton#headerBtn:pressed {
    background-color: {{bg_button_pressed}};
}

QFrame#scoutingSidebar {
    background-color: {{bg_elevated}};
    border: 1px solid {{border}};
    border-radius: 12px;
}

QFrame#emptyStateCard {
    background-color: {{bg_window}};
    border: 1px dashed {{border_strong}};
    border-radius: 12px;
    padding: 24px;
}

QLabel#emptyStateIcon {
    font-size: 32px;
    color: {{icon_muted}};
    background: transparent;
}

QLabel#prefBadge {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
    padding: 4px 10px;
    border-radius: 6px;
}

QLabel#prefBadge[status="liked"] {
    background-color: {{pref_like_bg}};
    color: {{pref_like_fg}};
    border: 1px solid {{pref_like_border}};
}

QLabel#prefBadge[status="disliked"] {
    background-color: {{pref_dislike_bg}};
    color: {{pref_dislike_fg}};
    border: 1px solid {{pref_dislike_border}};
}

QLabel#prefBadge[status="risk"] {
    background-color: {{warning_bg}};
    color: {{warning_text}};
}

QPushButton#prefRatingBtn {
    border-radius: 10px;
    padding: 12px 16px;
    font-weight: 700;
    font-size: 13px;
    min-height: 24px;
}

QPushButton#prefLikeBtn {
    background-color: {{pref_like_bg}};
    border: 1px solid {{pref_like_border}};
    color: {{pref_like_fg}};
}

QPushButton#prefLikeBtn:hover {
    background-color: {{success_btn}};
    border-color: {{success_btn}};
    color: {{text_on_accent}};
}

QPushButton#prefLikeBtn[selected="true"] {
    background-color: {{success_btn}};
    border-color: {{success_border}};
    color: {{text_on_accent}};
}

QPushButton#prefDislikeBtn {
    background-color: {{pref_dislike_bg}};
    border: 1px solid {{pref_dislike_border}};
    color: {{pref_dislike_fg}};
}

QPushButton#prefDislikeBtn:hover {
    background-color: {{danger_btn_border}};
    border-color: {{danger_border}};
    color: {{text_on_accent}};
}

QPushButton#prefDislikeBtn[selected="true"] {
    background-color: {{danger_btn_border}};
    border-color: {{danger_text}};
    color: {{text_on_accent}};
}

QPushButton#prefClearBtn {
    background-color: {{warning_bg}};
    border: 1px solid {{warning_accent}};
    color: {{warning_text}};
}

QPushButton#prefClearBtn:hover {
    background-color: {{warning_accent}};
    color: {{text_on_accent}};
}

QPushButton#gradientBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {{gradient_start}}, stop:1 {{gradient_end}});
    border: none;
    border-radius: 10px;
    color: {{text_on_accent}};
    font-weight: 700;
    font-size: 14px;
    padding: 12px 20px;
    min-height: 22px;
}

QPushButton#gradientBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {{accent_hover}}, stop:1 {{gradient_end}});
}

QPushButton#gradientBtn:disabled {
    background: {{bg_button}};
    color: {{text_disabled}};
}

QLabel#userProfileLabel {
    font-size: 13px;
    font-weight: 600;
    color: {{text_primary}};
    background: transparent;
}

QLabel#userProfileIcon {
    font-size: 22px;
    color: {{icon_muted}};
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

QLabel#broadcastReceiverBanner {
    font-size: 12px;
    font-weight: 600;
    padding: 8px 12px;
    border-radius: 8px;
}

QLabel#broadcastReceiverBanner[status="connected"] {
    background-color: {{success_bg}};
    color: {{success_text}};
}

QLabel#broadcastReceiverBanner[status="connecting"] {
    background-color: {{warning_bg}};
    color: {{warning_text}};
}

QGroupBox {
    font-size: 12px;
    font-weight: 600;
    color: {{text_group}};
    border: 1px solid {{border}};
    border-radius: 10px;
    margin-top: 10px;
    padding: 14px 12px 10px 12px;
    background-color: {{bg_window}};
}

QFrame#scoutingSidebar QGroupBox {
    border: none;
    background-color: transparent;
    margin-top: 4px;
    padding: 8px 0 0 0;
}

QFrame#scoutingSidebar QGroupBox::title {
    color: {{text_heading}};
    font-size: 13px;
    font-weight: 700;
    subcontrol-origin: margin;
    left: 0;
    padding: 0 0 6px 0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}

QFrame#panel {
    background-color: transparent;
    border: none;
    border-radius: 0;
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
    border: 1px solid {{border_strong}};
    color: {{text_primary}};
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

QPushButton#prefLike[selected="true"],
QPushButton#prefLikeBtn[selected="true"] {
    background-color: {{success_btn}};
    border-color: {{success_border}};
    color: {{text_on_accent}};
    font-weight: 700;
}

QPushButton#prefDislike[selected="true"],
QPushButton#prefDislikeBtn[selected="true"] {
    background-color: {{danger_btn_border}};
    border-color: {{danger_text}};
    color: {{text_on_accent}};
    font-weight: 700;
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

QTableWidget#importHistoryTable,
QTableWidget#leagueMembersTable,
QTableWidget#leagueCandidatesTable {
    font-size: 13px;
    background-color: {{bg_window}};
    color: {{text_primary}};
    border: 1px solid {{border_strong}};
    border-radius: 6px;
    padding: 0;
    gridline-color: {{border}};
}

QTableWidget#importHistoryTable::item,
QTableWidget#leagueMembersTable::item,
QTableWidget#leagueCandidatesTable::item {
    padding: 4px 8px;
}

QTableWidget#importHistoryTable QHeaderView::section,
QTableWidget#leagueMembersTable QHeaderView::section,
QTableWidget#leagueCandidatesTable QHeaderView::section {
    background-color: {{bg_header}};
    color: {{text_group}};
    font-weight: 600;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {{border_strong}};
}

QTableWidget#driverTable {
    font-size: 13px;
    background-color: {{bg_window}};
    color: {{text_primary}};
    border: 1px solid {{border}};
    border-radius: 10px;
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
    font-weight: 600;
    font-style: italic;
    color: {{text_muted}};
    padding: 0;
}

QLabel#liveLeagueBadge {
    font-size: 11px;
    font-weight: 800;
    color: {{text_primary}};
    background-color: {{bg_header}};
    border: 1px solid {{border_strong}};
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

QFrame#liveDriverCard[expanded="true"] {
    border-color: {{accent}};
}

QFrame#liveDriverExpandPanel {
    background-color: {{live_scroll_bg}};
    border-top: 1px solid {{bg_header}};
}

QLabel#liveExpandChevron {
    font-family: "Font Awesome 6 Free";
    font-weight: 900;
    font-size: 16px;
    color: {{text_muted}};
    min-width: 20px;
}

QPushButton[iconOnly="true"] {
    padding: 4px 8px;
    min-width: 28px;
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
    font-weight: 600;
    font-style: italic;
    color: {{text_muted}};
    padding: 0;
}

QLabel#gridWalkLeagueBadge {
    font-size: 10px;
    font-weight: 800;
    color: {{text_primary}};
    background-color: {{bg_header}};
    border: 1px solid {{border_strong}};
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
    border: none;
    border-radius: 0;
    background-color: transparent;
    top: 0;
}

QTabWidget#mainTabs > QTabBar {
    background: transparent;
    border: none;
    border-bottom: 1px solid {{border}};
}

QTabWidget#mainTabs > QTabBar::tab {
    background-color: transparent;
    color: {{text_secondary}};
    border: none;
    border-bottom: 3px solid transparent;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 20px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 13px;
    min-width: 96px;
}

QTabWidget#mainTabs > QTabBar::tab:selected {
    background-color: {{bg_header}};
    color: {{text_heading}};
    border-bottom: 3px solid {{accent}};
    font-weight: 700;
}

QTabWidget#mainTabs > QTabBar::tab:selected:hover {
    background-color: {{bg_header_hover}};
    color: {{text_heading}};
}

QTabWidget#mainTabs > QTabBar::tab:hover:!selected {
    background-color: {{bg_elevated}};
    color: {{text_primary}};
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

QWidget#noteTagList,
QWidget#noteTagRow {
    background: transparent;
    background-color: transparent;
}

QWidget#settingsContent QLineEdit#noteTagInput {
    background: transparent;
    background-color: transparent;
    border: 1px solid {{border_strong}};
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 18px;
}

QWidget#settingsContent QLineEdit#noteTagInput:focus {
    border: 2px solid {{accent_border}};
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

QDialog {
    background: transparent;
}

QFrame#appModalPanel {
    background-color: {{bg_elevated}};
    border: 1px solid {{border_strong}};
    border-radius: 14px;
}

QMessageBox {
    background-color: {{bg_window}};
    border: 1px solid {{border_strong}};
    border-radius: 14px;
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

QPushButton#dialogChromeBtn {
    border: 1px solid {{border}};
    border-radius: 4px;
    background-color: {{bg_elevated}};
    color: {{text_secondary}};
    font-size: 14px;
    font-weight: 600;
    padding: 0;
}

QPushButton#dialogChromeBtn:hover {
    background-color: {{bg_button_hover}};
    color: {{text_heading}};
}

QPushButton#dialogChromeBtn:pressed {
    background-color: {{bg_button_pressed}};
}

QPushButton#dialogChromeBtn:disabled {
    color: {{text_muted}};
    background-color: {{bg_elevated}};
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

QLabel#streamerModeProgressTitle {
    font-size: 15px;
    font-weight: 600;
    color: {{text_heading}};
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
    color: {{text_primary}};
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


def note_tag_input_stylesheet(theme_id: str | None = None) -> str:
    """Per-widget stylesheet for quick note tag fields (macOS ignores app-level transparency)."""
    t = theme_tokens(theme_id or get_theme_id())
    return (
        "QLineEdit {"
        f" background: transparent;"
        f" background-color: transparent;"
        f" border: 1px solid {t['border_strong']};"
        f" border-radius: 8px;"
        f" padding: 8px 12px;"
        f" color: {t['text_primary']};"
        f" selection-background-color: {t['selection_bg']};"
        " }"
        " QLineEdit:focus {"
        f" border: 2px solid {t['accent_border']};"
        " }"
    )


def configure_modal_dialog(dialog) -> None:
    """Wrap dialog content in a rounded inner panel on a transparent outer window."""
    from PyQt6.QtWidgets import QDialog, QFrame, QVBoxLayout, QWidget

    if not isinstance(dialog, QDialog):
        return
    if getattr(dialog, "_modal_panel_wrapped", False):
        return
    dialog._modal_panel_wrapped = True

    if not dialog.objectName():
        dialog.setObjectName("appModalDialog")

    old_layout = dialog.layout()
    if old_layout is None:
        return

    margins = old_layout.contentsMargins()
    spacing = old_layout.spacing()

    items = []
    while old_layout.count():
        item = old_layout.takeAt(0)
        if item is not None:
            items.append(item)

    stealer = QWidget()
    stealer.setLayout(old_layout)
    stealer.deleteLater()

    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    dialog.setAutoFillBackground(False)
    dialog.setStyleSheet(f"QDialog#{dialog.objectName()} {{ background: transparent; }}")

    panel = QFrame(dialog)
    panel.setObjectName("appModalPanel")
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    panel_layout = QVBoxLayout(panel)
    panel_layout.setContentsMargins(margins)
    panel_layout.setSpacing(spacing)
    for item in items:
        widget = item.widget()
        nested = item.layout()
        if widget is not None:
            panel_layout.addWidget(widget)
        elif nested is not None:
            panel_layout.addLayout(nested)
        else:
            panel_layout.addItem(item)

    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addWidget(panel)

    style = dialog.style()
    if style is not None:
        style.unpolish(panel)
        style.polish(panel)
    dialog.update()


def configure_note_tag_input(line_edit: QLineEdit, theme_id: str | None = None) -> None:
    """Style a quick note tag line edit with a transparent, underline-only field."""
    line_edit.setObjectName("noteTagInput")
    line_edit.setAutoFillBackground(False)
    line_edit.setFrame(False)
    line_edit.setStyleSheet(note_tag_input_stylesheet(theme_id))


def apply_app_theme(app: QApplication, theme_id: str | None = None) -> str:
    """Apply stylesheet globally; returns the theme id applied."""
    if theme_id is None:
        theme_id = get_theme_id()
    theme_id = set_active_theme_id(theme_id)
    app.setStyleSheet(build_stylesheet(theme_id))
    try:
        from .icons import clear_icon_cache

        clear_icon_cache()
    except ImportError:
        pass
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
        "liked": (28, 48, 36),
        "liked_hover": (36, 62, 46),
        "liked_selected": (40, 68, 78),
        "disliked": (52, 28, 28),
        "disliked_hover": (68, 36, 36),
        "disliked_selected": (64, 36, 58),
        "hover": (32, 32, 38),
        "risky": (52, 44, 24),
        "risky_hover": (64, 56, 30),
        "risky_selected": (56, 50, 40),
        "alternate": (22, 22, 26),
        "base": (18, 18, 20),
        "highlight_fg": (232, 234, 237),
        "selected_bg": (55, 78, 140),
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
