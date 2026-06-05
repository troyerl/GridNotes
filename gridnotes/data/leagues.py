"""League and season membership for grouping drivers."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class League:
    id: int
    name: str
    created_at: str


@dataclass(frozen=True)
class LeagueSeason:
    id: int
    league_id: int
    name: str
    created_at: str
    member_count: int = 0


@dataclass(frozen=True)
class LeagueMember:
    cust_id: int
    driver_name: str
    added_at: str


@dataclass(frozen=True)
class DriverCandidate:
    cust_id: int
    driver_name: str


@dataclass(frozen=True)
class LeagueRaceSession:
    subsession_id: int
    league_id: int
    league_name: str
    season_id: int | None
    season_name: str | None
    marked_at: str


@dataclass(frozen=True)
class MarkLeagueRaceResult:
    drivers_in_session: int
    drivers_added: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_driver_exists(
    cursor: sqlite3.Cursor,
    cust_id: int,
    driver_name: str | None = None,
) -> None:
    name = (driver_name or "").strip() or f"Driver #{cust_id}"
    cursor.execute(
        """
        INSERT INTO drivers (cust_id, driver_name)
        VALUES (?, ?)
        ON CONFLICT(cust_id) DO UPDATE SET
            driver_name = CASE
                WHEN TRIM(COALESCE(excluded.driver_name, '')) != ''
                THEN excluded.driver_name
                ELSE drivers.driver_name
            END
        """,
        (cust_id, name),
    )


def fetch_leagues(conn: sqlite3.Connection) -> list[League]:
    rows = conn.execute(
        """
        SELECT id, name, created_at
        FROM leagues
        ORDER BY name COLLATE NOCASE
        """
    ).fetchall()
    return [League(id=row[0], name=row[1], created_at=row[2]) for row in rows]


def create_league(conn: sqlite3.Connection, name: str) -> int:
    clean = (name or "").strip()
    if not clean:
        raise ValueError("League name is required.")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO leagues (name, created_at) VALUES (?, ?)",
        (clean, _utc_now()),
    )
    return int(cursor.lastrowid)


def rename_league(conn: sqlite3.Connection, league_id: int, name: str) -> None:
    clean = (name or "").strip()
    if not clean:
        raise ValueError("League name is required.")
    conn.execute(
        "UPDATE leagues SET name = ? WHERE id = ?",
        (clean, league_id),
    )


def delete_league(conn: sqlite3.Connection, league_id: int) -> None:
    conn.execute(
        """
        DELETE FROM league_memberships
        WHERE season_id IN (
            SELECT id FROM league_seasons WHERE league_id = ?
        )
        """,
        (league_id,),
    )
    conn.execute("DELETE FROM league_seasons WHERE league_id = ?", (league_id,))
    conn.execute("DELETE FROM league_race_sessions WHERE league_id = ?", (league_id,))
    conn.execute("DELETE FROM leagues WHERE id = ?", (league_id,))


def fetch_seasons(conn: sqlite3.Connection, league_id: int) -> list[LeagueSeason]:
    rows = conn.execute(
        """
        SELECT
            s.id,
            s.league_id,
            s.name,
            s.created_at,
            COUNT(m.id) AS member_count
        FROM league_seasons s
        LEFT JOIN league_memberships m ON m.season_id = s.id
        WHERE s.league_id = ?
        GROUP BY s.id
        ORDER BY s.created_at DESC, s.name COLLATE NOCASE
        """,
        (league_id,),
    ).fetchall()
    return [
        LeagueSeason(
            id=row[0],
            league_id=row[1],
            name=row[2],
            created_at=row[3],
            member_count=int(row[4] or 0),
        )
        for row in rows
    ]


def create_season(conn: sqlite3.Connection, league_id: int, name: str) -> int:
    clean = (name or "").strip()
    if not clean:
        raise ValueError("Season name is required.")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO league_seasons (league_id, name, created_at)
        VALUES (?, ?, ?)
        """,
        (league_id, clean, _utc_now()),
    )
    return int(cursor.lastrowid)


def delete_season(conn: sqlite3.Connection, season_id: int) -> None:
    conn.execute("DELETE FROM league_memberships WHERE season_id = ?", (season_id,))
    conn.execute("DELETE FROM league_seasons WHERE id = ?", (season_id,))


