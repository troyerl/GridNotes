#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo ""
  echo "Python 3 was not found. Install Python 3.10+ from https://www.python.org/downloads/"
  echo ""
  read -r -p "Press Enter to close…"
  exit 1
fi

echo "Starting GridNotes installer…"
python3 install_gui.py
