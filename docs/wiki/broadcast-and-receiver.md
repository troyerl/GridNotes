# Broadcast and receiver

**See also:** [Wiki home](README.md) · [Live Mode](live-mode.md) · [Drivers tab](drivers-tab.md) · [Settings](settings.md)

GridNotes can share your scouting book and live iRacing session with another device on your **local network** (LAN). The racing PC **broadcasts**; a second PC or laptop **receives**.

- **Broadcaster** — keeps iRacing running; main GridNotes window hides while broadcasting
- **Receiver** — views the broadcaster's book and live session; notes and likes sync **back to the broadcaster**

Notes written on a receiver are **not saved to the receiver's local database**.

---

## Quick comparison

| | Broadcaster | Receiver |
|---|-------------|----------|
| iRacing required | Yes (on this PC) | No |
| Local book visible | Yes (hidden window) | No — sees broadcaster's book |
| Import JSON | Yes | **Disabled** |
| Edit notes / likes | Saved locally | Synced to broadcaster |
| Live Mode | Own iRacing session | Broadcaster's live session |

---

## Broadcast (racing PC)

### Start broadcasting

1. Ensure you are **not** connected as a receiver
2. Click **Broadcast** in the header
3. Main window hides; **GridNotes Broadcast** status dialog appears

### Broadcast status dialog

| Element | Description |
|---------|-------------|
| **Broadcasting scouting data** | Dialog title area |
| **Broadcaster: {hostname}** | This PC's name on the network |
| **Port: 8765** | WebSocket port receivers connect to |
| Receiver status | **Waiting for a receiver…** → **N receiver(s) connected** with names |
| **Audio spotter** | Toggle spotter for this broadcast session only (does not change saved Settings) |
| Hint | Keep iRacing running; receivers use the **Receiver** button |
| **Stop broadcasting** | Ends broadcast and restores main window |

### While broadcasting

- iRacing SDK continues on the broadcaster PC
- Database snapshots and live session updates stream to connected receivers
- Driver note edits from receivers apply to **your** database
- Database re-syncs to receivers every few seconds and after edits

### Stop broadcasting

Click **Stop broadcasting**:

- Receivers are disconnected
- Main GridNotes window returns
- If Live Mode was active and iRacing is connected, Live Mode is restored

---

## Receiver (second device)

### Connect

1. Ensure you are **not** broadcasting on this device
2. Click **Receiver** in the header
3. **Connect to broadcaster** dialog opens

| Element | Description |
|---------|-------------|
| **Broadcasters on this network** | Auto-discovered list |
| **Refresh** | Re-scan the network |
| **Or enter address manually** | IP or hostname + port (default **8765**) |
| **Connect** / **Cancel** | Start or abort connection |

### While connected

A banner appears above the tabs:

| State | Banner text |
|-------|-------------|
| Connecting | **Connecting to {host}…** |
| Loading data | **Connected to {name} — loading scouting data…** |
| Active | **Connected to {name} — receiving scouting data. Notes and likes sync to the broadcaster (not saved on this device).** |

Header shows **Disconnect** button.

### What works on a receiver

- Browse the [Drivers tab](drivers-tab.md) with the broadcaster's book
- Use [Live Mode](live-mode.md) and [Grid Walk](live-mode.md#grid-walk) with the broadcaster's live session
- Write notes and set **Liked** / **Didn't like** — changes sync to broadcaster
- View [Import history](import-history.md) and [Leagues](leagues.md) data from broadcaster's snapshot

### What is disabled on a receiver

- **Import race JSON…** — tooltip explains import is disabled while receiving
- Local database edits do not persist on the receiver

### Disconnect

Click **Disconnect** (or close the app):

- Restores your **local** scouting book
- Clears broadcast live session data from the UI
- Re-enables Import
- Restarts local iRacing SDK worker (if available on this PC)
- Status: **Waiting for iRacing…**

### Unexpected broadcaster disconnect (v1.0.52+)

If the broadcaster closes the app or stops broadcasting without warning:

- Receiver automatically restores your local book
- Live session cards clear
- Import is re-enabled
- Message: **Broadcaster disconnected — restored your local scouting book.**

---

## Settings cross-reference

**Settings → Live Mode → Broadcast to another device** explains the header buttons and shows receiver connection status when active.

See [Settings → Live Mode](settings.md#broadcast-to-another-device).

---

## Network requirements

- Both devices on the **same local network**
- Port **8765** (WebSocket) must be reachable between devices
- Windows firewall may prompt on first broadcast — allow GridNotes on private networks

Discovery uses LAN broadcast; if auto-discovery fails, enter the broadcaster's IP manually.

---

## Typical setups

### Second monitor at the desk

Receiver on the same PC is not the intended model — use one GridNotes window. Broadcast is for a **separate device**.

### Laptop beside the sim

1. Sim PC broadcasts while racing
2. Laptop receives for Live Mode on a side screen
3. Add notes on the laptop during the race — they save on the sim PC

### Steward / spotter

A passenger or crew member on a tablet/laptop can scout and flag drivers; marks appear on the driver's main book.

---

## Troubleshooting

| Problem | Try |
|---------|-----|
| Receiver can't find broadcaster | **Refresh** list, or enter IP manually. Confirm both on same Wi‑Fi/LAN. |
| Connected but no data | Broadcaster must still be running. Wait for snapshot or restart broadcast. |
| Live Mode blank on receiver | Update to v1.0.51+ (receiver crash fix). Reconnect. |
| Stale data after broadcaster stopped | Update to v1.0.52+ (auto-restore on disconnect). Click **Disconnect** manually. |

[← Wiki home](README.md) · [Live Mode →](live-mode.md)
