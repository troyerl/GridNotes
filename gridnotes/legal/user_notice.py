"""User-facing license and legal copy for Settings → Legal."""

from __future__ import annotations

from pathlib import Path

COPYRIGHT_HOLDER = "Logan Troyer"
PRODUCT_NAME = "GridNotes"

IRACING_TERMS_URL = "https://www.iracing.com/console-terms-use-eula/"
IRACING_OAUTH_URL = "https://oauth.iracing.com/oauth2/book/introduction.html"

INSTALL_LICENSE_ACK_LABEL = "I have read and agree to the license terms"


def _license_file_candidates(source_root: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if source_root is not None:
        candidates.append(source_root / "LICENSE")
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "LICENSE")
    return candidates


def install_license_text(source_root: Path | None = None) -> str:
    """Plain-text license shown in the install wizard (matches LICENSE when present)."""
    for path in _license_file_candidates(source_root):
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8").strip()
            except OSError:
                continue
    return (
        f"{PRODUCT_NAME} — Free for Personal Use License\n\n"
        f"Copyright (c) 2026 {COPYRIGHT_HOLDER}\n\n"
        "Permission is granted to download, install, and use GridNotes free of "
        "charge for personal, non-commercial purposes. Commercial use requires "
        "written permission. GridNotes is not affiliated with iRacing. See LICENSE "
        "in the download folder for the full terms."
    )


def license_summary_html() -> str:
    return (
        "<p><b>Free for personal use.</b> You may download, install, and run "
        f"{PRODUCT_NAME} at no charge for your own non-commercial scouting and "
        "note-taking.</p>"
        "<p>You may share official release files (for example, from GitHub Releases) "
        "as long as this license travels with them. Commercial use, resale, or "
        "offering the app as part of a paid service requires written permission "
        f"from {COPYRIGHT_HOLDER}.</p>"
        f"<p>Copyright © {COPYRIGHT_HOLDER}. A full copy of the license is included "
        "with the project as <code>LICENSE</code>.</p>"
    )


def using_gridnotes_html() -> str:
    return (
        f"<p>{PRODUCT_NAME} is a local desktop tool. Each person runs their own copy "
        "on their own computer and builds their own scouting book from races they "
        "participate in or data they are allowed to import.</p>"
        "<p><b>Intended use:</b> private notes, likes/dislikes, safety trends, and "
        "optional live session views while iRacing is running (Windows). Optional "
        "LAN broadcast shares <i>your</i> book with another device on your network "
        "during a session — not a public website or shared cloud database.</p>"
        "<p><b>Not intended for:</b> cheating, modifying iRacing, packet sniffing, "
        "automated driving, publishing a public driver database, or selling access "
        "to other people's race history.</p>"
    )


def iracing_notice_html() -> str:
    return (
        f"<p>{PRODUCT_NAME} is <b>not affiliated with, endorsed by, or sponsored by "
        "iRacing</b>. You must have your own iRacing membership where required and "
        "follow iRacing's Terms of Use, EULA, Sporting Code, and any league rules "
        "that apply to you.</p>"
        "<p>Live features read iRacing's shared-memory SDK (telemetry/session info) "
        "in read-only fashion — the same general approach as dashboards and spotter "
        "tools. iRacing does not explicitly approve third-party apps; use is at "
        "your own discretion and subject to iRacing's policies, which may change.</p>"
        "<p>If you use JSON import or the optional Data API, use data you are "
        "authorized to access — typically your own exports or API credentials. "
        "Do not scrape the members site or redistribute iRacing data for value.</p>"
        f'<p>References: <a href="{IRACING_TERMS_URL}">iRacing Terms / EULA</a> · '
        f'<a href="{IRACING_OAUTH_URL}">iRacing OAuth / Data API notice</a></p>'
    )


def data_privacy_html() -> str:
    return (
        f"<p><b>Your data stays on your PC.</b> {PRODUCT_NAME} stores notes, marks, "
        "and imported race stats in a local SQLite database. There is no GridNotes "
        "cloud account and no central server that holds your scouting book.</p>"
        "<p>Imported races include other drivers' iRacing names, customer IDs, and "
        "public race statistics from sessions you were in. Your personal notes about "
        "those drivers are also stored locally. Treat that information responsibly — "
        "do not use it to harass, dox, or publish others without a lawful reason.</p>"
        "<p>You can back up, export, or delete your database from Settings → "
        "Maintenance. Uninstall can optionally remove all local data.</p>"
    )


def disclaimer_html() -> str:
    return (
        "<p>The information on this page is provided for convenience and is "
        "<b>not legal advice</b>. Laws and iRacing policies vary by jurisdiction "
        "and may change. If you need certainty about commercial distribution, "
        "data publishing, or compliance, consult a qualified attorney.</p>"
        f"<p>{PRODUCT_NAME} is provided <b>\"as is\"</b> without warranty. See the "
        "LICENSE file for the full disclaimer and limitation of liability.</p>"
    )
