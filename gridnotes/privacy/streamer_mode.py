"""UI-only driver anonymization for streaming and screenshots."""

from __future__ import annotations

from ..safety.safety_index import SafetyIndex, tier_label

STREAMER_MODE_KEY = "streamer_mode"

_ALIAS_MODULO = 100


def is_streamer_mode_enabled(raw: str | None) -> bool:
    return (raw or "0").strip() == "1"


def driver_alias_number(cust_id: int) -> int:
    """Stable 0–99 tag from iRacing customer ID (same driver, same tag)."""
    return int(cust_id) % _ALIAS_MODULO


def driver_risk_suffix(safety: SafetyIndex | None) -> str:
    if safety is None or safety.tier == "unknown":
        return "Unknown"
    return tier_label(safety.tier)


def streamer_display_name(
    cust_id: int,
    safety: SafetyIndex | None = None,
    *,
    compact: bool = False,
    car_number: str | None = None,
) -> str:
    """
    Public-facing alias for streamer mode.

    When *car_number* is set (Live Mode session), uses the car's racing number,
    e.g. ``Driver #42 (Moderate risk)``. Otherwise falls back to a stable cust-id tag.
    """
    if car_number and str(car_number).strip():
        num = str(car_number).strip().lstrip("#")
        label = f"Driver #{num}"
    else:
        tag = driver_alias_number(cust_id)
        label = f"Driver #{tag:02d}"

    risk = driver_risk_suffix(safety)
    if compact and safety is not None and safety.tier != "unknown":
        short = {"Low risk": "Low", "Moderate risk": "Mod", "High risk": "High"}.get(
            risk, risk
        )
        return f"{label} ({short})"
    return f"{label} ({risk})"


def display_driver_name(
    cust_id: int,
    real_name: str,
    safety: SafetyIndex | None,
    *,
    streamer_mode: bool,
    compact_table: bool = False,
) -> str:
    if streamer_mode:
        return streamer_display_name(cust_id, safety, compact=compact_table)
    return (real_name or "").strip() or "Unknown"


def streamer_detail_meta(*, last_seen_fmt: str) -> str:
    """Detail panel subtitle while streamer mode is on (no cust ID or real name)."""
    if last_seen_fmt and last_seen_fmt != "—":
        return f"Streamer mode · Last raced {last_seen_fmt} ET"
    return "Streamer mode · Real names hidden on screen"


def mask_cust_id_display(cust_id: int, *, streamer_mode: bool) -> str:
    if streamer_mode:
        return "—"
    return str(cust_id)
