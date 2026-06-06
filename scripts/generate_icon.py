"""Build icon.ico (Windows) and icon.icns (macOS) from icon.png."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "icon.png"
ICO = ROOT / "icon.ico"
ICNS = ROOT / "icon.icns"


def write_ico(img) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    img.save(ICO, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Wrote {ICO} ({ICO.stat().st_size} bytes)")


def write_icns(png_path: Path, icns_path: Path) -> None:
    if sys.platform != "darwin":
        print("Skipping icon.icns (requires macOS iconutil)")
        return
    if shutil.which("iconutil") is None:
        raise SystemExit("iconutil is required to build icon.icns on macOS")

    from PIL import Image

    source = Image.open(png_path).convert("RGBA")
    iconset_entries = (
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    )

    with tempfile.TemporaryDirectory(prefix="gridnotes-icon-") as tmp:
        iconset = Path(tmp) / "GridNotes.iconset"
        iconset.mkdir()
        for filename, size in iconset_entries:
            out = iconset / filename
            resized = source.resize((size, size), Image.Resampling.LANCZOS)
            # iconutil is picky about PNG metadata; RGB without alpha is safest.
            resized.convert("RGB").save(out, format="PNG")
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise SystemExit(f"iconutil failed: {detail}")
    print(f"Wrote {icns_path} ({icns_path.stat().st_size} bytes)")


def main() -> None:
    if not PNG.is_file():
        raise SystemExit(f"Missing {PNG}")

    from PIL import Image

    img = Image.open(PNG).convert("RGBA")
    write_ico(img)
    write_icns(PNG, ICNS)


if __name__ == "__main__":
    main()
