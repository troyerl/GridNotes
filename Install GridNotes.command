#!/bin/bash
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo ""
  echo "  GridNotes needs Python installed once before it can run."
  echo ""
  echo "  1. Open https://www.python.org/downloads/ in your browser"
  echo "  2. Download and install Python"
  echo "  3. Double-click Install GridNotes.command again"
  echo ""
  open "https://www.python.org/downloads/" 2>/dev/null || true
  read -r -p "Press Enter to close…"
  exit 1
fi

echo ""
echo "  Starting GridNotes install helper…"
echo "  Click Install GridNotes in the window."
echo ""
python3 install_gui.py
