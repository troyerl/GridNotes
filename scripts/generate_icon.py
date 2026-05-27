"""Build icon.ico from icon.png for Windows taskbar / EXE icon."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "icon.png"
ICO = ROOT / "icon.ico"


def main() -> None:
    if not PNG.is_file():
        raise SystemExit(f"Missing {PNG}")

    from PIL import Image

    img = Image.open(PNG).convert("RGBA")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    img.save(ICO, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Wrote {ICO} ({ICO.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
