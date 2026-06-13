"""Tests for league and season membership."""

from gridnotes.data.leagues import (
    add_members_to_season,
    clear_session_league_race,
    count_driver_candidates,
    create_league,
    create_season,
    delete_league,
    delete_season,
    ensure_driver_exists,
    fetch_driver_candidates,
    fetch_leagues,
    fetch_league_membership_labels,
    fetch_members,
    fetch_seasons,
    fetch_session_league_race,
    mark_session_league_race,
    remove_members_from_season,
    rename_league,
)


def _seed_drivers(conn, drivers: list[tuple[int, str]]) -> None:
    for cust_id, name in drivers:
        ensure_driver_exists(conn.cursor(), cust_id, name)
    conn.commit()


def test_create_league_and_season(memory_conn):
    league_id = create_league(memory_conn, "Club Racing")
    memory_conn.commit()
    season_id = create_season(memory_conn, league_id, "2026 S1")
    memory_conn.commit()

    leagues = fetch_leagues(memory_conn)
    assert len(leagues) == 1
    assert leagues[0].name == "Club Racing"

    seasons = fetch_seasons(memory_conn, league_id)
    assert len(seasons) == 1
    assert seasons[0].name == "2026 S1"
    assert seasons[0].member_count == 0
    assert seasons[0].id == season_id


def test_add_and_remove_members(memory_conn):
    _seed_drivers(
        memory_conn,
        [(101, "Alice"), (102, "Bob"), (103, "Charlie")],
    )
    league_id = create_league(memory_conn, "League A")
    season_id = create_season(memory_conn, league_id, "Season 1")
    memory_conn.commit()

    added = add_members_to_season(
        memory_conn,
        season_id,
        [(101, "Alice"), (102, "Bob")],
    )
    memory_conn.commit()
    assert added == 2

    members = fetch_members(memory_conn, season_id)
    assert [m.cust_id for m in members] == [101, 102]
    assert members[0].driver_name == "Alice"

    duplicate_add = add_members_to_season(
        memory_conn,
        season_id,
        [(101, "Alice"), (103, "Charlie")],
    )
    memory_conn.commit()
    assert duplicate_add == 1

    removed = remove_members_from_season(memory_conn, season_id, [101])
    memory_conn.commit()
    assert removed == 1
    assert [m.cust_id for m in fetch_members(memory_conn, season_id)] == [102, 103]


def test_driver_candidates_exclude_season_members(memory_conn):
    _seed_drivers(memory_conn, [(1, "One"), (2, "Two"), (3, "Three")])
    league_id = create_league(memory_conn, "L")
    season_id = create_season(memory_conn, league_id, "S")
    add_members_to_season(memory_conn, season_id, [(1, "One")])
    memory_conn.commit()

    candidates = fetch_driver_candidates(memory_conn, season_id)
    assert {c.cust_id for c in candidates} == {2, 3}
    assert count_driver_candidates(memory_conn, season_id) == 2

    filtered = fetch_driver_candidates(memory_conn, season_id, search="Two")
    assert len(filtered) == 1
    assert filtered[0].cust_id == 2


def test_separate_leagues_and_seasons(memory_conn):
    _seed_drivers(memory_conn, [(10, "Ten"), (20, "Twenty")])
    league_a = create_league(memory_conn, "A")
    league_b = create_league(memory_conn, "B")
    season_a1 = create_season(memory_conn, league_a, "2025")
    season_a2 = create_season(memory_conn, league_a, "2026")
    season_b1 = create_season(memory_conn, league_b, "2026")
    add_members_to_season(memory_conn, season_a1, [(10, "Ten")])
    add_members_to_season(memory_conn, season_a2, [(20, "Twenty")])
    add_members_to_season(memory_conn, season_b1, [(10, "Ten"), (20, "Twenty")])
    memory_conn.commit()

    assert [m.cust_id for m in fetch_members(memory_conn, season_a1)] == [10]
    assert [m.cust_id for m in fetch_members(memory_conn, season_a2)] == [20]
    assert len(fetch_members(memory_conn, season_b1)) == 2

    seasons_a = fetch_seasons(memory_conn, league_a)
    counts = {s.name: s.member_count for s in seasons_a}
    assert counts == {"2025": 1, "2026": 1}


def test_delete_league_cascades(memory_conn):
    _seed_drivers(memory_conn, [(1, "One")])
    league_id = create_league(memory_conn, "Temp")
    season_id = create_season(memory_conn, league_id, "S1")
    add_members_to_season(memory_conn, season_id, [(1, "One")])
    memory_conn.commit()

    delete_league(memory_conn, league_id)
    memory_conn.commit()

    assert fetch_leagues(memory_conn) == []
    assert fetch_seasons(memory_conn, league_id) == []
    assert fetch_members(memory_conn, season_id) == []


