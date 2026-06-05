# Drivers tab

**See also:** [Wiki home](README.md) · [Getting started](getting-started.md) · [Live Mode](live-mode.md) · [Import history](import-history.md) · [Leagues](leagues.md) · [Settings](settings.md)

The **Drivers** tab is your main scouting workspace. It combines a filterable driver table, import tools, and a detail panel for notes and marks. When **Live Mode** is on, the table is replaced by live driver cards — see [Live Mode](live-mode.md).

---

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Controls: Import · Reset · Current session · Search · …     │
├──────────────────────────────┬──────────────────────────────┤
│ Driver table (+ pagination)  │ Driver details panel         │
│                              │  Safety Index · Stats        │
│                              │  Notes · Liked / Disliked    │
└──────────────────────────────┴──────────────────────────────┘
         OR (when Live Mode is on)
┌─────────────────────────────────────────────────────────────┐
│ Live Session view — see live-mode.md                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Controls row

| Control | What it does |
|---------|--------------|
| **Import race JSON…** | Opens a file picker for iRacing `event_result` JSON or custom `{"races": [...]}` files. Shows progress while importing. Disabled while connected as a [broadcast receiver](broadcast-and-receiver.md). |
| **Reset all data** | Permanently deletes all drivers, notes, and race results after confirmation. |
| **Current session only** | Appears when iRacing live scouting is active. Filters the table to drivers in the current session. During practice/qualifying, drivers are scouted but not saved to your book until the race starts. |
| **Search drivers** | Filters the table by name as you type. In streamer mode, search matches alias or real name. Shortcut: **Ctrl+F**. |
| **Hide your name** | Hides a driver row matching this name (usually your own). |
| **Save hidden name** | Persists the hidden name to settings. |
| **Scouting guide…** | Opens the Safety Index and marks reference dialog. |

**Live session hint** (below controls when not connected):

> Not connected to iRacing yet — start iRacing and join a session to enable.

When connected during qualifying, you may see:

> Qualifying — live scouting enabled. Drivers are added to your book when the race starts.

---

## Driver table

### Columns

| Column | Meaning |
|--------|---------|
| **Driver Name** | Name from your book (alias in streamer mode) |
| **Mark** | **Liked**, **Disliked**, **Risk**, or combinations |
| **League** | Compact badge if driver is on a [league season roster](leagues.md). Hover for league and season name. |
| **Races** | Total races tracked in your book |
| **Safety Index** | 0–100 score with optional trend arrow (↗ ↘ →). Color-coded by tier. |
| **Avg Incidents** | Average incidents per race |
| **Avg Finish** | Average finish position |
| **Avg +/- Pos** | Average positions gained (+) or lost (−) vs starting grid |
| **DNFs** | Total DNFs |
| **Last SR** | Most recent safety rating |
| **Last iRating** | Most recent iRating |
| **Last Series** | Most recent series name |
| **DNF Breakdown** | Counts by DNF type (disconnect, crash, etc.) |
| **Note** | Shows **Notes** when scouting notes exist |
| **ID** | iRacing customer ID (hidden column, used internally) |

### Row colors

| Color | Meaning |
|-------|---------|
| Green tint | **Liked** |
| Red tint | **Disliked** |
| Gold tint | High Safety Index (**Risk**) |
| Default + hover highlight | No strong mark |

### Sorting and pagination

- **Click a column header** to sort. Sort column and order are saved between sessions.
- **Drag column edges** to resize. Widths are saved to settings.
- **Pagination bar** at the bottom: **Showing X–Y of Z drivers**, **Rows per page** (25 / 50 / 100 / 200), **Previous** / **Next**.

### Selecting a driver

- **Click a row** to open the detail panel on the right.
- **Arrow keys** move between rows.
- **Enter** on a selected row focuses the notes editor.

---

## Driver details panel

**Title:** Driver details

When nothing is selected:

> Select a driver from the table to view stats, write scouting notes, and mark whether you liked racing with them.

### Header

- **Driver name** (large)
- Meta line: `ID {cust_id} · Last raced {date}` (streamer mode hides ID)

### Grid Safety Index

Group box showing:

- Score, trend arrow, tier badge (**LOW** / **MODERATE** / **HIGH**)
- Progress bar (`X / 100`)
- Profile summary text
- Component bars: **Incidents**, **DNF rate**, **Pos loss**
- Risk factor callouts or **No major risk factors**
- **Guide** button → Scouting guide dialog

### Stats

**Series**, **Avg finish**, **Avg incidents**, **Races tracked**, **Last iRating**, **Last SR**, **Avg +/- pos**, **DNFs**, **DNF breakdown**

### Scouting notes

- Multi-line text editor. Placeholder example: *Aggressive on restarts, gives room on restarts, weak under pressure…*
- **Quick note templates** — chip buttons configured in [Settings → Data](settings.md#quick-note-tags). Default chips: **Clean**, **Divebombs**, **Blocks**, **Restarts**, **Unpredictable**. Clicking a chip appends text to your notes.

### How was racing with them?

| Button | Effect |
|--------|--------|
| **Liked** | Green row highlight |
| **Didn't like** | Red row highlight |
| **Clear** | Remove preference mark |

### Save notes

Saves notes and marks for the selected driver. Shortcut: **Ctrl+S** / **Cmd+S**.

On a [broadcast receiver](broadcast-and-receiver.md), notes and likes sync to the broadcaster instead of saving locally.

---

## Import race JSON

1. Click **Import race JSON…**
2. Select one or more JSON files
3. Progress dialog shows file count and **Updating the driver list…**
4. Imported sessions appear on [Import history](import-history.md)

**Supported formats:**

- iRacing **`event_result`** (`type: "event_result"`) — imports the Race session
- Custom **`{"races": [{"subsession_id": …, "results": […]}]}`**

Re-importing the same subsession does **not** duplicate rows — each driver/subsession pair is stored once.

---

## Connections to other pages

| From Drivers | To |
|--------------|-----|
| Import race JSON | [Import history](import-history.md) session list |
| League column | [Leagues](leagues.md) season rosters |
| Live Mode toggle | [Live Mode](live-mode.md) cards and Grid Walk |
| Quick note chips | [Settings → Quick note tags](settings.md#quick-note-tags) |
| Broadcast / Receiver | [Broadcast and receiver](broadcast-and-receiver.md) |

---

## Tips

1. **Sort by Safety Index** before a race to spot high-risk drivers quickly.
2. Use **Current session only** + **Live Mode** together during qualifying — see [Live Mode workflows](live-mode.md#when-to-use-live-mode).
3. Click a driver card in Live Mode to jump back here with that row selected and notes open.
4. **Hide your name** keeps your own row out of the list when streaming or sharing screen.

[← Wiki home](README.md) · [Live Mode →](live-mode.md)
