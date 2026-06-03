# GridNotes code structure

Python code lives under the **`gridnotes/`** package.

```
gridnotes/
├── app/                    Application entry & config
│   ├── gridnotes_app.py    Main window (Drivers, Settings, SDK)
│   ├── app_icon.py         Window / taskbar icon
│   ├── app_version.py      Version string
│   └── feature_flags.py    Feature toggles
│
├── ui/                     Qt screens, theme, table styling
│   ├── theme.py / theme_tokens.py / appearance.py
│   ├── ui_widgets.py       Accordion, settings nav
│   ├── driver_table.py     Driver list table
│   ├── safety_widgets.py   Safety Index panel
│   ├── live_session.py     Live Mode view
│   ├── settings_tab.py     Settings tab
│   └── update_progress_dialog.py
│
├── data/                   SQLite & driver records
│   ├── db.py               Database path, settings keys
│   ├── user_paths.py       %LOCALAPPDATA%\GridNotes paths
│   ├── queries.py          SQL for stats / details
│   ├── driver_models.py    Row models for UI
│   ├── driver_cleanup.py   Remove zero-race drivers
│   └── data_retention.py   Expire old race results
│
├── iracing/                iRacing SDK & API
│   ├── iracing_worker.py       Live SDK polling
│   ├── iracing_import.py       JSON / API import logic
│   ├── import_worker.py        Background JSON import
│   ├── iracing_data_api.py     Data API client
│   ├── iracing_data_api_config.py
│   ├── iracing_api_fetch_worker.py
│   ├── iracing_oauth_guide.py  OAuth help HTML
│   └── session_kind.py         Practice / race / etc.
│
├── safety/                 Safety Index algorithm
│   └── safety_index.py
│
├── services/               Cross-cutting app services
│   ├── log_config.py       gridnotes.log
│   ├── user_feedback.py    Dialogs + error logging
│   ├── app_update.py       GitHub / git update check
│   └── app_update_worker.py
│
├── platform/               OS-specific runtime (not wizard-only)
│   └── windows/
│       ├── windows_shell.py         Taskbar / shortcut AppUserModelID
│       ├── windows_shell_native.py  PowerShell property store
│       ├── windows_launcher.py      GridNotes.exe (pythonw + icon)
│       └── windows_apps.py          Add/Remove Programs registry
│
├── installer/              Install wizard, updates, shortcuts
│   ├── window.py / worker.py
│   ├── logic.py            Copy tree, venv, launcher, refresh
│   ├── shortcuts.py        Desktop / Start Menu .lnk
│   ├── portable_update.py  In-app ZIP update (robocopy)
│   ├── post_update_cli.py  Post-update batch entry
│   ├── uninstall.py / uninstall_cli.py
│   ├── ensure_python.py
│   └── templates/
│       └── gridnotes_start.py   Bootstrap copied to install root
│
└── core/                   Small shared helpers
    ├── utils.py
    └── timestamps.py
```

**Repo root entry points**

| File | Purpose |
|------|---------|
| `main.py` | Run GridNotes (dev + PyInstaller) |
| `gridnotes_start.py` | Source install bootstrap → `main.py` |
| `install_gui.py` | Install wizard |

**Scripts & docs**

| Path | Purpose |
|------|---------|
| `scripts/` | Build installer, icons, Windows taskbar PS1 |
| `docs/` | Maintainer docs, [RELEASES.md](RELEASES.md), release notes, code structure |

**Import style**

```python
from gridnotes.data.db import connect_db
from gridnotes.platform.windows.windows_shell import apply_window_taskbar_identity
```
