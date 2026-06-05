"""Tests for gridnotes.iracing.spotter_telemetry."""

from tests.conftest import MockIRacing

from gridnotes.iracing.spotter_telemetry import (
    SPOTTER_GAP_SECONDS,
    build_car_idx_to_cust_id,
    find_car_behind,
    is_green_flag_run,
    resolve_cust_id_behind,
)


def test_build_car_idx_to_cust_id():
    ir = MockIRacing(
        {
            "DriverInfo": {
                "Drivers": [
                    {"CarIdx": 0, "UserID": 100, "UserName": "Player"},
                    {"CarIdx": 1, "UserID": 200, "UserName": "Rival"},
                ]
            }
        }
    )
    mapping = build_car_idx_to_cust_id(ir)
    assert mapping[0] == 100
    assert mapping[1] == 200


def test_is_green_flag_run_false_on_yellow():
    ir = MockIRacing(
        {
            "IsReplayPlaying": False,
            "SessionFlags": 0x0002,  # yellow only
            "PlayerCarIdx": 0,
            "CarIdxOnPitRoad": [False],
            "Speed": 50.0,
        }
    )
    assert is_green_flag_run(ir) is False


def test_is_green_flag_run_true():
    ir = MockIRacing(
        {
            "IsReplayPlaying": False,
            "SessionFlags": 0x0004,  # green
            "PlayerCarIdx": 0,
            "CarIdxOnPitRoad": [False],
            "Speed": 50.0,
        }
    )
    assert is_green_flag_run(ir) is True


def test_find_car_behind():
    ir = MockIRacing(
        {
            "PlayerCarIdx": 0,
            "CarIdxLapDistPct": [0.50, 0.48],
            "CarIdxLap": [3, 3],
            "CarIdxOnPitRoad": [False, False],
            "CarIdxEstTime": [100.0, 101.0],
            "LapCurrentLapTime": 90.0,
        }
    )
    result = find_car_behind(ir, max_gap_sec=SPOTTER_GAP_SECONDS)
    assert result is not None
    car_idx, gap = result
    assert car_idx == 1
    assert 0 < gap <= SPOTTER_GAP_SECONDS


def test_resolve_cust_id_behind():
    ir = MockIRacing(
        {
            "PlayerCarIdx": 0,
            "CarIdxLapDistPct": [0.50, 0.48],
            "CarIdxLap": [3, 3],
            "CarIdxOnPitRoad": [False, False],
            "CarIdxEstTime": [100.0, 101.0],
            "LapCurrentLapTime": 90.0,
        }
    )
    mapping = {0: 100, 1: 200}
    resolved = resolve_cust_id_behind(ir, mapping)
    assert resolved is not None
    cust_id, gap = resolved
    assert cust_id == 200