def fetch_members(conn: sqlite3.Connection, season_id: int) -> list[LeagueMember]:
    rows = conn.execute(
        """
        SELECT m.cust_id, COALESCE(d.driver_name, ''), m.added_at
        FROM league_memberships m
        LEFT JOIN drivers d ON d.cust_id = m.cust_id
        WHERE m.season_id = ?
        ORDER BY d.driver_name COLLATE NOCASE, m.cust_id
        """,
        (season_id,),
    ).fetchall()
    return [
        LeagueMember(
            cust_id=int(row[0]),
            driver_name=row[1] or f"Driver #{row[0]}",
            added_at=row[2],
        )
        for row in rows
    ]


def add_members_to_season(
    conn: sqlite3.Connection,
    season_id: int,
    drivers: list[tuple[int, str | None]],
) -> int:
    """Add drivers to a season. Returns count of newly added memberships."""
    if not drivers:
        return 0
    cursor = conn.cursor()
    added = 0
    now = _utc_now()
    for cust_id, driver_name in drivers:
        ensure_driver_exists(cursor, cust_id, driver_name)
        cursor.execute(
            """
            INSERT OR IGNORE INTO league_memberships (season_id, cust_id, added_at)
            VALUES (?, ?, ?)
            """,
            (season_id, cust_id, now),
        )
        if cursor.rowcount:
            added += 1
    return added


def remove_members_from_season(
    conn: sqlite3.Connection,
    season_id: int,
    cust_ids: list[int],
) -> int:
    if not cust_ids:
        return 0
    placeholders = ",".join("?" * len(cust_ids))
    cursor = conn.cursor()
    cursor.execute(
        f"""
        DELETE FROM league_memberships
        WHERE season_id = ? AND cust_id IN ({placeholders})
        """,
        (season_id, *cust_ids),
    )
    return cursor.rowcount


def fetch_driver_candidates(
    conn: sqlite3.Connection,
    season_id: int,
    *,
    search: str = "",
    limit: int = 200,
    offset: int = 0,
) -> list[DriverCandidate]:
    query = (search or "").strip()
    params: list[object] = [season_id]
    search_sql = ""
    if query:
        search_sql = (
            " AND (CAST(d.cust_id AS TEXT) LIKE ? "
            "OR d.driver_name LIKE ? COLLATE NOCASE)"
        )
        like = f"%{query}%"
        params.extend([like, like])
    params.extend([limit, offset])
    rows = conn.execute(
        f"""
        SELECT d.cust_id, COALESCE(d.driver_name, '')
        FROM drivers d
        WHERE d.cust_id NOT IN (
            SELECT cust_id FROM league_memberships WHERE season_id = ?
        )
        {search_sql}
        ORDER BY d.driver_name COLLATE NOCASE, d.cust_id
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()
    return [
        DriverCandidate(
            cust_id=int(row[0]),
            driver_name=row[1] or f"Driver #{row[0]}",
        )
        for row in rows
    ]


def count_driver_candidates(
    conn: sqlite3.Connection,
    season_id: int,
    *,
    search: str = "",
) -> int:
    query = (search or "").strip()
    params: list[object] = [season_id]
    search_sql = ""
    if query:
        search_sql = (
            " AND (CAST(d.cust_id AS TEXT) LIKE ? "
            "OR d.driver_name LIKE ? COLLATE NOCASE)"
        )
        like = f"%{query}%"
        params.extend([like, like])
    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM drivers d
        WHERE d.cust_id NOT IN (
            SELECT cust_id FROM league_memberships WHERE season_id = ?
        )
        {search_sql}
        """,
        params,
    ).fetchone()
    return int(row[0] or 0) if row else 0


