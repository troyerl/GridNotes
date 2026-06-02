"""Audio co-driver spotter using local Windows text-to-speech."""

from __future__ import annotations

import logging
import queue
import re
import sys
import threading
import time
from dataclasses import dataclass

from ..safety.safety_index import SafetyIndex, compute_safety_index

logger = logging.getLogger(__name__)

AUDIO_SPOTTER_KEY = "audio_spotter"
SPOTTER_COOLDOWN_SECONDS = 45.0
MAX_NOTE_SNIPPET_CHARS = 120

_SENTENCE_END = re.compile(r"[.!?]\s+")


@dataclass(frozen=True)
class SpotterDriverInfo:
    name: str
    notes: str
    race_preference: int | None
    safety: SafetyIndex


def is_audio_spotter_setting_enabled(raw: str | None) -> bool:
    return (raw or "0").strip() == "1"


def load_spotter_driver(conn, cust_id: int) -> SpotterDriverInfo | None:
    """Load driver name, notes, preference, and safety for spotter announcements."""
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH agg AS (
            SELECT
                cust_id,
                ROUND(AVG(incidents), 1) AS avg_inc,
                ROUND(AVG(finish_position), 1) AS avg_fin,
                COUNT(id) AS total_races,
                ROUND(
                    AVG(
                        CASE
                            WHEN starting_position IS NOT NULL AND finish_position IS NOT NULL
                            THEN (starting_position - finish_position)
                        END
                    ),
                    1
                ) AS avg_pos_delta,
                SUM(CASE WHEN reason_out_id IN (1, 2, 3, 4) THEN 1 ELSE 0 END) AS dnf_total,
                SUM(CASE WHEN reason_out_id = 1 THEN 1 ELSE 0 END) AS disc,
                SUM(CASE WHEN reason_out_id = 2 THEN 1 ELSE 0 END) AS eject,
                SUM(CASE WHEN reason_out_id = 3 THEN 1 ELSE 0 END) AS quit_,
                SUM(CASE WHEN reason_out_id = 4 THEN 1 ELSE 0 END) AS dq,
                SUM(
                    CASE
                        WHEN reason_out_id IS NOT NULL AND reason_out_id NOT IN (0, 1, 2, 3, 4)
                        THEN 1
                        ELSE 0
                    END
                ) AS other
            FROM race_results
            WHERE cust_id = ?
            GROUP BY cust_id
        )
        SELECT
            d.driver_name,
            COALESCE(d.notes, ''),
            d.race_preference,
            a.avg_inc,
            a.avg_fin,
            COALESCE(a.total_races, 0),
            a.avg_pos_delta,
            COALESCE(a.dnf_total, 0),
            COALESCE(a.disc, 0),
            COALESCE(a.eject, 0),
            COALESCE(a.quit_, 0),
            COALESCE(a.dq, 0),
            COALESCE(a.other, 0)
        FROM drivers d
        LEFT JOIN agg a ON d.cust_id = a.cust_id
        WHERE d.cust_id = ?
        """,
        (cust_id, cust_id),
    )
    row = cursor.fetchone()
    if not row:
        return None

    from ..core.utils import sqlite_row_to_int

    name = (row[0] or "").strip() or f"Driver {cust_id}"
    notes = (row[1] or "").strip()
    pref = sqlite_row_to_int(row[2])
    avg_inc = row[3]
    avg_fin = row[4]
    total_races = int(row[5] or 0)
    avg_pos_delta = row[6]
    dnf_total = int(row[7] or 0)
    disc, eject, quit_, dq, other = int(row[8]), int(row[9]), int(row[10]), int(row[11]), int(row[12])

    safety = compute_safety_index(
        avg_incidents=avg_inc,
        avg_finish=avg_fin,
        total_races=total_races,
        avg_pos_delta=avg_pos_delta,
        dnf_total=dnf_total,
        disc=disc,
        eject=eject,
        quit_=quit_,
        dq=dq,
        other=other,
    )
    return SpotterDriverInfo(
        name=name,
        notes=notes,
        race_preference=pref if pref in (1, -1) else None,
        safety=safety,
    )


def should_warn_driver(info: SpotterDriverInfo) -> bool:
    if info.race_preference == -1:
        return True
    return info.safety.risky or info.safety.tier == "high"


def _note_snippet(notes: str) -> str:
    text = " ".join(notes.split())
    if not text:
        return ""
    match = _SENTENCE_END.search(text)
    if match:
        snippet = text[: match.end()].strip()
    else:
        snippet = text
    if len(snippet) > MAX_NOTE_SNIPPET_CHARS:
        snippet = snippet[: MAX_NOTE_SNIPPET_CHARS - 3].rstrip() + "..."
    return snippet


def build_spotter_message(
    info: SpotterDriverInfo,
    *,
    announce_name: str | None = None,
) -> str:
    name = (announce_name or info.name).strip() or "a flagged driver"
    parts = [f"Car behind is {name}."]
    if info.race_preference == -1:
        parts.append("Marked as disliked.")
    elif info.safety.risky or info.safety.tier == "high":
        parts.append("Marked as risk.")
    snippet = _note_snippet(info.notes)
    if snippet:
        parts.append(snippet)
    return " ".join(parts)


class _WindowsTTSWorker:
    """Background thread that speaks lines via Windows SAPI (pyttsx3)."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="GridNotesTTS", daemon=True)
        self._started = False
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def start(self) -> None:
        if sys.platform != "win32":
            return
        if not self._started:
            self._started = True
            self._thread.start()

    def stop(self) -> None:
        if self._started:
            self._queue.put(None)

    def speak(self, text: str) -> bool:
        if not text.strip() or sys.platform != "win32":
            return False
        self.start()
        if not self._available:
            return False
        self._queue.put(text.strip())
        return True

    def _run(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import pyttsx3

            engine = pyttsx3.init()
            rate = engine.getProperty("rate")
            if isinstance(rate, int) and rate > 0:
                engine.setProperty("rate", min(220, int(rate * 0.95)))
            self._available = True
            logger.info("Audio spotter TTS engine ready")
        except Exception:
            logger.exception("Audio spotter: pyttsx3 unavailable")
            self._available = False
            return

        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:
                logger.exception("Audio spotter TTS speak failed")


class AudioSpotterService:
    """Announces flagged drivers behind the player with cooldown per driver."""

    def __init__(self) -> None:
        self._tts = _WindowsTTSWorker()
        self._last_announced: dict[int, float] = {}
        self._active_cust_id: int | None = None

    @property
    def tts_available(self) -> bool:
        return sys.platform == "win32"

    def stop(self) -> None:
        self._tts.stop()

    def reset_tracking(self) -> None:
        self._active_cust_id = None

    def maybe_announce(
        self,
        cust_id: int,
        info: SpotterDriverInfo,
        *,
        announce_name: str | None = None,
    ) -> bool:
        if not should_warn_driver(info):
            self._active_cust_id = None
            return False

        now = time.monotonic()
        last = self._last_announced.get(cust_id, 0.0)
        if cust_id == self._active_cust_id and (now - last) < SPOTTER_COOLDOWN_SECONDS:
            return False

        message = build_spotter_message(info, announce_name=announce_name)
        if not self._tts.speak(message):
            logger.warning("Audio spotter: could not queue speech")
            return False

        self._active_cust_id = cust_id
        self._last_announced[cust_id] = now
        logger.info("Audio spotter announced cust_id=%s", cust_id)
        return True
