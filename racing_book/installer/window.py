"""PyQt6 install wizard window."""

from __future__ import annotations

import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..appearance import THEME_DARK_ID
from ..app_icon import load_app_icon
from ..theme import apply_app_theme, configure_widget_scrollbars

from .logic import check_python, find_project_root, venv_python
from .worker import InstallWorker


class InstallWizardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._root = find_project_root()
        self._worker: InstallWorker | None = None
        self._install_succeeded = False

        self.setWindowTitle("Install GridNotes")
        self.setMinimumSize(640, 520)
        self.resize(720, 560)

        icon = load_app_icon()
        if icon is not None:
            self.setWindowIcon(icon)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Install GridNotes")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        intro = QLabel(
            "This wizard sets up GridNotes on your computer from the downloaded source code. "
            "It creates a private Python environment in this folder, installs dependencies, "
            "and adds a shortcut you can use to launch the app."
        )
        intro.setObjectName("sectionHint")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.folder_label = QLabel(f"Install location:\n{self._root}")
        self.folder_label.setObjectName("statValue")
        self.folder_label.setWordWrap(True)
        self.folder_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.folder_label)

        ok, python_message = check_python()
        self.python_label = QLabel(python_message)
        self.python_label.setObjectName("sectionHint" if ok else "emptyState")
        self.python_label.setWordWrap(True)
        layout.addWidget(self.python_label)

        self.build_checkbox = QCheckBox(
            "Also build a standalone Windows app (GridNotes.exe in dist/)"
        )
        self.build_checkbox.setVisible(sys.platform == "win32")
        self.build_checkbox.setToolTip(
            "Requires PyInstaller and takes several minutes. "
            "Skip this if you only want to run from source."
        )
        layout.addWidget(self.build_checkbox)

        self.step_label = QLabel("Ready to install.")
        self.step_label.setObjectName("statInlineLabel")
        layout.addWidget(self.step_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Installation log will appear here…")
        log_font = QFont("Menlo" if sys.platform == "darwin" else "Consolas")
        log_font.setPointSize(11)
        self.log_view.setFont(log_font)
        configure_widget_scrollbars(self.log_view, page_step=80)
        layout.addWidget(self.log_view, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.close)
        button_row.addWidget(self.btn_cancel)

        self.btn_install = QPushButton("Install")
        self.btn_install.setObjectName("primaryBtn")
        self.btn_install.clicked.connect(self._start_install)
        self.btn_install.setEnabled(ok)
        button_row.addWidget(self.btn_install)

        self.btn_launch = QPushButton("Launch GridNotes")
        self.btn_launch.setObjectName("primaryBtn")
        self.btn_launch.setVisible(False)
        self.btn_launch.clicked.connect(self._launch_app)
        button_row.addWidget(self.btn_launch)

        layout.addLayout(button_row)

        if not ok:
            self.step_label.setText(
                "Fix the Python version issue above, then restart this installer."
            )

    def append_log(self, line: str) -> None:
        self.log_view.append(line)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def _set_busy(self, busy: bool) -> None:
        self.btn_install.setEnabled(not busy)
        self.build_checkbox.setEnabled(not busy)
        self.btn_cancel.setText("Cancel" if busy else "Close")
        if busy:
            self.btn_launch.setVisible(False)

    def _start_install(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self.log_view.clear()
        self.progress.setValue(0)
        self._install_succeeded = False
        self._set_busy(True)
        self.step_label.setText("Installing…")

        self._worker = InstallWorker(
            root=self._root,
            build_standalone=self.build_checkbox.isChecked(),
            parent=self,
        )
        self._worker.step_changed.connect(self.step_label.setText)
        self._worker.progress_changed.connect(self.progress.setValue)
        self._worker.log_line.connect(self.append_log)
        self._worker.finished.connect(self._on_install_finished)
        self._worker.start()

    def _on_install_finished(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        self._install_succeeded = ok
        self.append_log("")
        self.append_log(message)

        if ok:
            self.step_label.setText("Installation complete")
            self.btn_install.setVisible(False)
            self.btn_launch.setVisible(True)
            QMessageBox.information(self, "Installation Complete", message)
        else:
            self.step_label.setText("Installation did not finish")
            QMessageBox.warning(self, "Installation Failed", message)

    def _launch_app(self) -> None:
        py = venv_python(self._root / ".venv")
        main_py = self._root / "main.py"
        if not py.is_file() or not main_py.is_file():
            QMessageBox.warning(
                self,
                "Cannot Launch",
                "Run Install first, or use Run GridNotes.bat / Run GridNotes.command.",
            )
            return
        subprocess.Popen(
            [str(py), str(main_py)],
            cwd=str(self._root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.close()

    def closeEvent(self, event) -> None:
        if self._worker is not None and self._worker.isRunning():
            res = QMessageBox.question(
                self,
                "Cancel Installation?",
                "Installation is still running. Cancel it and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if res != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._worker.request_cancel()
            self._worker.wait(5000)
        event.accept()


def run_install_wizard() -> int:
    app = QApplication(sys.argv)
    apply_app_theme(app, THEME_DARK_ID)

    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    window = InstallWizardWindow()
    window.show()
    return app.exec()
