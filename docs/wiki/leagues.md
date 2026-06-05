# Leagues

**See also:** [Wiki home](README.md) · [Import history](import-history.md) · [Drivers tab](drivers-tab.md) · [Live Mode](live-mode.md)

The **Leagues** tab organizes drivers into **Leagues** and **Seasons** — useful for club racing, league series, or any recurring group you want to track separately from the general scouting book.

League members show a **League** column in the [Drivers tab](drivers-tab.md) and **League** badges in [Live Mode](live-mode.md).

---

## Layout

Split view:

```
┌──────────────────┬────────────────────────────────────────┐
│ Leagues          │  {League} · {Season}                   │
│  [list]          │  Roster table                          │
│  New / Rename /  │  Add current session · Remove selected │
│  Delete          │                                        │
│                  │  Add from scouting book                │
│ Seasons          │  [search] Select all · Add selected    │
│  [list]          │  Candidates table (checkboxes)         │
│  New / Delete    │                                        │
└──────────────────┴────────────────────────────────────────┘
```

---

## Leagues panel (left)

| Control | What it does |
|---------|--------------|
| **Leagues** list | Select a league to manage its seasons |
| **New league…** | Create a league — prompts for **League name:** |
| **Rename…** | Rename the selected league |
| **Delete** | Deletes the league and **all its seasons, memberships, and league race tags** (confirmation required) |

---

## Seasons panel (left)

| Control | What it does |
|---------|--------------|
| **Seasons** list | Shows `{season name} ({member count})` |
| **New season…** | Create a season — prompts for **Season name:** |
| **Delete** | Deletes the season and its memberships (confirmation required) |

---

## Season roster (right)

**Title:** `{League name} · {Season name}` — or **Select a league and season** when nothing is selected.

### Roster table

| Column | Content |
|--------|---------|
| **Driver** | Driver name from your scouting book |
| **ID** | iRacing customer ID |

**Multi-select** rows to remove several members at once.

| Control | What it does |
|---------|--------------|
| **Add current session (N)** | Bulk-add all drivers from the current iRacing live session. **N** is the driver count. Disabled if iRacing is not connected or no season is selected. Uses the same live driver list as **Current session only** on the [Drivers tab](drivers-tab.md). |
| **Remove selected** | Remove highlighted drivers from the season roster (does not delete them from your scouting book) |

---

## Add from scouting book

Add drivers who are already in your book but not necessarily in the current iRacing session.

| Control | What it does |
|---------|--------------|
| **Search drivers to add…** | Filter the candidate list by name |
| **Select all shown** | Check every visible candidate |
| **Add selected** | Add checked drivers to the season roster |
| **Candidates table** | Checkbox, **Driver**, **ID** — up to 200 search results |

---

## Three ways to build a roster

### 1. After a league race (while still in iRacing)

1. Create league and season
2. Join the league race in iRacing
3. Click **Add current session (N)**

### 2. After importing JSON

1. Import on [Drivers tab](drivers-tab.md)
2. On [Import history](import-history.md), select the session
3. Click **Mark as league race…** and pick league + season

This tags the session **and** adds all imported drivers to the roster.

### 3. Cherry-pick from your book

1. Select league and season
2. Search in **Add from scouting book**
3. Check drivers → **Add selected**

---

## Where league info appears

| Location | What you see |
|----------|--------------|
| [Drivers tab](drivers-tab.md) — **League** column | Compact indicator; hover for full league and season name |
| [Live Mode](live-mode.md) driver cards | **League** badge |
| [Grid Walk](live-mode.md#grid-walk) | **League** badge on grid rows |
| [Import history](import-history.md) — **League** column | `{League} · {Season}` for tagged sessions |

---

## Tips

1. Create the **League** once, then a new **Season** each year or split.
2. **Mark as league race** on Import history is the fastest post-race workflow if you already import JSON.
3. **Add current session** is best when you don't need a JSON import for roster tracking.
4. Deleting a league is permanent — export a [backup](settings.md#backup--restore) first if unsure.

[← Wiki home](README.md) · [Import history →](import-history.md)
