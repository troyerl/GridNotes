"""Tests for gridnotes.services.app_update helpers."""

from gridnotes.services.app_update import UpdateCheckResult, _normalize_tag


def test_normalize_tag():
    assert _normalize_tag("v1.0.44") == "1.0.44"
    assert _normalize_tag("1.0.44") == "1.0.44"


def test_update_check_result_fields():
    result = UpdateCheckResult(
        ok=True,
        message="Update ready",
        current_version="1.0.43",
        latest_version="1.0.44",
        release_notes="Fixes",
        download_url="https://example.com",
        update_available=True,
    )
    assert result.update_available
    assert result.latest_version == "1.0.44"
