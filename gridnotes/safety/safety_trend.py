"""Recent-race form trend vs lifetime Safety Index."""

from __future__ import annotations

from dataclasses import dataclass

from .safety_index import SafetyIndex, compute_safety_index, safety_tooltip

TREND_RACE_WINDOW = 5
MIN_RACES_FOR_TREND = 3
SIGNIFICANT_TREND_DELTA = 6.0

_DNF_REASON_IDS = frozenset({1, 2, 3, 4})


@dataclass(frozen=True)
class SafetyTrend:
    """Form guide: recent races vs lifetime Safety Index (lower score = safer)."""

    direction: str  # improving, worsening, stable, unknown
    lifetime_score: float | None
    recent_score: float | None
    window_races: int

    @property
    def arrow(self) -> str:
        return {
            "improving": "↗",
            "worsening": "↘",
            "stable": "→",
            "unknown": "",
        }.get(self.direction, "")

    @property
    def icon_name(self) -> str | None:
        return {
            "improving": "arrow-trend-up",
            "worsening": "arrow-trend-down",
            "stable": "arrow-right",
        }.get(self.direction)

    @property
    def color_hex(self) -> str:
        from .safety_index import TIER_COLORS_HEX

        if self.direction == "improving":
            return TIER_COLORS_HEX["low"]
        if self.direction == "worsening":
            return TIER_COLORS_HEX["high"]
        if self.direction == "stable":
            return TIER_COLORS_HEX["unknown"]
        return TIER_COLORS_HEX["unknown"]

    def tooltip_lines(self) -> list[str]:
        if self.direction == "unknown":
            if self.window_races > 0 and self.window_races < MIN_RACES_FOR_TREND:
                return [
                    f"Form guide: need {MIN_RACES_FOR_TREND}+ recent races "
                    f"({self.window_races} in last {TREND_RACE_WINDOW})"
                ]
            return ["Form guide: not enough recent race data"]

        assert self.lifetime_score is not None and self.recent_score is not None
        lines = [
            f"Lifetime Safety Index: {self.lifetime_score:.0f}",
            f"Last {self.window_races} races: {self.recent_score:.0f}",
        ]
        delta = self.lifetime_score - self.recent_score
        if self.direction == "improving":
            lines.append(f"Recent form is cleaner (↓ {delta:.0f} risk points)")
        elif self.direction == "worsening":
            lines.append(f"Recent form is riskier (↑ {abs(delta):.0f} risk points)")
        else:
            lines.append("Recent form matches lifetime average")
        return lines

    def tooltip(self) -> str:
        return "\n".join(self.tooltip_lines())


def safety_index_from_recent_races(
    rows: list[tuple],
) -> tuple[SafetyIndex, int]:
    """
  Build a Safety Index from recent race rows.

  Each row: (incidents, finish_position, starting_position, reason_out_id).
  """
    if not rows:
        return compute_safety_index(
            avg_inc=None, total_races=0, dnf_total=0, avg_pos_delta=None
        ), 0

    total = len(rows)
    dnf_total = 0
    inc_sum = 0.0
    inc_count = 0
    pos_sum = 0.0
    pos_count = 0

    for incidents, finish, start, reason_out_id in rows:
        try:
            reason = int(reason_out_id) if reason_out_id is not None else 0
        except (TypeError, ValueError):
            reason = 0
        if reason in _DNF_REASON_IDS:
            dnf_total += 1

        try:
            inc_val = float(incidents) if incidents is not None else None
        except (TypeError, ValueError):
            inc_val = None
        if inc_val is not None:
            inc_sum += inc_val
            inc_count += 1

        try:
            fin = int(finish) if finish is not None else None
            sta = int(start) if start is not None else None
        except (TypeError, ValueError):
            fin, sta = None, None
        if fin is not None and sta is not None:
            pos_sum += sta - fin
            pos_count += 1

    avg_inc = (inc_sum / inc_count) if inc_count else None
    avg_pos = (pos_sum / pos_count) if pos_count else None

    safety = compute_safety_index(
        avg_inc=avg_inc,
        total_races=total,
        dnf_total=dnf_total,
        avg_pos_delta=avg_pos,
    )
    return safety, total


def compute_safety_trend(
    lifetime: SafetyIndex,
    recent_rows: list[tuple],
) -> SafetyTrend:
    """Compare lifetime index to the last *TREND_RACE_WINDOW* races."""
    recent_safety, window_races = safety_index_from_recent_races(recent_rows)

    if lifetime.tier == "unknown":
        return SafetyTrend("unknown", None, None, window_races)

    lifetime_score = float(lifetime.score)

    if window_races < MIN_RACES_FOR_TREND or recent_safety.tier == "unknown":
        return SafetyTrend("unknown", lifetime_score, None, window_races)

    recent_score = float(recent_safety.score)
    delta = lifetime_score - recent_score

    if delta >= SIGNIFICANT_TREND_DELTA:
        direction = "improving"
    elif delta <= -SIGNIFICANT_TREND_DELTA:
        direction = "worsening"
    else:
        direction = "stable"

    return SafetyTrend(
        direction=direction,
        lifetime_score=lifetime_score,
        recent_score=recent_score,
        window_races=window_races,
    )


def compute_safety_trends_for_cust_ids(
    conn,
    lifetime_by_cust: dict[int, SafetyIndex],
    *,
    window: int = TREND_RACE_WINDOW,
) -> dict[int, SafetyTrend]:
    """Batch form-guide trends for many drivers."""
    from ..data.queries import fetch_recent_races_by_cust_ids

    if not lifetime_by_cust:
        return {}

    recent_by_cust = fetch_recent_races_by_cust_ids(
        conn, list(lifetime_by_cust.keys()), limit=window
    )
    trends: dict[int, SafetyTrend] = {}
    for cust_id, lifetime in lifetime_by_cust.items():
        trends[cust_id] = compute_safety_trend(
            lifetime, recent_by_cust.get(cust_id, [])
        )
    return trends


def combined_safety_tooltip(safety: SafetyIndex, trend: SafetyTrend | None) -> str:
    lines = [safety_tooltip(safety)]
    if trend is not None and trend.direction != "unknown":
        lines.extend(trend.tooltip_lines())
    return "\n".join(lines)
