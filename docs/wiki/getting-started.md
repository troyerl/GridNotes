# Getting started

**See also:** [Wiki home](README.md) · [Drivers tab](drivers-tab.md) · [Settings](settings.md) · [Live Mode](live-mode.md)

---

## What GridNotes does

GridNotes helps you remember who you raced against and whether you want to race with them again. It combines:

- A **sortable driver table** with stats and a **Grid Safety Index** (0–100)
- **Scouting notes** and **Liked / Didn't like** marks per driver
- **JSON import** of iRacing race results to build history
- **Live scouting** while iRacing is running (Windows) — filter to the current session and switch to **Live Mode**
- **Leagues** — group drivers into seasons and tag league races
- **Broadcast / Receiver** — share your book and live session with a second device on your LAN

All data is stored locally in SQLite under your user data folder (for example `%LOCALAPPDATA%\GridNotes` on Windows).

---

## Main window layout

When you open GridNotes you see:

1. **Header bar** — connection status, **Broadcast**, **Receiver**, **Streamer mode**, **Live Mode**
2. **Tab bar** — **Drivers**, **Import history**, **Leagues**, **Settings**
3. **Tab content** — the active page

There is no traditional menu bar. Everything is reachable from tabs, header buttons, and the Settings sidebar.

---

## The four tabs at a glance

### [Drivers tab](drivers-tab.md)

Your primary workspace:

- Searchable, sortable **driver table**
- **Import race JSON…** to add race history
- Right-hand **Driver details** panel for notes, marks, and Safety Index breakdown
- **Live Mode** replaces the table with large driver cards when toggled on

### [Import history tab](import-history.md)

A log of every subsession you have imported:

- Search by session ID
- **Mark as league race…** to tag a session and add its drivers to a league season roster

### [Leagues tab](leagues.md)

Organize recurring series or club racing:

- Create **Leagues** and **Seasons**
- Build season rosters with **Add current session** or bulk add from your scouting book

### [Settings tab](settings.md)

Configure theme, timezone, note tag chips, data retention, backups, updates, audio spotter, and more. Click **Save settings** when you change something.

---

## Typical workflows

### Build your scouting book after a race

1. Export or save iRacing **event_result** JSON from a completed race
2. On the **[Drivers tab](drivers-tab.md)**, click **Import race JSON…**
3. Select the file — drivers appear in the table with updated stats
4. Select a driver → write notes → **Liked** or **Didn't like** → **Save notes**
5. Check **[Import history](import-history.md)** to confirm the session is recorded

### Scout before a race (solo PC)

1. Start iRacing and join a session (practice, qualifying, or race)
2. GridNotes status shows **Live — … · N drivers**
3. Enable **Current session only** on the Drivers tab to filter the table
4. Toggle **Live Mode** (header button or **Ctrl+L**) for large driver cards
5. Before the green flag, enable **Grid Walk** inside Live Mode — see [Live Mode guide](live-mode.md#grid-walk)

### Run a league season

1. Create a league and season on the **[Leagues tab](leagues.md)**
2. After each league race, either:
   - Import JSON and **Mark as league race…** on **[Import history](import-history.md)**, or
   - Use **Add current session** on the Leagues tab while still in iRacing
3. League members show a **League** column in the driver table and badges in Live Mode

### Scout on a second monitor or laptop

1. Racing PC: click **Broadcast** — see [Broadcast and receiver](broadcast-and-receiver.md)
2. Second device: click **Receiver** and connect
3. View Live Mode and notes on the receiver; edits sync back to the broadcaster

---

## Header controls (always visible)

| Button | Purpose |
|--------|---------|
| **Broadcast** | Share scouting book + live iRacing session over LAN. Main window hides while broadcasting. |
| **Receiver** | Connect to another PC's broadcast and view their book + live session. |
| **Disconnect** | Visible while connected as receiver. Restores your local book. |
| **Streamer mode** | Replace real names with aliases on screen (database unchanged). |
| **Live Mode** | Switch Drivers tab to high-contrast live cards. |
| **Status badge** | iRacing connection state, driver count, or receiver status. |

Details: [Broadcast and receiver](broadcast-and-receiver.md) · [Live Mode](live-mode.md)

---

## Safety Index in one sentence

Each driver gets a **Grid Safety Index** (0–100) based on incidents, DNFs, and position loss across races in your book. Higher scores mean higher risk. Green / gold / red row tints and **Liked** / **Disliked** marks help you spot people quickly.

Open **Scouting guide…** on the Drivers tab for the full color and tier breakdown.

---

## Where to go next

| Goal | Read |
|------|------|
| Master the driver table and notes | [Drivers tab](drivers-tab.md) |
| Understand live cards and Grid Walk | [Live Mode](live-mode.md) |
| Tag league races | [Import history](import-history.md) + [Leagues](leagues.md) |
| Configure the app | [Settings](settings.md) |
| Use two PCs | [Broadcast and receiver](broadcast-and-receiver.md) |
| Quick keys | [Keyboard shortcuts](keyboard-shortcuts.md) |

[← Wiki home](README.md)
