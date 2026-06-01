"""PyQt6 install wizard window."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ui.appearance import THEME_DARK_ID
from ..app.app_icon import load_app_icon
from ..ui.theme import apply_app_theme, configure_widget_scrollbars

from .logic import (
    check_python,
    default_build_output_dir,
    default_install_location,
    default_install_location_hint,
    find_project_root,
    is_valid_install_root,
    normalize_chosen_install_dir,
    simple_install_location_hint,
    user_local_install_location,
    venv_python,
    venv_pythonw,
)
from .worker import InstallWorker


class InstallWizardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._source_root = find_project_root(Path.cwd())
        if not (self._source_root / "requirements.txt").is_file():
            self._source_root = find_project_root()
        self._install_root = default_install_location()
        self._worker: InstallWorker | None = None
        self._install_succeeded = False

        self.setWindowTitle("Install GridNotes")
        self.setMinimumSize(680, 620)
        self.resize(760, 660)

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
            "Extract the download anywhere you like, then click Install GridNotes below. "
            "GridNotes will be installed like a normal Windows app. "
            "This may take a few minutes and you only need to do it once."
        )
        intro.setObjectName("sectionHint")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        download_label = QLabel(
            "Your download folder (extract anywhere — GridNotes does not run from here):\n"
            f"{self._source_root}"
        )
        download_label.setObjectName("statValue")
        download_label.setWordWrap(True)
        download_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(download_label)

        install_label = QLabel("Where to install GridNotes")
        install_label.setObjectName("statInlineLabel")
        layout.addWidget(install_label)

        install_row = QHBoxLayout()
        install_row.setSpacing(8)
        self.install_path_input = QLineEdit(str(self._install_root))
        self.install_path_input.setPlaceholderText("Recommended install folder")
        install_row.addWidget(self.install_path_input, stretch=1)
        self.btn_browse_install = QPushButton("Choose folder…")
        self.btn_browse_install.clicked.connect(self._browse_install_dir)
        install_row.addWidget(self.btn_browse_install)
        layout.addLayout(install_row)

        install_hint = QLabel(simple_install_location_hint())
        install_hint.setObjectName("sectionHint")
        install_hint.setWordWrap(True)
        layout.addWidget(install_hint)

        ok, python_message = check_python()
        if ok:
            self.python_label = QLabel("Python is installed. You are ready to continue.")
            self.python_label.setObjectName("sectionHint")
        else:
            self.python_label = QLabel(
                "Python is not set up yet.\n\n"
                "1. Go to https://www.python.org/downloads/\n"
                "2. Download and run the installer\n"
                "3. On the first screen, turn ON “Add python.exe to PATH”\n"
                "4. Close this window and double-click Install GridNotes.bat again"
            )
            self.python_label.setObjectName("emptyState")
        self.python_label.setWordWrap(True)
        layout.addWidget(self.python_label)

        self.desktop_checkbox = QCheckBox("Put a GridNotes icon on my Desktop")
        self.desktop_checkbox.setChecked(True)
        layout.addWidget(self.desktop_checkbox)

        self.advanced_toggle = QCheckBox("Show advanced options")
        self.advanced_toggle.setChecked(False)
        self.advanced_toggle.toggled.connect(self._on_advanced_toggled)
        layout.addWidget(self.advanced_toggle)

        self.advanced_panel = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_panel)
        advanced_layout.setContentsMargins(12, 0, 0, 0)
        advanced_layout.setSpacing(8)

        advanced_hint = QLabel(default_install_location_hint())
        advanced_hint.setObjectName("sectionHint")
        advanced_hint.setWordWrap(True)
        advanced_layout.addWidget(advanced_hint)

        pf_row = QHBoxLayout()
        pf_row.addStretch()
        self.btn_user_local = QPushButton("Install for only me (no admin)")
        self.btn_user_local.setVisible(sys.platform == "win32")
        self.btn_user_local.clicked.connect(self._use_user_local_location)
        pf_row.addWidget(self.btn_user_local)
        advanced_layout.addLayout(pf_row)

        self.build_checkbox = QCheckBox(
            "Build GridNotes.exe in a separate folder (for sharing with others)"
        )
        self.build_checkbox.setVisible(sys.platform == "win32")
        self.build_checkbox.toggled.connect(self._on_build_toggled)
        advanced_layout.addWidget(self.build_checkbox)

        build_label = QLabel("Build output folder")
        build_label.setObjectName("statInlineLabel")
        advanced_layout.addWidget(build_label)

        build_row = QHBoxLayout()
        build_row.setSpacing(8)
        self.build_path_input = QLineEdit(str(default_build_output_dir(self._install_root)))
        self.build_path_input.setEnabled(False)
        build_row.addWidget(self.build_path_input, stretch=1)
        self.btn_browse_build = QPushButton("Choose folder…")
        self.btn_browse_build.setEnabled(False)
        self.btn_browse_build.clicked.connect(self._browse_build_dir)
        build_row.addWidget(self.btn_browse_build)
        advanced_layout.addLayout(build_row)

        self.advanced_panel.setVisible(False)
        layout.addWidget(self.advanced_panel)

        self.step_label = QLabel("Ready when you are.")
        self.step_label.setObjectName("statInlineLabel")
        layout.addWidget(self.step_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Technical log…")
        self.log_view.setVisible(False)
        log_font = QFont("Menlo" if sys.platform == "darwin" else "Consolas")
        log_font.setPointSize(11)
        self.log_view.setFont(log_font)
        configure_widget_scrollbars(self.log_view, page_step=80)

        self.details_toggle = QCheckBox("Show installation details (technical)")
        self.details_toggle.setChecked(False)
        self.details_toggle.toggled.connect(self.log_view.setVisible)
        layout.addWidget(self.details_toggle)
        layout.addWidget(self.log_view, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.close)
        button_row.addWidget(self.btn_cancel)

        self.btn_install = QPushButton("Install GridNotes")
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
            self.step_label.setText("Install Python first (see steps above).")

    def _on_advanced_toggled(self, checked: bool) -> None:
        self.advanced_panel.setVisible(checked)

    def _on_build_toggled(self, checked: bool) -> None:
        self.build_path_input.setEnabled(checked)
        self.btn_browse_build.setEnabled(checked)
        if checked and not self.build_path_input.text().strip():
            self.build_path_input.setText(
                str(default_build_output_dir(Path(self.install_path_input.text().strip())))
            )

    def _use_user_local_location(self) -> None:
        local = user_local_install_location()
        self.install_path_input.setText(str(local))
        if self.build_checkbox.isChecked():
            self.build_path_input.setText(str(default_build_output_dir(local)))
        if sys.platform == "win32":
            QMessageBox.information(
                self,
                "Install for only me",
                "If Windows already asked for administrator permission, you can close this "
                "window and run:\n\n"
                "Install GridNotes.bat /noelevate\n\n"
                "from your download folder instead.",
            )

    def _browse_install_dir(self) -> None:
        start = self.install_path_input.text().strip() or str(self._source_root)
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Choose install location",
            start,
        )
        if not chosen:
            return
        install_dir = normalize_chosen_install_dir(
            Path(chosen),
            source_root=self._source_root,
        )
        self.install_path_input.setText(str(install_dir))
        if self.build_checkbox.isChecked():
            self.build_path_input.setText(str(default_build_output_dir(install_dir)))

    def _browse_build_dir(self) -> None:
        start = self.build_path_input.text().strip() or str(
            default_build_output_dir(Path(self.install_path_input.text().strip()))
        )
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Choose build output folder",
            start,
        )
        if chosen:
            self.build_path_input.setText(chosen)

    def _resolved_install_root(self) -> Path | None:
        text = self.install_path_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Install location", "Choose a folder to install into.")
            return None
        path = normalize_chosen_install_dir(
            Path(text),
            source_root=self._source_root,
        )
        valid, reason = is_valid_install_root(path)
        if not valid:
            QMessageBox.warning(self, "Install location", reason)
            return None
        return path

    def _resolved_build_output_dir(self) -> Path | None:
        text = self.build_path_input.text().strip()
        if not text:
            QMessageBox.warning(
                self,
                "Build output folder",
                "Choose a folder for the standalone build.",
            )
            return None
        return Path(text).expanduser()

    def append_log(self, line: str) -> None:
        self.log_view.append(line)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def _set_busy(self, busy: bool) -> None:
        self.btn_install.setEnabled(not busy)
        self.build_checkbox.setEnabled(not busy)
        self.install_path_input.setEnabled(not busy)
        self.btn_browse_install.setEnabled(not busy)
        self.advanced_toggle.setEnabled(not busy)
        self.advanced_panel.setEnabled(not busy)
        self.btn_user_local.setEnabled(not busy)
        self.details_toggle.setEnabled(not busy)
        self.build_path_input.setEnabled(not busy and self.build_checkbox.isChecked())
        self.btn_browse_build.setEnabled(not busy and self.build_checkbox.isChecked())
        self.desktop_checkbox.setEnabled(not busy)
        self.btn_cancel.setText("Cancel" if busy else "Close")
        if busy:
            self.btn_launch.setVisible(False)

    def _start_install(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        install_root = self._resolved_install_root()
        if install_root is None:
            return

        build_output_dir = None
        if self.build_checkbox.isChecked():
            build_output_dir = self._resolved_build_output_dir()
            if build_output_dir is None:
                return

        if (
            install_root.resolve() != self._source_root.resolve()
            and install_root.exists()
            and any(install_root.iterdir())
        ):
            res = QMessageBox.question(
                self,
                "Install into this folder?",
                f"{install_root}\n\n"
                "This folder is not empty. GridNotes will copy files here and may "
                "overwrite existing files with the same names. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if res != QMessageBox.StandardButton.Yes:
                return

        self._install_root = install_root.resolve()
        self.log_view.clear()
        self.progress.setValue(0)
        self._install_succeeded = False
        self._set_busy(True)
        self.step_label.setText("Installing… please wait.")
        self.log_view.setVisible(True)
        self.details_toggle.setChecked(True)

        self._worker = InstallWorker(
            source_root=self._source_root,
            install_root=self._install_root,
            build_standalone=self.build_checkbox.isChecked(),
            build_output_dir=build_output_dir,
            create_desktop_shortcut=self.desktop_checkbox.isChecked(),
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
        root = self._install_root

        if self.build_checkbox.isChecked():
            build_dir = Path(self.build_path_input.text().strip()).expanduser()
            standalone_exe = build_dir / "GridNotes" / "GridNotes.exe"
            if standalone_exe.is_file():
                subprocess.Popen(
                    [str(standalone_exe)],
                    cwd=str(standalone_exe.parent),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self.close()
                return

        venv_dir = root / ".venv"
        py = venv_pythonw(venv_dir)
        if not py.is_file():
            py = venv_python(venv_dir)
        main_py = root / "main.py"
        if not py.is_file() or not main_py.is_file():
            QMessageBox.warning(
                self,
                "Cannot Launch",
                "Run Install first, or use the Desktop GridNotes icon.",
            )
            return
        subprocess.Popen(
            [str(py), str(main_py)],
            cwd=str(root),
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