def fetch_league_membership_labels(
    conn: sqlite3.Connection,
    cust_ids: list[int] | set[int] | None = None,
) -> dict[int, str]:
    """Map cust_id to comma-separated league · season labels."""
    params: list[int] = []
    where = ""
    if cust_ids is not None:
        ids = sorted({int(cid) for cid in cust_ids})
        if not ids:
            return {}
        placeholders = ",".join("?" * len(ids))
        where = f"WHERE m.cust_id IN ({placeholders})"
        params = ids

    rows = conn.execute(
        f"""
        SELECT m.cust_id, l.name, ls.name
        FROM league_memberships m
        JOIN league_seasons ls ON ls.id = m.season_id
        JOIN leagues l ON l.id = ls.league_id
        {where}
        ORDER BY m.cust_id, l.name COLLATE NOCASE, ls.name COLLATE NOCASE
        """,
        params,
    ).fetchall()

    grouped: dict[int, list[str]] = {}
    for cust_id, league_name, season_name in rows:
        cid = int(cust_id)
        if season_name:
            label = f"{league_name} · {season_name}"
        else:
            label = str(league_name)
        grouped.setdefault(cid, []).append(label)
    return {cid: ", ".join(parts) for cid, parts in grouped.items()}


def compact_league_indicator(full_label: str) -> str:
    """Short label for table cells and badges."""
    if not full_label:
        return ""
    if ", " in full_label:
        return "League"
    league_part = full_label.split(" · ", 1)[0].strip()
    if len(league_part) <= 12:
        return league_part
    return f"{league_part[:11]}…"


def fetch_subsession_drivers(
    conn: sqlite3.Connection,
    subsession_id: int,
) -> list[tuple[int, str | None]]:
    rows = conn.execute(
        """
        SELECT DISTINCT rr.cust_id, COALESCE(NULLIF(TRIM(d.driver_name), ''), '')
        FROM race_results rr
        LEFT JOIN drivers d ON d.cust_id = rr.cust_id
        WHERE rr.subsession_id = ?
          AND rr.cust_id IS NOT NULL
        ORDER BY d.driver_name COLLATE NOCASE, rr.cust_id
        """,
        (subsession_id,),
    ).fetchall()
    return [(int(row[0]), row[1] or None) for row in rows]


def mark_session_league_race(
    conn: sqlite3.Connection,
    subsession_id: int,
    league_id: int,
    *,
    season_id: int | None = None,
) -> MarkLeagueRaceResult:
    if subsession_id <= 0:
        raise ValueError("A valid subsession ID is required.")
    if season_id is not None:
        row = conn.execute(
            "SELECT league_id FROM league_seasons WHERE id = ?",
            (season_id,),
        ).fetchone()
        if row is None or int(row[0]) != league_id:
            raise ValueError("Season does not belong to the selected league.")
    conn.execute(
        """
        INSERT INTO league_race_sessions (
            subsession_id, league_id, season_id, marked_at
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(subsession_id) DO UPDATE SET
            league_id = excluded.league_id,
            season_id = excluded.season_id,
            marked_at = excluded.marked_at
        """,
        (subsession_id, league_id, season_id, _utc_now()),
    )
    drivers = fetch_subsession_drivers(conn, subsession_id)
    added = 0
    if season_id is not None and drivers:
        added = add_members_to_season(conn, season_id, drivers)
    return MarkLeagueRaceResult(
        drivers_in_session=len(drivers),
        drivers_added=added,
    )


def clear_session_league_race(conn: sqlite3.Connection, subsession_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM league_race_sessions WHERE subsession_id = ?",
        (subsession_id,),
    )
    return cursor.rowcount > 0


def fetch_session_league_race(
    conn: sqlite3.Connection,
    subsession_id: int,
) -> LeagueRaceSession | None:
    row = conn.execute(
        """
        SELECT
            lrs.subsession_id,
            lrs.league_id,
            l.name,
            lrs.season_id,
            ls.name,
            lrs.marked_at
        FROM league_race_sessions lrs
        JOIN leagues l ON l.id = lrs.league_id
        LEFT JOIN league_seasons ls ON ls.id = lrs.season_id
        WHERE lrs.subsession_id = ?
        """,
        (subsession_id,),
    ).fetchone()
    if row is None:
        return None
    return LeagueRaceSession(
        subsession_id=int(row[0]),
        league_id=int(row[1]),
        league_name=str(row[2]),
        season_id=int(row[3]) if row[3] is not None else None,
        season_name=str(row[4]) if row[4] is not None else None,
        marked_at=str(row[5]),
    )
