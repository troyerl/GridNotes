# Settings

**See also:** [Wiki home](README.md) · [Drivers tab](drivers-tab.md) · [Live Mode](live-mode.md) · [Getting started](getting-started.md)

The **Settings** tab configures appearance, data management, live scouting options, updates, and legal information.

**Important:** After changing settings, click **Save settings** (top right). The button enables only when there are unsaved changes.

---

## Sidebar sections

| Section | Topics |
|---------|--------|
| **Auto-import** | Automatic race result fetch via iRacing Data API *(shown only when feature flag enabled)* |
| **Appearance** | Timezone, color theme |
| **Data** | Quick note tags, retention, backup, cleanup, storage paths |
| **Live Mode** | Audio spotter, broadcast/receiver info |
| **Maintenance** | Updates, help, support, uninstall |
| **Legal** | License, privacy, disclaimers |

---

## Auto-import

*This section appears only when the auto-import feature flag is enabled in your build.*

| Setting | Description |
|---------|-------------|
| **Automatically fetch results when a race session ends** | Pull results via iRacing Data API after races |
| **OAuth access token** | Paste `access_token` from iRacing OAuth |
| **Test** | Verify the token works |
| **OAuth setup guide** | Accordion with setup instructions when registration is available |

Requires Windows, iRacing running, and the `iracingdataapi` package. OAuth registration may be paused — see in-app notice.

---

## Appearance

### Timezone

| Setting | Description |
|---------|-------------|
| **Display times in** | Combo box: **System default — {your PC timezone}** first, then IANA time zones |

Affects **Last raced** dates, import timestamps on [Import history](import-history.md), and other displayed times. Does not change stored UTC data.

### Color theme

| Setting | Options |
|---------|---------|
| **Theme** | **Dark** / **Light** |

Applies immediately after **Save settings**.

---

## Data

### Quick note tags

Configure the chip buttons above the scouting notes editor on the [Drivers tab](drivers-tab.md).

| Control | Description |
|---------|-------------|
| **Chip label** | Text shown on the button |
| **Note to append (optional)** | Text added to notes when clicked (can differ from label) |
| **Remove** | Delete a tag row |
| **Add tag…** | Add a new tag (max 24) |
| **Reset to defaults** | Restore **Clean**, **Divebombs**, **Blocks**, **Restarts**, **Unpredictable** |

### Race history retention

| Setting | Options |
|---------|---------|
| **Keep race data for** | **Never delete**, **3 months**, **6 months**, **1 year**, **2 years**, **3 years**, **5 years** |

Old **race results** are purged on save. **Notes** and **Liked / Disliked** marks are kept.

### Backup & restore

| Button | Description |
|--------|-------------|
| **Back up database…** | Export `driver_history.db` to a file you choose |
| **Restore from backup…** | Replace current database from a backup file (confirmation required) |

Back up before major changes like [Reset all data](drivers-tab.md) or league deletion.

### Driver cleanup

| Element | Description |
|---------|-------------|
| Status line | Count of drivers with **0 races** in your book |
| **Remove drivers with 0 races** | Delete driver rows that have no imported race history |

### Storage location

| Element | Description |
|---------|-------------|
| Data directory | Path to GridNotes user data (selectable text) |
| **Database file** | Full path and file size |

Typical Windows path: `%LOCALAPPDATA%\GridNotes\driver_history.db`

---

## Live Mode

### Audio spotter

| Setting | Description |
|---------|-------------|
| **Enable audio spotter (co-driver warnings, off by default)** | Windows TTS warning when a flagged driver is ~1.5s behind during green-flag running |

Also toggled from the [Live Mode](live-mode.md) header. Requires iRacing. Disabled on macOS/Linux.

See [Live Mode → Audio spotter](live-mode.md#audio-spotter-windows).

### Broadcast to another device

Informational section explaining **Broadcast** and **Receiver** header buttons. Shows connection status when actively receiving.

See [Broadcast and receiver](broadcast-and-receiver.md).

---

## Maintenance

### Application updates

| Element | Description |
|---------|-------------|
| **Check for updates automatically when GridNotes opens** | Background update check on startup |
| **Your version: …** | Installed version |
| **Check for updates** | Manual check against GitHub releases |
| **Update now** / **Get latest version** | Appears when an update is available (Windows installed builds) |

Update notes: [Release notes](../RELEASE_NOTES.md)

### Help & support

| Button | Description |
|--------|-------------|
| **Scouting guide…** | Safety Index and marks reference dialog |
| **Save support file…** | Export diagnostics bundle for troubleshooting |
| **Open logs folder** | Open user data folder in file manager |

### Uninstall

| Element | Description |
|---------|-------------|
| Install path info | Where GridNotes is installed |
| **Also delete my notes, database, and settings** | Checkbox for full data removal |
| **Uninstall GridNotes…** | Launch uninstaller (Windows installed builds) |

---

## Legal

Informational HTML sections (read only):

| Section | Content |
|---------|---------|
| **License** | Software license summary |
| **Using GridNotes** | Usage terms |
| **iRacing** | iRacing trademark and API notice |
| **Data and privacy** | Local-only data policy |
| **Disclaimer** | No warranty / not affiliated with iRacing |

---

## What happens when you save

**Save settings** triggers:

- Theme and timezone applied app-wide
- Quick note tag chips refreshed on [Drivers tab](drivers-tab.md)
- Retention purge run if policy changed
- Update check preference saved
- OAuth token saved (if Auto-import section visible)

---

## Connections

| Setting | Used on |
|---------|---------|
| Quick note tags | [Drivers tab → notes chips](drivers-tab.md#scouting-notes) |
| Timezone | [Import history](import-history.md) timestamps |
| Audio spotter | [Live Mode](live-mode.md) header |
| Theme | Entire app |
| Backups | All tabs |

[← Wiki home](README.md) · [Drivers tab →](drivers-tab.md)
