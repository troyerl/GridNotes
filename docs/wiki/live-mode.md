# Live Mode

**See also:** [Wiki home](README.md) · [Drivers tab](drivers-tab.md) · [Settings](settings.md) · [Broadcast and receiver](broadcast-and-receiver.md) · [Leagues](leagues.md)

**Live Mode** is a high-contrast scouting view for in-race use. It replaces the driver table inside the **Drivers** tab with large driver cards optimized for quick reading at a glance.

Toggle it with the header **Live Mode** button or **Ctrl+L**.

---

## When to use Live Mode

| Situation | Suggestion |
|-----------|------------|
| Practice / qualifying | Enable **Current session only** on [Drivers tab](drivers-tab.md), then turn on Live Mode to review the field |
| Pre-green flag | Enable **Grid Walk** (below) to see your grid neighbors |
| During the race | Scan cards for Safety Index, marks, and notes |
| Second monitor / receiver | [Broadcast receiver](broadcast-and-receiver.md) shows the broadcaster's live session in the same Live Mode UI |

Live Mode requires an active live scouting session from iRacing (or a broadcaster feed). If not connected:

> Not connected to iRacing — join a session to see live driver cards.

---

## Live Session header

| Element | Description |
|---------|-------------|
| **Live Session** | View title |
| Session meta | e.g. **Session #{id} · Race** or **Session #{id} · Qualifying** |
| **Audio spotter** | Windows only — spoken warning when a flagged driver is ~1.5s behind during green-flag running. Same setting as [Settings → Live Mode](settings.md#audio-spotter). |
| **Grid Walk** | Toggle starting-grid layout — see [Grid Walk](#grid-walk) |
| **Guide** | Opens Scouting guide dialog |
| Driver count | e.g. **24 drivers** or **24 drivers · scouting only (not saved yet)** |

During practice/qualifying, drivers are scouted live but **not saved to your book until the race session starts**.

---

## Context area

- **Context banner** — series, track, and session details from iRacing
- **At a glance** — summary of flagged drivers in the session (counts of high Safety Index, disliked, etc.)

---

## Driver cards (default view)

Each card shows one driver in the current session. Cards are ordered by **how many races you have on record** — most history at the top, drivers new to your book at the bottom. (Grid Walk keeps starting-grid order.)

| Element | Meaning |
|---------|---------|
| **Name** | Driver name (alias in streamer mode) |
| **New** badge | No race history in your book yet |
| **League** badge | On a [league season roster](leagues.md) — hover for details |
| Profile text | Safety Index verdict summary |
| **Liked** / **Disliked** label | Your mark from the scouting book |
| **Avg Inc**, **DNF**, **Last SR**, **Together** | Key stats at a glance — **Together** counts imported races you both were in |
| **▸ / ▾** | Tap the card (or chevron) to expand scouting details inline — notes, full stats, liked/disliked |
| **Safety Index** | Score + tier (**LOW** / **MODERATE** / **HIGH**) with color |

### Interacting with cards

- **Click a card** (or the **▸** chevron, or **Enter** / **Space** when focused) → expands an accordion with full scouting details inline — stats, notes, liked/disliked. Click again to collapse. You stay in Live Mode.
- **Together** shows how many imported races you share with that driver. Set **Hide your name** on the Drivers tab to your iRacing name if the count shows **—**.

---

## Grid Walk

**Grid Walk** is a sub-view inside Live Mode showing the **starting grid** in a staggered two-column layout (odd positions left, even right).

### When to use it

Between qualifying and the green flag — review who is **ahead of you in your column** and **beside you on the grid** before the start.

Toggle with the **Grid Walk** checkbox in the Live Session header.

### What you see

- **Summary line** — e.g. **You start P5 of 24 — review neighbors before the green flag.**
- **At a glance** summary
- **Hint text** — explains which cars are highlighted; warns if flagged drivers are ahead or beside you
- Grid rows: **P{n}**, name, **New**, **League**, Safety score + trend arrow, mark (**Liked** / **Disliked** / **Risk**)

### Highlight roles

| Highlight | Meaning |
|-----------|---------|
| **You** | Your car on the grid |
| **Ahead** | Car directly ahead in your column |
| **Beside** | Grid neighbor in the adjacent column |

If the grid is not loaded yet:

> Starting grid not available yet — wait for the race session to load.

Click any row to expand scouting details inline (same as Live Mode cards). Click again to collapse.

---

## Audio spotter (Windows)

When enabled:

- Uses text-to-speech during green-flag running
- Warns when a **disliked** or **high Safety Index** driver is approximately **1.5 seconds behind**
- Can be toggled from Live Mode header or [Settings → Live Mode](settings.md#audio-spotter)
- On the **broadcaster** PC, a separate broadcast-session toggle exists in the Broadcast status dialog

Requires iRacing to be running. Disabled on macOS and Linux.

---

## Streamer mode interaction

With **Streamer mode** on (header toggle):

- Card names show aliases (e.g. **Driver #14**) instead of real names
- Safety Index, marks, and notes still work normally
- Database and saved notes are unchanged — only on-screen display is affected

---

## Broadcast receiver

When connected as a [receiver](broadcast-and-receiver.md):

- Live Mode shows the **broadcaster's** live session and scouting data
- Notes and likes you add sync back to the broadcaster
- If the broadcaster disconnects, v1.0.52+ restores your local book and clears live session data

---

## Connections

| Feature | Related guide |
|---------|---------------|
| Toggle Live Mode | [Drivers tab](drivers-tab.md) · [Keyboard shortcuts](keyboard-shortcuts.md) |
| Current session filter | [Drivers tab → Current session only](drivers-tab.md#controls-row) |
| League badges | [Leagues](leagues.md) |
| Audio spotter setting | [Settings](settings.md#audio-spotter) |
| Two-device setup | [Broadcast and receiver](broadcast-and-receiver.md) |

[← Wiki home](README.md) · [Drivers tab →](drivers-tab.md)
