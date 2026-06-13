"""Driver row models and live-session entry builders."""

from __future__ import annotations

from dataclasses import dataclass

from ..safety.safety_index import SafetyIndex, compute_safety_index, empty_safety
from ..core.utils import sqlite_row_to_int


def _is_race_dnf(reason_out_id: int | None) -> bool:
    return int(reason_out_id or 0) in (1, 2, 3, 4)


def compare_race_finish_outcome(
    player_finish: int | None,
    player_reason: int | None,
    other_finish: int | None,
    other_reason: int | None,
) -> str | None:
    """Return ``win``, ``loss``, or ``tie`` for the player vs another driver in one race."""
    player_dnf = _is_race_dnf(player_reason)
    other_dnf = _is_race_dnf(other_reason)
    if player_dnf and not other_dnf:
        return "loss"
    if other_dnf and not player_dnf:
        return "win"
    if player_finish is None or other_finish is None:
        return None
    if player_finish < other_finish:
        return "win"
    if player_finish > other_finish:
        return "loss"
    return "tie"


def format_head_to_head_record(
    wins: int,
    losses: int,
    ties: int = 0,
) -> str:
    """Your wins–losses(–ties) vs another driver. First number is always your wins."""
    if wins <= 0 and losses <= 0 and ties <= 0:
        return "—"
    if ties > 0:
        return f"You {wins}–{losses}–{ties}"
    return f"You {wins}–{losses}"


def head_to_head_tooltip(
    wins: int,
    losses: int,
    ties: int = 0,
) -> str:
    """Explain a head-to-head record from your perspective."""
    tie_note = f", {ties} tie{'s' if ties != 1 else ''}" if ties else ""
    return (
        f"Your record vs this driver: {wins} win{'s' if wins != 1 else ''}, "
        f"{losses} loss{'es' if losses != 1 else ''}{tie_note}. "
        "The score is always your wins first, then your losses."
    )


def format_vs_you_outcome(outcome: str | None) -> str:
    """Single-race result when you and the selected driver shared a session."""
    if outcome == "win":
        return "You won"
    if outcome == "loss":
        return "You lost"
    if outcome == "tie":
        return "Tie"
    return "—"


def format_dnf_breakdown(disc: int, eject: int, quit_: int, dq: int, other: int) -> str:
    parts = []
    if disc:
        parts.append(f"Disc:{disc}")
    if eject:
        parts.append(f"Eject:{eject}")
    if quit_:
        parts.append(f"Quit:{quit_}")
    if dq:
        parts.append(f"DQ:{dq}")
    if other:
        parts.append(f"Other:{other}")
    return ", ".join(parts) if parts else ""


@dataclass(frozen=True)
class DriverTableRow:
    name: str
    avg_inc: float | None
    avg_fin: float | None
    total_races: int
    last_ir: int | None
    last_sr: float | None
    last_series: str | None
    avg_pos_delta: float | None
    cust_id: int
    race_preference: int | None
    dnf_total: int
    disc: int
    eject: int
    quit_: int
    dq: int
    other: int
    has_notes: bool

    @classmethod
    def from_sql_row(cls, row: tuple) -> DriverTableRow:
        (
            name,
            avg_inc,
            avg_fin,
            total_races,
            last_ir,
            last_sr,
            last_series,
            avg_pos_delta,
            cust_id,
            race_preference,
            dnf_total,
            disc,
            eject,
            quit_,
            dq,
            other,
            has_notes,
        ) = row
        return cls(
            name=name or "",
            avg_inc=avg_inc,
            avg_fin=avg_fin,
            total_races=int(total_races or 0),
            last_ir=last_ir,
            last_sr=last_sr,
            last_series=last_series,
            avg_pos_delta=avg_pos_delta,
            cust_id=int(cust_id),
            race_preference=sqlite_row_to_int(race_preference),
            dnf_total=int(dnf_total or 0),
            disc=int(disc or 0),
            eject=int(eject or 0),
            quit_=int(quit_ or 0),
            dq=int(dq or 0),
            other=int(other or 0),
            has_notes=bool(has_notes),
        )

    @property
    def safety(self) -> SafetyIndex:
        return compute_safety_index(
            avg_inc=self.avg_inc,
            total_races=self.total_races,
            dnf_total=self.dnf_total,
            avg_pos_delta=self.avg_pos_delta,
        )

    @property
    def dnf_breakdown(self) -> str:
        return format_dnf_breakdown(
            self.disc, self.eject, self.quit_, self.dq, self.other
        )

    def to_live_entry(self) -> dict:
        return {
            "cust_id": self.cust_id,
            "name": self.name,
            "avg_inc": self.avg_inc,
            "avg_fin": self.avg_fin,
            "total_races": self.total_races,
            "dnf_total": self.dnf_total,
            "avg_pos_delta": self.avg_pos_delta,
            "last_sr": self.last_sr,
            "last_ir": self.last_ir,
            "has_note": self.has_notes,
            "pref": self.race_preference,
        }


