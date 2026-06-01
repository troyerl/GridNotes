"""Grid Safety Index — composite risk score from incidents, DNF rate, and position loss."""

from __future__ import annotations

from dataclasses import dataclass

MIN_RACES_FOR_SCORE = 3
INCIDENTS_MAX = 8.0
DNF_RATE_MAX = 0.35
POS_LOSS_MAX = 5.0

WEIGHT_INCIDENTS = 0.50
WEIGHT_DNF = 0.35
WEIGHT_POS = 0.15

RISKY_SCORE_THRESHOLD = 55


@dataclass(frozen=True)
class SafetyIndex:
    score: float
    tier: str
    profile: str
    incidents_norm: float
    dnf_norm: float
    pos_norm: float
    avg_inc: float | None
    dnf_rate: float
    avg_pos_delta: float | None
    total_races: int
    reasons: tuple[str, ...]
    risky: bool


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _tier_for_score(score: float, has_data: bool) -> str:
    if not has_data:
        return "unknown"
    if score < 35:
        return "low"
    if score < RISKY_SCORE_THRESHOLD:
        return "moderate"
    return "high"


def _profile_label(inc_norm: float, dnf_norm: float, pos_norm: float, has_data: bool) -> str:
    if not has_data:
        return "Insufficient race history"
    if inc_norm > 0.6 and dnf_norm < 0.4:
        return "Fast but aggressive"
    if inc_norm < 0.4 and dnf_norm > 0.6:
        return "Slow and unreliable"
    if inc_norm > 0.5 and dnf_norm > 0.5:
        return "High incident + DNF risk"
    if pos_norm > 0.5 and inc_norm < 0.5:
        return "Slow and unpredictable"
    if inc_norm < 0.35 and dnf_norm < 0.35 and pos_norm < 0.35:
        return "Clean"
    return "Moderate risk"


def compute_safety_index(
    *,
    avg_inc,
    total_races,
    dnf_total,
    avg_pos_delta,
) -> SafetyIndex:
    races_val = _safe_int(total_races)
    dnf_val = _safe_int(dnf_total)
    inc_val = _safe_float(avg_inc)
    pos_val = _safe_float(avg_pos_delta)

    has_data = races_val >= MIN_RACES_FOR_SCORE
    dnf_rate = (dnf_val / races_val) if races_val > 0 else 0.0

    inc_norm = _clamp(inc_val / INCIDENTS_MAX, 0, 1) if inc_val is not None else 0.0
    dnf_norm = _clamp(dnf_rate / DNF_RATE_MAX, 0, 1)
    pos_norm = (
        _clamp(max(0.0, -pos_val) / POS_LOSS_MAX, 0, 1) if pos_val is not None else 0.0
    )

    if has_data:
        score = 100.0 * (
            WEIGHT_INCIDENTS * inc_norm
            + WEIGHT_DNF * dnf_norm
            + WEIGHT_POS * pos_norm
        )
    else:
        score = 0.0

    tier = _tier_for_score(score, has_data)
    profile = _profile_label(inc_norm, dnf_norm, pos_norm, has_data)

    reasons: list[str] = []
    if inc_val is not None and inc_norm >= 0.5:
        reasons.append(f"High incidents ({inc_val:.1f}/race)")
    elif inc_val is not None and inc_norm >= 0.35:
        reasons.append(f"Elevated incidents ({inc_val:.1f}/race)")

    if races_val > 0 and dnf_norm >= 0.5:
        reasons.append(f"DNF rate {dnf_rate * 100:.0f}% ({dnf_val}/{races_val})")
    elif races_val > 0 and dnf_norm >= 0.35:
        reasons.append(f"DNFs ({dnf_val}/{races_val})")

    if pos_val is not None and pos_norm >= 0.4:
        reasons.append(f"Loses positions ({pos_val:.1f} avg +/-)")

    risky = has_data and score >= RISKY_SCORE_THRESHOLD

    return SafetyIndex(
        score=round(score, 1),
        tier=tier,
        profile=profile,
        incidents_norm=inc_norm,
        dnf_norm=dnf_norm,
        pos_norm=pos_norm,
        avg_inc=inc_val,
        dnf_rate=dnf_rate,
        avg_pos_delta=pos_val,
        total_races=races_val,
        reasons=tuple(reasons),
        risky=risky,
    )


def empty_safety() -> SafetyIndex:
    """Safety index for drivers with no usable history (cleared UI, unknown drivers)."""
    return compute_safety_index(
        avg_inc=None,
        total_races=0,
        dnf_total=0,
        avg_pos_delta=None,
    )


def safety_tooltip(safety: SafetyIndex) -> str:
    if safety.tier == "unknown":
        return f"Safety Index: {safety.profile}"
    lines = [
        f"Safety Index {safety.score:.0f}/100 — {safety.profile}",
        *safety.reasons,
    ]
    return "\n".join(lines)


TIER_COLORS_HEX = {
    "low": "#6ee7a8",
    "moderate": "#f5c26b",
    "high": "#f08080",
    "unknown": "#9aa3b2",
}

TIER_COLORS_RGB = {
    "low": (110, 231, 168),
    "moderate": (245, 194, 107),
    "high": (240, 128, 128),
    "unknown": (154, 163, 178),
}

TIER_LABELS = {
    "low": "Low risk",
    "moderate": "Moderate risk",
    "high": "High risk",
}


def tier_color_hex(tier: str) -> str:
    return TIER_COLORS_HEX.get(tier, TIER_COLORS_HEX["unknown"])


def tier_qcolor(tier: str):
    from PyQt6.QtGui import QColor

    r, g, b = TIER_COLORS_RGB.get(tier, TIER_COLORS_RGB["unknown"])
    return QColor(r, g, b)


def tier_label(tier: str) -> str:
    return TIER_LABELS.get(tier, "")


def unknown_history_message(total_races: int, *, for_table: bool = False) -> str:
    if total_races > 0:
        return "Not enough races for Safety Index (need 3+)" if for_table else "Not enough history to determine risk"
    return "No race history in book"


def live_sort_score(safety: SafetyIndex, total_races: int) -> float:
    if safety.tier != "unknown":
        return safety.score
    return 0.0 if total_races > 0 else -1.0
