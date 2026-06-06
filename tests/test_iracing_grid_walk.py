"""Tests for gridnotes.iracing.grid_walk."""

from tests.conftest import MockIRacing

from gridnotes.iracing.grid_walk import (
    GridSlot,
    build_car_idx_directory,
    parse_starting_grid,
    slots_to_payload,
)


def test_build_car_idx_directory_skips_pace_car():
    ir = MockIRacing(
        {
            "DriverInfo": {
                "Drivers": [
                    {"CarIdx": 0, "UserID": 1, "UserName": "Alice"},
                    {"CarIdx": 1, "UserName": "Pace Car", "UserID": 0},
                ]
            }
        }
    )
    directory = build_car_idx_directory(ir)
    assert 0 in directory
    assert 1 not in directory


def test_parse_starting_grid_from_car_idx_position():
    ir = MockIRacing(
        {
            "PlayerCarIdx": 0,
            "SessionNum": 0,
            "DriverInfo": {
                "Drivers": [
                    {"CarIdx": 0, "UserID": 10, "UserName": "P1"},
                    {"CarIdx": 1, "UserID": 20, "UserName": "P2"},
                ]
            },
            "CarIdxPosition": [1, 2],
            "SessionInfo": {
                "Sessions": [
                    {
                        "SessionNum": 0,
                        "SessionType": "Race",
                        "ResultsPositions": [
                            {"Position": 1, "UserID": 10, "UserName": "P1"},
                            {"Position": 2, "UserID": 20, "UserName": "P2"},
                        ],
                    }
                ]
            },
        }
    )
    parsed = parse_starting_grid(ir)
    assert parsed is not None
    slots, player_cust = parsed
    assert len(slots) == 2
    assert slots[0].position == 1
    assert slots[0].cust_id == 10
    assert player_cust == 10


def test_parse_starting_grid_prefers_race_session_during_qualifying():
    ir = MockIRacing(
        {
            "PlayerCarIdx": 1,
            "SessionNum": 0,
            "DriverInfo": {
                "Drivers": [
                    {"CarIdx": 0, "UserID": 10, "UserName": "P1"},
                    {"CarIdx": 1, "UserID": 20, "UserName": "P2"},
                ]
            },
            "CarIdxPosition": [2, 1],
            "SessionInfo": {
                "Sessions": [
                    {
                        "SessionNum": 0,
                        "SessionType": "Qualifying",
                    },
                    {
                        "SessionNum": 1,
                        "SessionType": "Race",
                        "ResultsPositions": [
                            {"Position": 1, "UserID": 10, "UserName": "P1"},
                            {"Position": 2, "UserID": 20, "UserName": "P2"},
                        ],
                    },
                ]
            },
        }
    )
    parsed = parse_starting_grid(ir)
    assert parsed is not None
    slots, player_cust = parsed
    assert [slot.position for slot in slots] == [1, 2]
    assert [slot.cust_id for slot in slots] == [10, 20]
    assert player_cust == 20


def test_parse_starting_grid_uses_race_results_not_live_order():
    """During a race CarIdxPosition is live order; grid walk should use starting grid."""
    ir = MockIRacing(
        {
            "PlayerCarIdx": 0,
            "SessionNum": 1,
            "DriverInfo": {
                "Drivers": [
                    {"CarIdx": 0, "UserID": 10, "UserName": "P1"},
                    {"CarIdx": 1, "UserID": 20, "UserName": "P2"},
                ]
            },
            "CarIdxPosition": [2, 1],
            "SessionInfo": {
                "Sessions": [
                    {"SessionNum": 0, "SessionType": "Qualifying"},
                    {
                        "SessionNum": 1,
                        "SessionType": "Race",
                        "ResultsPositions": [
                            {"Position": 1, "UserID": 10, "UserName": "P1"},
                            {"Position": 2, "UserID": 20, "UserName": "P2"},
                        ],
                    },
                ]
            },
        }
    )
    parsed = parse_starting_grid(ir)
    assert parsed is not None
    slots, _ = parsed
    assert [slot.cust_id for slot in slots] == [10, 20]


def test_slots_to_payload():
    slots = [
        GridSlot(position=1, cust_id=10, name="Alice", car_idx=0),
        GridSlot(position=2, cust_id=20, name="Bob", car_idx=1),
    ]
    payload = slots_to_payload(slots)
    assert len(payload) == 2
    assert payload[0]["cust_id"] == 10
