"""Reference copy for Safety Index, form trends, marks, and risk factors."""

from __future__ import annotations

from ..safety.safety_index import (
    MIN_RACES_FOR_SCORE,
    RISKY_SCORE_THRESHOLD,
    TIER_COLORS_HEX,
    WEIGHT_DNF,
    WEIGHT_INCIDENTS,
    WEIGHT_POS,
)
from ..safety.safety_trend import (
    MIN_RACES_FOR_TREND,
    SIGNIFICANT_TREND_DELTA,
    TREND_RACE_WINDOW,
)

_LOW_MAX = 35  # matches _tier_for_score in safety_index


def _tier_row(label: str, score_range: str, tier_key: str) -> str:
    color = TIER_COLORS_HEX.get(tier_key, TIER_COLORS_HEX["unknown"])
    return (
        f'<li><span style="color:{color}; font-weight:700;">■</span> '
        f"<b>{label}</b> — {score_range}</li>"
    )


def scouting_legend_sections() -> list[tuple[str, str]]:
    """Reference sections for the scouting guide dialog."""
    inc_pct = int(round(WEIGHT_INCIDENTS * 100))
    dnf_pct = int(round(WEIGHT_DNF * 100))
    pos_pct = int(round(WEIGHT_POS * 100))

    safety_html = (
        "<p>The <b>Grid Safety Index</b> is a 0–100 risk score built from your saved "
        "race results. <b>Higher scores mean higher risk.</b> It appears in the driver "
        "table, the detail panel, Live Mode cards, and Grid Walk.</p>"
        f"<p>Drivers need <b>{MIN_RACES_FOR_SCORE}+ races</b> in your book before a "
        "score is shown; until then the cell stays blank.</p>"
        "<p><b>Risk tiers</b> (score ranges):</p>"
        "<ul>"
        + _tier_row("Low", f"0–{_LOW_MAX - 1}", "low")
        + _tier_row(
            "Moderate",
            f"{_LOW_MAX}–{RISKY_SCORE_THRESHOLD - 1}",
            "moderate",
        )
        + _tier_row("High", f"{RISKY_SCORE_THRESHOLD}+", "high")
        + "</ul>"
        "<p>The number uses your lifetime average incidents, DNF rate, and how often "
        "the driver loses positions (starting minus finish). Open a driver’s detail "
        "panel to see the component bars and short profile label (for example "
        "“Fast but aggressive”).</p>"
        f"<p>Scores of <b>{RISKY_SCORE_THRESHOLD}+</b> are treated as "
        "<b>high risk</b>: the Mark column may show <b>Risk</b>, rows get a gold "
        "highlight, and the audio spotter can warn you in Live Mode.</p>"
    )

    trend_improving = TIER_COLORS_HEX["low"]
    trend_worsening = TIER_COLORS_HEX["high"]
    trend_stable = TIER_COLORS_HEX["unknown"]

    form_html = (
        "<p><b>Form guide</b> arrows compare a driver’s <b>lifetime</b> Safety Index "
        f"to their last <b>{TREND_RACE_WINDOW} races</b> (needs "
        f"<b>{MIN_RACES_FOR_TREND}+</b> recent races in that window).</p>"
        "<ul>"
        f'<li><span style="color:{trend_improving}; font-weight:700;">↗</span> '
        "<b>Improving</b> — recent form is cleaner; recent score is at least "
        f"{SIGNIFICANT_TREND_DELTA:.0f} points lower than lifetime "
        "(arrow and score tint green when shown).</li>"
        f'<li><span style="color:{trend_worsening}; font-weight:700;">↘</span> '
        "<b>Worsening</b> — recent form is riskier; recent score is at least "
        f"{SIGNIFICANT_TREND_DELTA:.0f} points higher (red).</li>"
        f'<li><span style="color:{trend_stable}; font-weight:700;">→</span> '
        "<b>Stable</b> — recent form is within that band of lifetime.</li>"
        "<li><b>No arrow</b> — not enough recent races, or no lifetime score yet.</li>"
        "</ul>"
        "<p>Example: lifetime score 45 with three clean recent races may show "
        '<span style="font-weight:700;">45 ↗</span> even though the lifetime number '
        "still looks moderate.</p>"
        "<p>Hover the Safety column or open the detail panel for lifetime vs recent "
        "breakdown in the tooltip.</p>"
    )

    marks_html = (
        "<p><b>Mark column</b> (driver table and Grid Walk) — your scouting labels:</p>"
        "<ul>"
        "<li><b>Liked</b> — you marked that you enjoyed racing with this driver "
        "(green row tint).</li>"
        "<li><b>Disliked</b> — you would avoid them when possible (red tint).</li>"
        "<li><b>Risk</b> — high Safety Index from stats; can appear with or without "
        "a like/dislike (gold tint). Disliked takes priority for spotter warnings.</li>"
        "</ul>"
        "<p><b>Notes column</b> shows <b>Notes</b> when you saved scouting notes for "
        "that driver.</p>"
        "<p>Use the <b>Like</b> / <b>Dislike</b> buttons in the detail panel, or "
        "keyboard shortcuts, to set marks. Row colors are reinforced by icons in the "
        "Mark column so risk is not conveyed by color alone.</p>"
    )

    factors_html = (
        "<p>In the detail panel, <b>Grid Safety Index</b> breaks down into three "
        "weighted factors:</p>"
        "<ul>"
        f"<li><b>Incidents</b> — {inc_pct}% of the score (avg incidents per race).</li>"
        f"<li><b>DNF rate</b> — {dnf_pct}% (did not finish vs races started).</li>"
        f"<li><b>Position loss</b> — {pos_pct}% (how often they lose places from "
        "grid to checker).</li>"
        "</ul>"
        "<p><b>Risk factor callouts</b> (shown under the bars when applicable):</p>"
        "<ul>"
        "<li><b>High / elevated incidents</b> — above-normal incident average.</li>"
        "<li><b>DNF rate</b> or <b>DNFs</b> — frequent disconnects, crashes, or "
        "other DNFs in your history.</li>"
        "<li><b>Loses positions</b> — tends to fall back during the race.</li>"
        "</ul>"
        "<p>These are summaries of imported iRacing results in your local database; "
        "they reflect what you have imported, not iRacing’s official safety rating.</p>"
    )

    return [
        ("Safety Index & colors", safety_html),
        ("Form guide (↗ ↘ →)", form_html),
        ("Marks, notes & row highlights", marks_html),
        ("Risk factors & breakdown", factors_html),
    ]


def scouting_guide_document_html() -> str:
    """Full HTML document for the scouting guide dialog."""
    intro = (
        "<p>GridNotes scores drivers from race results in your local book. "
        "Use this guide when reading the Safety column, form arrows, marks, "
        "and detail-panel breakdown.</p>"
    )
    parts = [intro]
    for title, body in scouting_legend_sections():
        parts.append(f"<h2>{title}</h2>")
        parts.append(body)
    return "\n".join(parts)
