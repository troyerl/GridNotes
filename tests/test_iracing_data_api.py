"""Tests for gridnotes.iracing.iracing_data_api pure helpers."""

import pytest

pytest.importorskip("iracingdataapi", reason="iracingdataapi optional")

from gridnotes.iracing.iracing_data_api import (
    event_result_has_race_data,
    format_api_error,
    normalize_api_result_payload,
)


def test_format_api_error_value_error():
    msg = format_api_error(ValueError("Connection timeout"))
    assert "timeout" in msg.lower()


def test_event_result_has_race_data_true():
    payload = {
        "type": "event_result",
        "data": {
            "subsession_id": 1,
            "session_results": [
                {
                    "simsession_type_name": "Race",
                    "results": [{"cust_id": 1, "name": "A"}],
                }
            ],
        },
    }
    assert event_result_has_race_data(payload) is True


def test_event_result_has_race_data_false():
    assert event_result_has_race_data({"type": "event_result", "data": {}}) is False


def test_normalize_api_result_payload_flattens():
    payload = {
        "session_results": [
            {"results": [{"display_name": "Alice", "cust_id": 1}]},
        ]
    }
    normalized = normalize_api_result_payload(payload)
    results = normalized["session_results"][0]["results"]
    assert results[0]["name"] == "Alice"