def apply_racing_type_stats_to_live_entry(
    entry: dict,
    type_row: DriverTableRow | None,
    *,
    racing_type: str,
    racing_type_label: str,
) -> None:
    """Replace lifetime scouting stats with a racing-type slice for Live Mode."""
    entry["racing_type"] = racing_type
    entry["racing_type_label"] = racing_type_label
    if not racing_type:
        return
    if type_row is None or type_row.total_races <= 0:
        entry["avg_inc"] = None
        entry["avg_fin"] = None
        entry["total_races"] = 0
        entry["dnf_total"] = 0
        entry["avg_pos_delta"] = None
        entry["safety"] = empty_safety()
        entry["dnf_breakdown"] = ""
        return
    entry["avg_inc"] = type_row.avg_inc
    entry["avg_fin"] = type_row.avg_fin
    entry["total_races"] = type_row.total_races
    entry["dnf_total"] = type_row.dnf_total
    entry["avg_pos_delta"] = type_row.avg_pos_delta
    entry["safety"] = type_row.safety
    entry["has_history"] = True
    entry["dnf_breakdown"] = type_row.dnf_breakdown


@dataclass(frozen=True)
class DriverDetailRow:
    name: str
    last_seen_at: str | None
    last_series: str | None
    avg_inc: float | None
    avg_fin: float | None
    total_races: int
    last_ir: int | None
    last_sr: float | None
    avg_pos_delta: float | None
    dnf_total: int
    disc: int
    eject: int
    quit_: int
    dq: int
    other: int

    @classmethod
    def from_sql_row(cls, row: tuple) -> DriverDetailRow:
        (
            name,
            last_seen_at,
            last_series,
            avg_inc,
            avg_fin,
            total_races,
            last_ir,
            last_sr,
            avg_pos_delta,
            dnf_total,
            disc,
            eject,
            quit_,
            dq,
            other,
        ) = row
        return cls(
            name=name or "",
            last_seen_at=last_seen_at,
            last_series=last_series,
            avg_inc=avg_inc,
            avg_fin=avg_fin,
            total_races=int(total_races or 0),
            last_ir=last_ir,
            last_sr=last_sr,
            avg_pos_delta=avg_pos_delta,
            dnf_total=int(dnf_total or 0),
            disc=int(disc or 0),
            eject=int(eject or 0),
            quit_=int(quit_ or 0),
            dq=int(dq or 0),
            other=int(other or 0),
        )

    @property
    def safety(self) -> SafetyIndex:
        return compute_safety_index(
            avg_inc=self.avg_inc,
            total_races=self.total_races,
            dnf_total=self.dnf_total,
            avg_pos_delta=self.avg_pos_delta,
        )

    @property
    def dnf_breakdown(self) -> str:
        return format_dnf_breakdown(self.disc, self.eject, self.quit_, self.dq, self.other)


def build_live_session_entries(
    active_cust_ids: set[int],
    active_driver_names: dict[int, str],
    table_rows: list[DriverTableRow],
) -> list[dict]:
    """Merge SDK session drivers with saved stats for Live Mode and Grid Walk."""
    if not active_cust_ids:
        return []

    db_by_id = {row.cust_id: row for row in table_rows}
    entries: list[dict] = []

    for cid in active_cust_ids:
        row = db_by_id.get(cid)
        if row is not None:
            entry = row.to_live_entry()
            safety = row.safety
        else:
            entry = {
                "cust_id": cid,
                "name": active_driver_names.get(cid, f"Driver {cid}"),
                "avg_inc": None,
                "total_races": 0,
                "dnf_total": 0,
                "avg_pos_delta": None,
                "last_sr": None,
                "last_ir": None,
                "has_note": False,
                "pref": None,
            }
            safety = empty_safety()

        entry["safety"] = safety

        races = entry.get("total_races") or 0
        entry["has_history"] = races > 0
        entries.append(entry)

    return entries


def sort_live_mode_card_entries(entries: list[dict]) -> list[dict]:
    """Live Mode card order: most races in your book first, none at the bottom."""
    return sorted(
        entries,
        key=lambda e: (
            -(int(e.get("total_races") or 0)),
            (e.get("name") or "").casefold(),
        ),
    )


def format_shared_races_label(count: int | None) -> str:
    """User-facing label for how often you raced someone (Live Mode)."""
    if count is None:
        return ""
    if count <= 0:
        return "No shared races yet"
    if count == 1:
        return "Raced together 1 time"
    return f"Raced together {count} times"


def format_live_session_at_glance(entries: list[dict]) -> str:
    """One-line session summary for Live Mode / Grid Walk headers."""
    if not entries:
        return ""

    total = len(entries)
    flagged = disliked = liked = new = league = 0
    for entry in entries:
        if not entry.get("has_history"):
            new += 1
        if entry.get("league_label"):
            league += 1
        pref = entry.get("pref")
        if pref == 1:
            liked += 1
        elif pref == -1:
            disliked += 1
        safety = entry.get("safety")
        if isinstance(safety, SafetyIndex) and safety.tier != "unknown":
            if safety.risky or safety.tier == "high":
                flagged += 1

    parts = [f"{total} drivers"]
    if flagged:
        parts.append(f"{flagged} flagged")
    if disliked:
        parts.append(f"{disliked} disliked")
    if liked:
        parts.append(f"{liked} liked")
    if league:
        parts.append(f"{league} league")
    if new:
        parts.append(f"{new} new to your book")
    return " · ".join(parts)
