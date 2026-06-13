"""Broad racing-type buckets for contextual scouting stats and filters."""

from __future__ import annotations

RACING_TYPE_OVAL = "oval"
RACING_TYPE_ROAD = "road"
RACING_TYPE_FORMULA = "formula"
RACING_TYPE_DIRT = "dirt"

RACING_TYPE_FILTER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("", "All types"),
    (RACING_TYPE_OVAL, "Oval"),
    (RACING_TYPE_ROAD, "Road"),
    (RACING_TYPE_FORMULA, "Formula"),
    (RACING_TYPE_DIRT, "Dirt"),
)

_FORMULA_KEYWORDS = (
    "formula",
    "f1",
    "f2",
    "f3",
    "f4",
    "indycar",
    "indy car",
    "ir-01",
    "ir01",
    "ir-04",
    "ir04",
    "ir-18",
    "ir18",
    "usf2000",
    "usf 2000",
    "pro mazda",
    "star mazda",
    "spec racer",
    "formula vee",
    "formula ford",
    "super formula",
    "open wheel",
    "open-wheel",
    "dallara",
    "ray formula",
)

_DIRT_KEYWORDS = (
    "dirt oval",
    "dirtoval",
    "dirt road",
    "dirtroad",
    "world of outlaws",
    "woo",
    "knoxville",
    "sprint car",
    "micro sprint",
    "midget",
    "late model",
    "super late model",
    "street stock",
    "pro late model",
    "legends dirt",
    "dirt",
)

_OVAL_KEYWORDS = (
    "nascar",
    "oval",
    "arca",
    "truck",
    "modified",
    "legend car",
    "mini stock",
    "tour type",
    "b class",
    "c class",
)

_ROAD_KEYWORDS = (
    "road",
    "gt3",
    "gt4",
    "gtd",
    "imsa",
    "porsche cup",
    "ferrari",
    "lamborghini",
    "tcr",
    "mx-5",
    "mx5",
    "global mazda",
    "production car",
    "sports car",
    "rallycross",
    "rally cross",
)


def _normalized_tokens(text: str | None) -> str:
    return (text or "").strip().lower()


def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_racing_type_from_series(series_name: str | None) -> str:
    """Best-effort bucket from an iRacing series / event name."""
    text = _normalized_tokens(series_name)
    if not text:
        return ""
    if _matches_any(text, _FORMULA_KEYWORDS):
        return RACING_TYPE_FORMULA
    if _matches_any(text, _DIRT_KEYWORDS):
        return RACING_TYPE_DIRT
    if _matches_any(text, _OVAL_KEYWORDS):
        return RACING_TYPE_OVAL
    if _matches_any(text, _ROAD_KEYWORDS):
        return RACING_TYPE_ROAD
    return ""


def classify_racing_type_from_category(category: str | None) -> str:
    """Map live SDK category labels to a racing-type bucket."""
    text = _normalized_tokens(category).replace("_", " ")
    if not text:
        return ""
    if "formula" in text or text == "open wheel":
        return RACING_TYPE_FORMULA
    if "dirt" in text:
        return RACING_TYPE_DIRT
    if "oval" in text:
        return RACING_TYPE_OVAL
    if "road" in text or "sports car" in text:
        return RACING_TYPE_ROAD
    return ""


def resolve_racing_type(
    *,
    category: str | None = None,
    series_name: str | None = None,
) -> str:
    """Pick the best racing-type bucket for live scouting context."""
    series_type = classify_racing_type_from_series(series_name)
    if series_type == RACING_TYPE_FORMULA:
        return RACING_TYPE_FORMULA
    category_type = classify_racing_type_from_category(category)
    if category_type:
        return category_type
    if series_type:
        return series_type
    return ""


def racing_type_label(racing_type: str | None) -> str:
    return {
        RACING_TYPE_OVAL: "Oval",
        RACING_TYPE_ROAD: "Road",
        RACING_TYPE_FORMULA: "Formula",
        RACING_TYPE_DIRT: "Dirt",
    }.get((racing_type or "").strip(), "")


def racing_type_stats_scope(racing_type: str | None) -> str:
    label = racing_type_label(racing_type)
    return f"{label} stats" if label else ""
