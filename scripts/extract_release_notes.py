#!/usr/bin/env python3
"""Extract one version section from docs/RELEASE_NOTES.md for GitHub Releases."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_PATH = ROOT / "docs" / "RELEASE_NOTES.md"
_SECTION_RE = re.compile(r"^## v\d+\.\d+\.\d+")


def normalize_version(tag_or_version: str) -> str:
    text = tag_or_version.strip()
    if text.lower().startswith("refs/tags/"):
        text = text.split("/", 2)[-1]
    return text.lstrip("vV")


def extract_release_notes(version: str, path: Path = NOTES_PATH) -> str:
    version = normalize_version(version)
    if not version:
        raise ValueError("missing version (e.g. v1.0.21)")

    if not path.is_file():
        raise FileNotFoundError(f"Release notes file not found: {path}")

    header = f"## v{version}"
    lines = path.read_text(encoding="utf-8").splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.startswith(header):
            start = index
            break
    if start is None:
        raise LookupError(f"No section {header!r} in {path}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if _SECTION_RE.match(lines[index]):
            end = index
            break

    body_lines: list[str] = []
    for line in lines[start:end]:
        if line.strip() == "---":
            break
        body_lines.append(line)

    body = "\n".join(body_lines).strip()
    if not body:
        raise LookupError(f"Section {header!r} is empty in {path}")
    return body


def write_release_notes(version: str, output: Path, *, notes_path: Path = NOTES_PATH) -> None:
    """Write extracted notes to *output* as UTF-8 (no console encoding)."""
    text = extract_release_notes(version, notes_path)
    output.write_text(text + "\n", encoding="utf-8", newline="\n")


def _write_stdout_utf8(text: str) -> None:
    """Write UTF-8 to stdout (fallback when no --output)."""
    data = text.encode("utf-8")
    if not data.endswith(b"\n"):
        data += b"\n"
    sys.stdout.buffer.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a version section from docs/RELEASE_NOTES.md",
    )
    parser.add_argument(
        "version",
        help="Tag or version (e.g. v1.0.23)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write UTF-8 release body to this file (recommended on Windows CI)",
    )
    args = parser.parse_args(argv)

    try:
        if args.output is not None:
            write_release_notes(args.version, args.output)
        else:
            _write_stdout_utf8(extract_release_notes(args.version))
    except (LookupError, FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
