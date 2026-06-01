# GridNotes code structure

Python code lives under `racing_book/`, grouped by responsibility.

```
racing_book/
├── app/              Application entry & config
│   ├── racebook_app.py    Main window (Drivers, Settings, SDK)
│   ├── app_icon.py        Window / taskbar icon
│   ├── app_version.py     Version string (1.2.25)
│   └── feature_flags.py   Feature toggles
│
├── ui/               Qt screens, theme, table styling
│   ├── theme.py / theme_tokens.py / appearance.py
│   ├── ui_widgets.py      Accordion, settings nav
│   ├── driver_table.py      Driver list table
│   ├── safety_widgets.py  Safety Index panel
│   ├── live_session.py      Live Mode view
│   └── settings_tab.py      Settings tab
│
├── data/             SQLite & driver records
│   ├── db.py              Database path, settings keys
│   ├── queries.py         SQL for stats / details
│   ├── driver_models.py   Row models for UI
│   ├── driver_cleanup.py  Remove zero-race drivers
│   └── data_retention.py  Expire old race results
│
├── iracing/          iRacing SDK & API
│   ├── iracing_worker.py       Live SDK polling
│   ├── iracing_import.py       JSON / API import logic
│   ├── import_worker.py        Background JSON import
│   ├── iracing_data_api.py     Data API client
│   ├── iracing_data_api_config.py
│   ├── iracing_api_fetch_worker.py
│   ├── iracing_oauth_guide.py  OAuth help HTML
│   └── session_kind.py         Practice / race / etc.
│
├── safety/           Safety Index algorithm
│   └── safety_index.py
│
├── services/         Cross-cutting app services
│   ├── log_config.py       gridnotes.log
│   ├── user_feedback.py    Dialogs + error logging
│   ├── app_update.py       GitHub / git update check
│   └── app_update_worker.py
│
├── core/             Small shared helpers
│   ├── utils.py
│   └── timestamps.py
│
└── installer/        Graphical source installer
    ├── window.py
    ├── logic.py
    ├── worker.py
    └── shortcuts.py
```

**Entry points**

| File | Purpose |
|------|---------|
| `main.py` | Run GridNotes |
| `install_gui.py` | Run install wizard |

**Import style**

Use the package path, for example:

```python
from racing_book.data.db import connect_db
from racing_book.ui.theme import apply_app_theme
```