def test_delete_season_cascades_memberships(memory_conn):
    _seed_drivers(memory_conn, [(5, "Five")])
    league_id = create_league(memory_conn, "Keep")
    season_id = create_season(memory_conn, league_id, "Drop")
    add_members_to_season(memory_conn, season_id, [(5, "Five")])
    memory_conn.commit()

    delete_season(memory_conn, season_id)
    memory_conn.commit()

    assert fetch_seasons(memory_conn, league_id) == []
    assert fetch_members(memory_conn, season_id) == []
    assert count_driver_candidates(memory_conn, season_id) == 1


def test_rename_league(memory_conn):
    league_id = create_league(memory_conn, "Old Name")
    memory_conn.commit()
    rename_league(memory_conn, league_id, "New Name")
    memory_conn.commit()
    assert fetch_leagues(memory_conn)[0].name == "New Name"


def test_add_members_creates_missing_driver_row(memory_conn):
    league_id = create_league(memory_conn, "L")
    season_id = create_season(memory_conn, league_id, "S")
    memory_conn.commit()

    added = add_members_to_season(
        memory_conn,
        season_id,
        [(999, "New Driver")],
    )
    memory_conn.commit()
    assert added == 1

    row = memory_conn.execute(
        "SELECT driver_name FROM drivers WHERE cust_id = 999"
    ).fetchone()
    assert row[0] == "New Driver"


def test_mark_and_clear_session_league_race(memory_conn):
    league_id = create_league(memory_conn, "Club")
    season_id = create_season(memory_conn, league_id, "2026 S1")
    memory_conn.commit()

    result = mark_session_league_race(
        memory_conn,
        12345,
        league_id,
        season_id=season_id,
    )
    memory_conn.commit()
    assert result.drivers_in_session == 0
    assert result.drivers_added == 0

    tagged = fetch_session_league_race(memory_conn, 12345)
    assert tagged is not None
    assert tagged.league_name == "Club"
    assert tagged.season_name == "2026 S1"

    mark_session_league_race(memory_conn, 12345, league_id)
    memory_conn.commit()
    retagged = fetch_session_league_race(memory_conn, 12345)
    assert retagged is not None
    assert retagged.season_id is None

    assert clear_session_league_race(memory_conn, 12345)
    memory_conn.commit()
    assert fetch_session_league_race(memory_conn, 12345) is None
    assert not clear_session_league_race(memory_conn, 12345)


def test_mark_session_league_race_adds_session_drivers(memory_conn):
    memory_conn.executemany(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (?, ?)",
        [(1, "Alice"), (2, "Bob")],
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (?, ?, 1, 0)
        """,
        [(1, 100), (2, 100), (3, 100)],
    )
    league_id = create_league(memory_conn, "Club")
    season_id = create_season(memory_conn, league_id, "2026 S1")
    add_members_to_season(memory_conn, season_id, [(1, "Alice")])
    memory_conn.commit()

    result = mark_session_league_race(
        memory_conn,
        100,
        league_id,
        season_id=season_id,
    )
    memory_conn.commit()

    assert result.drivers_in_session == 3
    assert result.drivers_added == 2
    assert {member.cust_id for member in fetch_members(memory_conn, season_id)} == {
        1,
        2,
        3,
    }

    again = mark_session_league_race(
        memory_conn,
        100,
        league_id,
        season_id=season_id,
    )
    memory_conn.commit()
    assert again.drivers_added == 0


def test_fetch_league_membership_labels(memory_conn):
    memory_conn.executemany(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (?, ?)",
        [(1, "Alice"), (2, "Bob")],
    )
    league_a = create_league(memory_conn, "Club A")
    league_b = create_league(memory_conn, "Club B")
    season_a = create_season(memory_conn, league_a, "2026 S1")
    season_b = create_season(memory_conn, league_b, "2026 S1")
    add_members_to_season(memory_conn, season_a, [(1, "Alice")])
    add_members_to_season(memory_conn, season_b, [(1, "Alice"), (2, "Bob")])
    memory_conn.commit()

    labels = fetch_league_membership_labels(memory_conn, [1, 2, 99])
    assert labels[1] == "Club A · 2026 S1, Club B · 2026 S1"
    assert labels[2] == "Club B · 2026 S1"
    assert 99 not in labels

    from gridnotes.data.leagues import compact_league_indicator, league_membership_tooltip

    assert compact_league_indicator(labels[1]) == "League"
    assert compact_league_indicator(labels[2]) == "Club B"
    tooltip = league_membership_tooltip(labels[1])
    assert "League memberships:" in tooltip
    assert "Club A · 2026 S1" in tooltip
    assert "Club B · 2026 S1" in tooltip


def test_delete_league_removes_session_tags(memory_conn):
    league_id = create_league(memory_conn, "Temp")
    mark_session_league_race(memory_conn, 999, league_id)
    memory_conn.commit()

    delete_league(memory_conn, league_id)
    memory_conn.commit()

    assert fetch_session_league_race(memory_conn, 999) is None
