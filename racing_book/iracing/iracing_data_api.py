"""iRacing Data API client helpers (iracingdataapi package)."""

from __future__ import annotations

import json
import logging
import sys
from json import JSONDecodeError
from typing import Any

from .iracing_data_api_config import get_access_token

logger = logging.getLogger(__name__)

PACKAGE_NAME = "iracingdataapi"
_import_error: str | None = None


def package_available() -> bool:
    global _import_error
    try:
        import iracingdataapi  # noqa: F401

        _import_error = None
        return True
    except ImportError as exc:
        _import_error = str(exc)
        logger.debug("%s import failed: %s", PACKAGE_NAME, exc)
        return False


def package_unavailable_reason() -> str:
    if package_available():
        return ""

    exc = _import_error or ""
    if "No module named 'iracingdataapi'" in exc or "No module named iracingdataapi" in exc:
        return (
            f"{PACKAGE_NAME} is not installed for this Python.\n"
            f"Run: {sys.executable} -m pip install -r requirements.txt"
        )

    if exc:
        return (
            f"{PACKAGE_NAME} could not be loaded ({exc}).\n"
            f"Run: {sys.executable} -m pip install -r requirements.txt"
        )

    return (
        f"{PACKAGE_NAME} is not available.\n"
        f"Run: {sys.executable} -m pip install -r requirements.txt"
    )


def _api_response_to_dict(data: Any) -> dict:
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")
    raise TypeError(f"Unexpected API response type: {type(data)!r}")


def _is_invalid_api_response(exc: BaseException) -> bool:
    try:
        from requests.exceptions import JSONDecodeError as RequestsJSONDecodeError
    except ImportError:
        RequestsJSONDecodeError = ()  # type: ignore[misc, assignment]

    return isinstance(exc, (JSONDecodeError, RequestsJSONDecodeError))


def format_api_error(exc: BaseException) -> str:
    """Turn API/client exceptions into a short message for the UI and log."""
    if _is_invalid_api_response(exc):
        return (
            "iRacing returned an invalid API response (not JSON). "
            "Your OAuth access token may be expired or invalid — obtain a new one."
        )

    try:
        from iracingdataapi.exceptions import AccessTokenInvalid

        if isinstance(exc, AccessTokenInvalid):
            return (
                "OAuth access token is invalid or expired. "
                "Obtain a new token from your iRacing OAuth application."
            )
    except ImportError:
        pass

    if isinstance(exc, ValueError):
        return str(exc)

    if isinstance(exc, RuntimeError):
        text = str(exc).strip()
        if text:
            return text

    if isinstance(exc, OSError) and getattr(exc, "strerror", None):
        return f"Network error: {exc.strerror}"

    text = str(exc).strip()
    return text or exc.__class__.__name__


def build_client_from_token(access_token: str):
    """Create an irDataClient from an OAuth access token."""
    from iracingdataapi.client import irDataClient

    token = (access_token or "").strip()
    if not token:
        raise ValueError("OAuth access token is required.")
    return irDataClient(access_token=token, silent=True)


def build_client():
    """Create an irDataClient from saved settings. Raises ValueError if misconfigured."""
    return build_client_from_token(get_access_token())


def test_connection_with_token(access_token: str) -> tuple[bool, str]:
    """Verify an OAuth token without reading from saved settings."""
    if not package_available():
        reason = package_unavailable_reason()
        logger.warning("iRacing Data API connection test failed: %s", reason)
        return False, reason

    try:
        client = build_client_from_token(access_token)
        client.member_info()
        logger.info("iRacing Data API connection test succeeded")
        return True, "Connected to iRacing Data API."
    except Exception as exc:
        friendly = format_api_error(exc)
        if _is_invalid_api_response(exc):
            logger.warning("iRacing Data API connection test failed: %s", friendly)
        else:
            logger.exception(
                "iRacing Data API connection test failed: %s", friendly
            )
        return False, friendly


def test_connection() -> tuple[bool, str]:
    """Verify saved OAuth token by calling a lightweight API endpoint."""
    return test_connection_with_token(get_access_token())


def _flatten_session_results(session: dict) -> dict:
    """Expand team driver_results into individual result rows for the importer."""
    results = session.get("results")
    if not isinstance(results, list):
        return session

    flat: list[dict] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        nested = row.get("driver_results")
        if isinstance(nested, list) and nested:
            for driver in nested:
                if not isinstance(driver, dict):
                    continue
                merged = {**row, **driver}
                if driver.get("display_name"):
                    merged["name"] = driver["display_name"]
                flat.append(merged)
        else:
            if row.get("display_name") and not row.get("name"):
                row = {**row, "name": row["display_name"]}
            flat.append(row)

    return {**session, "results": flat}


def normalize_api_result_payload(payload: dict) -> dict:
    """Normalize API /results/get payload for event_result import."""
    data = dict(payload)
    sessions = data.get("session_results")
    if isinstance(sessions, list):
        data["session_results"] = [
            _flatten_session_results(s) for s in sessions if isinstance(s, dict)
        ]
    return data


def fetch_event_result_json(subsession_id: int, *, include_licenses: bool = True) -> dict:
    """
    Fetch subsession results and wrap as iRacing event_result JSON for the importer.
    Raises on network/auth errors; returns wrapper even if race session is empty.
    """
    if subsession_id <= 0:
        raise ValueError("Invalid subsession id.")

    client = build_client()
    raw = client.result(subsession_id=int(subsession_id), include_licenses=include_licenses)
    payload = normalize_api_result_payload(_api_response_to_dict(raw))
    return {"type": "event_result", "data": payload}


def event_result_has_race_data(event_result: dict) -> bool:
    from .iracing_import import parse_races_from_json

    races, _, _ = parse_races_from_json(event_result)
    for race in races:
        results = race.get("results") if isinstance(race, dict) else None
        if isinstance(results, list) and results:
            return True
    return False
