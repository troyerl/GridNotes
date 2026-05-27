"""Application-wide visual theme (Qt stylesheets)."""

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

QScrollBar:vertical {
    background: #1a1e24;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3d4654;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #4d5868;
}
"""

STATUS_CONNECTED = "connected"
STATUS_WAITING = "waiting"
STATUS_OFFLINE = "offline"
